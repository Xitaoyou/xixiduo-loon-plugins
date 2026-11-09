"""通过独立本地代理入口逐节点验证 HTTPS，并读取实际出口国家。"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile
import time
from ai_check import check_ai, POLICY
from enrich import quality, quality_key, check_media, download, select, country_best, download_best, measured_name, qualified, clean_ip_best

TARGETS = ('https://www.cloudflare.com/cdn-cgi/trace',
           'https://one.one.one.one/cdn-cgi/trace')
COUNTRIES = dict(US='美国', JP='日本', HK='香港', TW='台湾', SG='新加坡', KR='韩国',
                 DE='德国', GB='英国', FR='法国', NL='荷兰', CA='加拿大', AU='澳大利亚',
                 RU='俄罗斯', IN='印度', VN='越南', TH='泰国', MY='马来西亚', ID='印度尼西亚',
                 PH='菲律宾', TR='土耳其', FI='芬兰', SE='瑞典', NO='挪威', CH='瑞士',
                 PL='波兰', IT='意大利', ES='西班牙', BR='巴西', ZA='南非', AE='阿联酋',
                 CN='中国', MO='澳门', IE='爱尔兰', AT='奥地利', BE='比利时', CZ='捷克',
                 RO='罗马尼亚', UA='乌克兰', IL='以色列', NZ='新西兰', AR='阿根廷', MX='墨西哥')


def parse_body(body):
    values = re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', body)
    head, options = [], {}
    for value in values:
        if '=' in value and len(head) >= (5 if values[0] == 'VMess' else 4):
            key, val = value.split('=', 1)
            options[key] = json.loads(val) if val.startswith('"') else val
        else:
            head.append(json.loads(value) if value.startswith('"') else value)
    return head, options


def public_ip(host):
    """先解析并固定公开 IP，避免核心再次解析到内网；SNI/WS Host 保持原值。"""
    host = host.strip('[]')
    addresses = sorted({item[4][0] for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)},
                       key=lambda value: (':' in value, value))
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise ValueError('non-public endpoint')
    return addresses[0]


def outbound(body, tag, resolve=public_ip):
    head, opt = parse_body(body)
    kind, host, port = head[:3]
    result = dict(type='vmess' if kind == 'VMess' else 'hysteria2', tag=tag,
                  server=resolve(host), server_port=int(port), connect_timeout='8s')
    if kind == 'VMess':
        if head[3] == 'aes-128-cfb':
            raise ValueError('legacy cipher unsupported by test core')
        result.update(uuid=head[4], security=head[3], alter_id=int(opt['alterId']))
        if opt['transport'] == 'ws':
            result['transport'] = dict(type='ws', path=opt['path'], headers={'Host': opt['host']})
        if opt['over-tls'] == 'true':
            result['tls'] = dict(enabled=True, server_name=opt['sni'], insecure=False)
    else:
        result.update(password=head[3], tls=dict(enabled=True, server_name=opt['sni'], insecure=False))
    return result


def parse_trace(text):
    if len(text) > 4096:
        raise ValueError('oversized response')
    fields = dict(line.split('=', 1) for line in text.splitlines() if '=' in line)
    ip = ipaddress.ip_address(fields.get('ip', ''))
    country = fields.get('loc', '')
    if not ip.is_global or not re.fullmatch('[A-Z]{2}', country):
        raise ValueError('invalid trace')
    return country


def request_trace(proxy_port=None, target=TARGETS[0], details=False):
    env = {k: v for k, v in os.environ.items() if k.lower() not in
           ('http_proxy', 'https_proxy', 'all_proxy', 'no_proxy')}
    # -q 禁用 .curlrc，明确禁止环境代理和 direct fallback，不跟随重定向。
    command = ['curl', '-q', '--silent', '--fail', '--max-time', '10',
               '--connect-timeout', '7', '--max-filesize', '4096', '--noproxy', '',
               '--proxy', f'http://127.0.0.1:{proxy_port}' if proxy_port else '', target]
    proc = subprocess.run(command, capture_output=True, text=True, timeout=13, env=env)
    if proc.returncode:
        raise ValueError('proxy request failed')
    country = parse_trace(proc.stdout)
    if details:
        fields = dict(line.split('=', 1) for line in proc.stdout.splitlines() if '=' in line)
        return dict(country=country, ip=fields['ip'])
    return country


def country_label(code):
    flag = ''.join(chr(127397 + ord(char)) for char in code)
    return flag + ' ' + COUNTRIES.get(code, code)


def check(content, binary):
    started = time.monotonic()
    lines = content.splitlines()
    if len(lines) > 512:
        raise ValueError('unexpected candidate count')
    # 检测站整体不可达时不清空订阅。
    request_trace()
    candidates, skipped = [], 0
    for line in lines:
        name, body = line.split(' = ', 1)
        try:
            tag = 'node-' + str(len(candidates))
            candidates.append((name, body, outbound(body, tag)))
        except (ValueError, OSError, KeyError):
            skipped += 1
    if not candidates:
        raise ValueError('no public candidates')
    config = {'log': {'disabled': True}, 'inbounds': [], 'outbounds': [],
              'route': {'rules': []}}
    for index, (_, _, out) in enumerate(candidates):
        inbound = 'in-' + str(index)
        config['inbounds'].append(dict(type='mixed', tag=inbound, listen='127.0.0.1', listen_port=20000 + index))
        config['outbounds'].append(out)
        config['route']['rules'].append(dict(inbound=[inbound], action='route', outbound=out['tag']))
    with tempfile.TemporaryDirectory(prefix='loon-health-') as directory:
        path = Path(directory) / 'config.json'
        path.write_text(json.dumps(config), encoding='utf-8')
        path.chmod(0o600)
        validated = subprocess.run([binary, 'check', '-c', str(path)], capture_output=True, timeout=20)
        if validated.returncode:
            raise ValueError('proxy core configuration rejected')
        core = subprocess.Popen([binary, 'run', '-c', str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 8
            while True:
                if core.poll() is not None:
                    raise ValueError('proxy core stopped')
                try:
                    with socket.create_connection(('127.0.0.1', 20000), timeout=0.2):
                        break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise ValueError('proxy core not ready')
                    time.sleep(0.1)

            def probe(item):
                index, (name, body, _) = item
                code = None
                for target in TARGETS:
                    try:
                        code = request_trace(20000 + index, target, details=True)
                        break
                    except (ValueError, OSError, subprocess.SubprocessError):
                        pass
                if not code:
                    return None
                ai = check_ai(20000 + index)
                return dict(country=code['country'], exit_ip=code['ip'], id=name.rsplit('-', 1)[-1][:8],
                            body=body, ai=ai, port=20000 + index)

            with ThreadPoolExecutor(max_workers=4) as pool:
                reachable = [item for item in pool.map(probe, enumerate(candidates)) if item]
            passed = [node for node in reachable if node['ai']['passed']]
            print(json.dumps({'stage':'AI complete','reachable':len(reachable),'ai_passed':len(passed)}), flush=True)

            def enrich(node):
                node['quality'] = quality(node['exit_ip'])
                node['media'] = check_media(node['port'])
                node['download_mbps'] = download(node['port'])
                return node

            with ThreadPoolExecutor(max_workers=4) as pool:
                passed = list(pool.map(enrich, passed))
        finally:
            core.terminate()
            try:
                core.wait(timeout=5)
            except subprocess.TimeoutExpired:
                core.kill()
                core.wait()
    if not passed:
        raise ValueError('no node passed at least two AI probes; previous subscription retained')
    output, counts = [], Counter()
    countries = Counter()
    node_results = []
    eligible = [n for n in passed if qualified(n)]
    if not eligible:
        raise ValueError('no quality-qualified measured candidates; previous subscription retained')
    best = country_best(eligible)
    ai_picks, media_picks = select(eligible)
    download_picks = download_best(eligible)
    clean_picks = clean_ip_best(eligible)
    # 推荐可以超出同国综合最优项；其余普通条目不再发布。
    retained = {n['id']:n for n in best + ai_picks + media_picks + download_picks + clean_picks}
    country_best_ids = {n['id'] for n in best}
    selected_order = {n['id']:index for index,n in enumerate(best)}
    country_numbers = Counter()
    for node in sorted(retained.values(), key=lambda n: (n['country'], n['id'] not in country_best_ids, selected_order.get(n['id'],0), n['id'])):
        code, body, ai = node['country'], node['body'], node['ai']
        protocol = body.split(',', 1)[0]
        country_numbers[code] += 1
        node['name'] = measured_name(f'{country_label(code)} {country_numbers[code]:02d}', node)
        if node['id'] in country_best_ids:
            output.append(f'{node["name"]} = {body}')
        node_results.append(dict(id=node['id'], name=node['name'], country=code, **ai,
                                 quality=node['quality'], media=node['media'], download_mbps=node['download_mbps']))
        counts[protocol] += 1
        countries[code] += 1
    aliases, recommendations = [], {}
    for category, labels, picks in (('ai', ('AI推荐', '备选AI'), ai_picks),
                                     ('media', ('流媒体推荐', '备选流媒体'), media_picks),
                                     ('download', ('下载推荐',), download_picks),
                                     ('clean_ip', ('纯净IP推荐',), clean_picks)):
        recommendations[category] = []
        for label, node in zip(labels, picks):
            aliases.append(f'{label}：{node["name"]} = {node["body"]}')
            recommendations[category].append(dict(label=label, node=node['name'], id=node['id']))
    output = aliases + output
    metadata = dict(connection_tested=True, test_method='HTTPS trace and at least 2 of ChatGPT/Claude/Gemini; TLS verified',
                    tested_from='GitHub Actions runner', candidates=len(lines),
                    unreachable=len(candidates) - len(reachable), endpoint_rejected=skipped,
                    ai_rejected=len(reachable) - len(passed), ai_min_pass=2, filter_policy=POLICY+'-country-top4-quality-v1',
                    sort_by='up to 4 quality-qualified distinct exits per country: quality then latency; preserve recommendations',
                    ai_qualified=len(passed),quality_qualified=len(eligible), quality_rejected=len(passed)-len(eligible),
                    country_best_count=len(best),country_limit=4,country_count=len({n['country'] for n in best}),
                    recommendations=recommendations, recommendation_rows=len(aliases),
                    media_required=['Netflix','Disney+','YouTube Premium','Prime Video'],
                    media_all_passed=sum(n['media']['all_passed'] for n in passed),
                    media_service_passes={k:sum(n['media']['services'][k] for n in passed) for k in ('Netflix','Disney+','YouTube Premium','Prime Video')},
                    quality_labels=dict(Counter(n['quality']['label'] for n in passed)),
                    node_results=node_results,
                    countries=dict(countries), test_seconds=round(time.monotonic() - started, 1))
    return '\n'.join(output) + '\n', dict(counts), metadata
