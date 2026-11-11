"""Windows-only, outbound daily probe. No publication credentials on the worker."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
import ipaddress
import json
import os
from pathlib import Path
import socket
import statistics
import subprocess
import tempfile
import threading
import time

import ai_check
import enrich
import health
from mainland_policy import PROFILE, MIN_DOWNLOAD_MBPS, MIN_BASELINE_MBPS, valid_baseline

MiB = 1024 ** 2
GiB = 1024 ** 3
RX_LIMIT, TX_LIMIT, MONTH_LIMIT = 2 * GiB, 128 * MiB, 5 * GiB


class BudgetExceeded(RuntimeError):
    pass


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    os.replace(tmp, path)


def primary_counter():
    import psutil
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(('223.5.5.5', 443))  # Select route; UDP connect sends no packet.
        address = s.getsockname()[0]
    names = [name for name, addrs in psutil.net_if_addrs().items()
             if any(a.family == socket.AF_INET and a.address == address for a in addrs)]
    if len(names) != 1:
        raise RuntimeError('Cannot identify primary adapter')
    name = names[0]

    def read():
        row = psutil.net_io_counters(pernic=True, nowrap=False)[name]
        return row.bytes_recv, row.bytes_sent
    return read


class Budget:
    """Adapter deltas are a conservative upper bound, not per-process billing."""
    def __init__(self, ledger, counter=None, seconds=90 * 60):
        self.ledger = Path(ledger)
        self.counter = counter or primary_counter()
        self.before = self.counter()
        self.latest = self.before
        self.deadline = time.monotonic() + seconds
        self.month = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m')
        self.state = json.loads(self.ledger.read_text()) if self.ledger.exists() else {}
        self.base_tx = self.state.get('tx_upper_bound', 0) if self.state.get('month') == self.month else 0
        self.error = None
        self.processes = set()
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.watch, daemon=True)
        self.closed = False

    def start(self):
        self.check()
        if self.base_tx + TX_LIMIT > MONTH_LIMIT:
            raise BudgetExceeded('monthly_tx_reservation_unavailable')
        # Charge the full per-run allowance up front. A power loss cannot reset usage.
        self.checkpoint()
        self.thread.start()
        return self

    def check(self):
        with self.lock:
            if self.error:
                raise BudgetExceeded(self.error)
            if (datetime.now(timezone(timedelta(hours=8))) + timedelta(seconds=20)).strftime('%Y-%m') != self.month:
                raise BudgetExceeded('monthly_accounting_boundary')
            current = self.counter()
            if any(a < b for a, b in zip(current, self.latest)):
                raise BudgetExceeded('network_counter_reset')
            self.latest = current
            rx, tx = (a - b for a, b in zip(current, self.before))
            if time.monotonic() >= self.deadline:
                raise BudgetExceeded('deadline_exceeded')
            # Stop early, leaving room for in-flight packets and process shutdown.
            if rx >= RX_LIMIT - 32 * MiB or tx >= TX_LIMIT - 4 * MiB:
                raise BudgetExceeded('round_traffic_budget')
            if self.base_tx + tx >= MONTH_LIMIT - 4 * MiB:
                raise BudgetExceeded('monthly_tx_budget')

    def checkpoint(self, final=False):
        rx, tx = (max(0, a - b) for a, b in zip(self.latest, self.before))
        save(self.ledger, dict(month=self.month, tx_upper_bound=self.base_tx + (tx if final else TX_LIMIT),
                               last_rx_upper_bound=rx, last_tx_upper_bound=tx,
                               accounting='primary-adapter-during-test-upper-bound'))

    def watch(self):
        last_save = 0
        while not self.stop.wait(.1):
            try:
                self.check()
                if time.monotonic() - last_save >= 1:
                    with self.lock:
                        self.checkpoint()
                    last_save = time.monotonic()
            except Exception as e:
                with self.lock:
                    self.error = str(e) if isinstance(e, BudgetExceeded) else 'budget_monitor_failed'
                    for process in list(self.processes):
                        if process.poll() is None:
                            process.terminate()
                return

    def spawn(self, args, **kw):
        with self.lock:
            self.check()
            p = subprocess.Popen(args, **kw)
            self.processes.add(p)
            return p

    def run(self, args, timeout=15, **kw):
        p = self.spawn(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, **kw)
        try:
            output, _ = p.communicate(timeout=timeout)
            self.check()
            return p.returncode, output
        finally:
            if p.poll() is None:
                p.kill()
                p.wait()
            with self.lock:
                self.processes.discard(p)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.stop.set()
        self.thread.join(timeout=3)
        with self.lock:
            for p in list(self.processes):
                if p.poll() is None:
                    p.terminate()
                    try:
                        p.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        p.kill()
                        p.wait()
            try:
                self.check()
            except Exception as e:
                self.error = str(e) if isinstance(e, BudgetExceeded) else 'budget_monitor_failed'
            # Faulted counters/monitor retain the entire reservation, never settle to zero.
            self.checkpoint(final=self.error is None)


class Http:
    def __init__(self, budget):
        self.budget = budget
        self.env = {k: v for k, v in os.environ.items()
                    if k.lower() not in ('http_proxy', 'https_proxy', 'all_proxy', 'no_proxy')}

    def fetch(self, port, url, headers=None, data=None, limit=2 * MiB, download=False):
        with tempfile.TemporaryDirectory(prefix='cn-http-') as folder:
            path = Path(folder) / 'body'
            args = ['curl.exe' if os.name == 'nt' else 'curl', '-q', '--silent',
                    '--proto', '=https', '--proto-redir', '=https', '--location', '--max-redirs', '3',
                    '--max-time', '12', '--connect-timeout', '5', '--max-filesize', str(limit),
                    '--noproxy', '', '--proxy', f'http://127.0.0.1:{port}' if port else '',
                    '--user-agent', 'Mozilla/5.0', '--output', str(path),
                    '--write-out', '%{http_code} %{size_download} %{time_total}']
            for key, value in (headers or {}).items():
                args += ['--header', key + ': ' + value]
            if data is not None:
                request = Path(folder) / 'request'
                request.write_text(data, encoding='utf-8')
                args += ['--data-binary', '@' + str(request)]
            code, out = self.budget.run(args + [url], timeout=15)
            if code or not path.exists() or path.stat().st_size > limit:
                raise ValueError('request_failed')
            status, size, elapsed = out.decode('ascii').split()
            seconds = float(elapsed)
            return dict(code=int(status), ms=max(1, round(seconds * 1000)),
                        seconds=seconds, size=int(size),
                        body='' if download else path.read_text(encoding='utf-8', errors='replace'))


def domestic_controls(http):
    passed = 0
    for host in ('www.baidu.com', 'www.taobao.com', 'www.alipay.com'):
        try:
            r = http.fetch(None, 'https://' + host + '/robots.txt', limit=65536)
            passed += 200 <= r['code'] < 500 and r['code'] != 429
        except (ValueError, OSError, subprocess.SubprocessError):
            pass
    if passed < 2:
        raise RuntimeError('domestic_controls_failed')


def baseline(http):
    """Two domestic mirror routes; no node, GitHub download or foreign direct control."""
    size = 2 * MiB
    providers = {}
    for name, url in (('aliyun', 'https://mirrors.aliyun.com/ubuntu/ls-lR.gz'),
                      ('huawei', 'https://mirrors.huaweicloud.com/ubuntu/ls-lR.gz')):
        rates = []
        for _ in range(3):
            try:
                r = http.fetch(None, url, headers={'Range': f'bytes=0-{size-1}'}, limit=size, download=True)
                if r['code'] == 206 and r['size'] == size and r['seconds'] > 0:
                    rates.append(round(size * 8 / r['seconds'] / 1_000_000, 2))
            except (ValueError, OSError, subprocess.SubprocessError):
                pass
        if len(rates) >= 2:
            providers[name] = dict(samples_mbps=rates, median_mbps=statistics.median(rates))
    if len(providers) < 2:
        raise RuntimeError('domestic_baseline_unavailable')
    speed = statistics.median(p['median_mbps'] for p in providers.values())
    if speed < MIN_BASELINE_MBPS:
        raise RuntimeError('domestic_baseline_too_slow')
    return dict(median_mbps=round(speed, 2), providers=providers, sample_bytes=size,
                method='direct-domestic-range-3x2MiB-total-time')


def optional_baseline(http):
    try:
        return baseline(http)
    except BudgetExceeded:
        raise
    except RuntimeError as exc:
        if str(exc) not in ('domestic_baseline_unavailable', 'domestic_baseline_too_slow'):
            raise
        return {'error': str(exc), 'median_mbps': None}


def finalize_downloads(results, before, after):
    trusted = valid_baseline(before, after)
    for r in results:
        if not trusted and r.get('download_mbps') is not None:
            r['unverified_download_mbps'] = r['download_mbps']
            r['download_mbps'] = None
        r['download_status'] = ('measured' if r.get('download_mbps') is not None
                                else 'pending_retry' if trusted else 'baseline_unverified')
    return [] if trusted else ['download_baseline_unverified']


def basic(http, port):
    medians, exit_ip, country = [], '', 'ZZ'
    providers = [('https://www.cloudflare.com/cdn-cgi/trace', 'trace'),
                 ('https://www.gstatic.com/generate_204', 'empty'),
                 ('https://www.apple.com/library/test/success.html', 'apple')]
    for url, kind in providers:
        samples = []
        for _ in range(3):
            try:
                r = http.fetch(port, url, limit=8192)
                valid = (kind == 'empty' and r['code'] == 204 and not r['body'].strip()
                         or kind == 'apple' and r['code'] == 200 and '<TITLE>Success</TITLE>' in r['body'])
                if kind == 'trace' and r['code'] == 200:
                    country = health.parse_trace(r['body'])
                    exit_ip = dict(line.split('=', 1) for line in r['body'].splitlines() if '=' in line)['ip']
                    valid = True
                if valid:
                    samples.append(r['ms'])
            except (ValueError, OSError, subprocess.SubprocessError):
                pass
        if len(samples) >= 2:
            medians.append(statistics.median(samples))
    return dict(status='alive' if len(medians) >= 2 else 'dead',
                basic_latency_ms=round(statistics.median(medians)) if len(medians) >= 2 else None,
                exit_ip=exit_ip, country=country)


def ai(http, port):
    services, delays = {}, []
    for name, probe in zip(ai_check.SERVICES, (ai_check.chatgpt, ai_check.claude, ai_check.gemini)):
        try:
            delay = probe(port, request=http.fetch)
        except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError):
            delay = None
        services[name] = dict(passed=delay is not None, latency_ms=delay)
        if delay is not None:
            delays.append(delay)
    return dict(passed=len(delays) >= 2, pass_count=len(delays), services=services,
                latency_ms=round(statistics.median(delays)) if delays else None)


def download(http, port):
    rates = []
    size = 4 * MiB
    for _ in range(3):
        r = http.fetch(port, f'https://speed.cloudflare.com/__down?bytes={size}&nonce={time.time_ns()}',
                       limit=size, download=True)
        if r['code'] != 200 or r['size'] != size or r['seconds'] <= 0:
            raise ValueError('incomplete_download')
        rates.append(round(size * 8 / r['seconds'] / 1_000_000, 2))
    return dict(download_mbps=round(statistics.median(rates), 2), download_samples_mbps=rates)


def make_config(nodes):
    config = dict(log={'disabled': True}, inbounds=[], outbounds=[], route={'rules': []})
    ports, rejected = {}, 0
    for i, node in enumerate(nodes):
        out = dict(node['outbound'])
        try:
            out['server'] = health.public_ip(out['server'])
        except (ValueError, OSError):
            rejected += 1
            continue
        tag, port = 'cn' + str(i), 21000 + i
        out['tag'] = tag
        config['outbounds'].append(out)
        config['inbounds'].append(dict(type='mixed', tag=tag, listen='127.0.0.1', listen_port=port))
        config['route']['rules'].append(dict(inbound=[tag], action='route', outbound=tag))
        ports[node['id']] = port
    if not ports:
        raise RuntimeError('no_public_endpoints')
    return config, ports, rejected


def execute(doc, binary, budget):
    http = Http(budget)
    domestic_controls(http)
    before = optional_baseline(http)
    print(json.dumps({'stage': 'server_baseline_before', **before}), flush=True)
    config, ports, rejected = make_config(doc['nodes'])
    with tempfile.TemporaryDirectory(prefix='cn-core-') as folder:
        path = Path(folder) / 'config.json'
        save(path, config)
        code, _ = budget.run([binary, 'check', '-c', str(path)], timeout=20)
        if code:
            raise RuntimeError('core_configuration_rejected')
        core = budget.spawn([binary, 'run', '-c', str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
        if core.poll() is not None:
            raise RuntimeError('core_start_failed')

        def probe(n):
            r = dict(id=n['id'], measurement_profile=PROFILE, ai={'pass_count': 0, 'latency_ms': None, 'services': {}},
                     quality={'grade': 1, 'risk_score': None, 'label': '未知'},
                     media={'all_passed': False, 'services': {k: False for k in enrich.MEDIA}},
                     download_mbps=None)
            r.update(basic(http, ports[n['id']]) if n['id'] in ports else
                     dict(status='dead', basic_latency_ms=None, exit_ip='', country='ZZ'))
            if r.get('basic_latency_ms') is not None and 0 < r['basic_latency_ms'] < 1200:
                r['ai'] = ai(http, ports[n['id']])
            return r

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(probe, doc['nodes']))
        for index, r in enumerate(results, 1):
            print(json.dumps(dict(stage='node_basic', number=index, status=r['status'],
                                  latency_ms=r['basic_latency_ms'], ai_pass=r['ai']['pass_count'])), flush=True)
        if len(results) >= 3 and not any(r['status'] == 'alive' for r in results):
            raise RuntimeError('all_nodes_failed')
        enrich.fetch = http.fetch  # Only this dedicated worker process; overseas code is unaffected.
        for r in results:
            if r['status'] != 'alive' or not (0 < (r.get('basic_latency_ms') or 99999) < 1200):
                continue
            port = ports[r['id']]
            try:
                if not r['exit_ip']:
                    ip = json.loads(http.fetch(port, 'https://api.ipify.org?format=json', limit=4096)['body'])['ip']
                    if not ipaddress.ip_address(ip).is_global:
                        raise ValueError('invalid_exit')
                    r['exit_ip'] = ip
                try:
                    q = json.loads(http.fetch(None, 'https://api.ipquery.io/' + r['exit_ip'] + '?format=json', limit=65536)['body'])
                    r['quality'] = enrich.quality_from(q, r['exit_ip'])
                    if r['country'] == 'ZZ':
                        code = q.get('location', {}).get('country_code', 'ZZ')
                        r['country'] = code if len(code) == 2 and code.isalpha() else 'ZZ'
                except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError):
                    pass
                r.update(download(http, port))  # All bulk transfers are serial.
                print(json.dumps(dict(stage='node_download', number=results.index(r) + 1,
                                      mbps=r['download_mbps'], samples=r['download_samples_mbps'])), flush=True)
                after = json.loads(http.fetch(port, 'https://api.ipify.org?format=json', limit=4096)['body'])['ip']
                if after != r['exit_ip']:
                    r['download_mbps'] = None
            except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError):
                r['download_mbps'] = None
            try:
                r['media'] = enrich.check_media(port)
            except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError):
                pass
            budget.check()
            if core.poll() is not None:
                raise RuntimeError('core_stopped')
        domestic_controls(http)
        after = optional_baseline(http)
        print(json.dumps({'stage': 'server_baseline_after', **after}), flush=True)
        warnings = finalize_downloads(results, before, after)
        if core.poll() is not None:
            raise RuntimeError('core_stopped')
        budget.check()
        return dict(cycle=doc['cycle'], source_version=doc['source_version'], results=results,
                    endpoint_rejected=rejected, complete=True, tested_at=datetime.now(timezone.utc).isoformat(),
                    baseline=dict(before=before, after=after), warnings=warnings,
                    measurement_profile=PROFILE, measured_from='广州云测 · 100Mbps 服务器')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True)
    p.add_argument('--binary', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--ledger', required=True)
    a = p.parse_args()
    budget = None
    try:
        if os.name != 'nt':
            raise RuntimeError('Windows worker required')
        doc = json.loads(Path(a.input).read_text(encoding='utf-8'))
        if not 1 <= len(doc['nodes']) <= 256:
            raise RuntimeError('source_count_invalid')
        budget = Budget(a.ledger).start()
        result = execute(doc, a.binary, budget)
        budget.close()
        if budget.error:
            raise BudgetExceeded(budget.error)
        result['traffic'] = dict(rx_upper_bound=budget.latest[0] - budget.before[0],
                                 tx_upper_bound=budget.latest[1] - budget.before[1])
        save(a.output, result)
    except Exception as e:
        # Never log upstream configs, credentials, URLs or exception payloads.
        reason = str(e) if isinstance(e, (BudgetExceeded, RuntimeError)) else type(e).__name__
        save(a.output, dict(complete=False, error=reason))
        raise SystemExit('Mainland probe failed; results not published: ' + reason)
    finally:
        if budget is not None:
            budget.close()


if __name__ == '__main__':
    main()
