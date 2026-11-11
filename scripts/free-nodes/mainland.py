"""Hosted preparation and atomic mainland-only publishing. Never measures overseas."""
import argparse
import base64
from collections import Counter
from datetime import datetime, timezone, timedelta
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
from urllib.request import Request, urlopen
from urllib.parse import urlsplit, parse_qsl, urlencode
import zipfile

from update import decrypt, convert
import health
from pool import identity
import mainland_policy as policy
from export_clients import render

PUBLIC = 'Xitaoyou/xixiduo-loon-plugins'
CONTROL = 'Xitaoyou/xixiduo-cn-probe'
CORE_VERSION = '1.14.4'
CORE_SHA = '99185d75d314a07dbba4a130c8ad986cbeb629a07927975636b341ca61f991df'
HERE = Path(__file__).resolve().parent


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path, default=None):
    return json.loads(Path(path).read_text(encoding='utf-8')) if Path(path).exists() else default


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def api(path, data=None):
    args = ['gh', 'api', path]
    if data is not None:
        args += ['--method', 'PUT', '--input', '-']
    r = subprocess.run(args, input=json.dumps(data) if data is not None else None,
                       capture_output=True, text=True, encoding='utf-8', timeout=45)
    if r.returncode:
        raise RuntimeError('github_api_failed')
    return json.loads(r.stdout)


def remote_json(repo, path, ref='main', optional=False):
    try:
        r = api(f'repos/{repo}/contents/{path}?ref={ref}')
    except RuntimeError:
        # Optional only for the very first installation, not a way to reset history.
        if optional:
            listing = api(f'repos/{repo}/git/trees/{ref}?recursive=1')
            if not any(x['path'] == path for x in listing['tree']):
                return None
        raise
    return json.loads(base64.b64decode(r['content']))


def fetch_bytes(url, limit=64 * 1024 * 1024):
    with urlopen(Request(url, headers={'User-Agent': 'xixiduo-cn-probe'}), timeout=45) as r:
        data = r.read(limit + 1)
    if len(data) > limit:
        raise RuntimeError('download_oversize')
    return data


def normalize_source_uri(line):
    """TCP headerType=none explicitly disables headers; no connection setting is lost."""
    u = urlsplit(line)
    if u.scheme not in ('vless', 'trojan'):
        return line
    query = parse_qsl(u.query, keep_blank_values=True)
    headers = [v for k, v in query if k == 'headerType']
    if headers == ['none']:
        return u._replace(query=urlencode([(k, v) for k, v in query if k != 'headerType'])).geturl()
    return line


def source():
    version = api('repos/pixelor/ecfg/commits/main')['sha']
    tree = api('repos/pixelor/ecfg/git/trees/' + version + '?recursive=1')
    expected = next(x['sha'] for x in tree['tree'] if x['path'] == 'data/ecfg6')
    payload = None
    for url in (f'https://raw.githubusercontent.com/pixelor/ecfg/{version}/data/ecfg6',
                f'https://cdn.jsdelivr.net/gh/pixelor/ecfg@{version}/data/ecfg6',
                'https://cdn.shadowrockets.app/ecfg/data/ecfg6',
                'https://files.shadowrockets.app/ecfg/data/ecfg6'):
        try:
            blob = fetch_bytes(url, 2 * 1024 * 1024)
            if hashlib.sha1(b'blob ' + str(len(blob)).encode() + b'\0' + blob).hexdigest() == expected:
                payload = decrypt(blob)
                break
        except (ValueError, OSError):
            pass
    if payload is None:
        raise RuntimeError('verified_ecfg6_unavailable')
    nodes, rejects = {}, Counter()
    for line in payload.splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        try:
            _, _, body = convert(normalize_source_uri(line.strip()))
            ident = identity(body)
            if ident in nodes:
                rejects['duplicates'] += 1
            nodes[ident] = dict(id=ident, body=body,
                               outbound=health.outbound(body, 'pending', resolve=lambda h: h.strip('[]')))
        except (ValueError, KeyError, TypeError, OverflowError):
            rejects['unsupported_or_restricted'] += 1
    if not 1 <= len(nodes) <= 128:
        raise RuntimeError('ecfg6_count_out_of_range')
    return version, sorted(nodes.values(), key=lambda n: n['id']), dict(rejects)


def combined_source(priority_ids=(), retained=()):
    version, nodes, counts = source()
    merged = {n['id']: n for n in nodes}
    for n in retained:
        merged.setdefault(n['id'], n)
    repo = 'Pawdroid/Free-servers'
    extra_version = api(f'repos/{repo}/commits/main')['sha']
    tree = api(f'repos/{repo}/git/trees/{extra_version}?recursive=1')
    expected = next(x['sha'] for x in tree['tree'] if x['path'] == 'sub')
    blob = fetch_bytes(f'https://raw.githubusercontent.com/{repo}/{extra_version}/sub', 2 * 1024 * 1024)
    if hashlib.sha1(b'blob ' + str(len(blob)).encode() + b'\0' + blob).hexdigest() != expected:
        raise RuntimeError('pawdroid_source_hash_mismatch')
    payload = base64.b64decode(b''.join(blob.split()), validate=True).decode('utf-8')
    counts = dict(counts, ecfg6_unique=len(nodes), pawdroid_added=0, pawdroid_duplicates=0, pawdroid_rejected=0, published_retested=len(retained))
    for line in payload.splitlines():
        if not line.strip():
            continue
        try:
            _, _, body = convert(normalize_source_uri(line.strip()))
            ident = identity(body)
            if ident in merged:
                counts['pawdroid_duplicates'] += 1
                continue
            merged[ident] = dict(id=ident, body=body,
                                outbound=health.outbound(body, 'pending', resolve=lambda h: h.strip('[]')))
            counts['pawdroid_added'] += 1
        except (ValueError, KeyError, TypeError, OverflowError):
            counts['pawdroid_rejected'] += 1
    ecfg_tree = api('repos/pixelor/ecfg/git/trees/' + version + '?recursive=1')
    en_hash = next(x['sha'] for x in ecfg_tree['tree'] if x['path'] == 'data/ecfg6_en')
    en_blob = fetch_bytes(f'https://raw.githubusercontent.com/pixelor/ecfg/{version}/data/ecfg6_en', 2 * 1024 * 1024)
    if hashlib.sha1(b'blob ' + str(len(en_blob)).encode() + b'\0' + en_blob).hexdigest() != en_hash:
        raise RuntimeError('ecfg6_en_source_hash_mismatch')
    extra = {}
    for line in decrypt(en_blob).splitlines():
        try:
            _, _, body = convert(normalize_source_uri(line.strip()))
            ident = identity(body)
            if ident not in merged:
                extra[ident] = dict(id=ident, body=body,
                                    outbound=health.outbound(body, 'pending', resolve=lambda h: h.strip('[]')))
        except (ValueError, KeyError, TypeError, OverflowError):
            pass
    # Fixed daily rotation: bounded work, while different extra nodes get a chance each day.
    ids = sorted(extra)
    day = datetime.now(timezone(timedelta(hours=8))).date().toordinal()
    take = min(128, 256 - len(merged), len(ids))
    priority = sorted(set(priority_ids).intersection(extra))[:min(16, take)]
    chosen = list(priority)
    for i in range(len(ids)):
        if len(chosen) >= take:
            break
        ident = ids[(day * 128 + i) % len(ids)]
        if ident not in chosen:
            chosen.append(ident)
    for ident in chosen:
        merged[ident] = extra[ident]
    counts.update(ecfg6_en_extra_available=len(ids), ecfg6_en_extra_tested=take)
    if len(merged) > 256:
        raise RuntimeError('combined_source_count_out_of_range')
    version = hashlib.sha256((version + ':' + extra_version).encode()).hexdigest()
    return version, sorted(merged.values(), key=lambda n: n['id']), counts


def retained_nodes(previous, content):
    records = previous.get('node_results', [])
    if len(records) > 30:
        raise RuntimeError('retained_node_count_invalid')
    bodies = {line.split(' = ', 1)[0]: line.split(' = ', 1)[1]
              for line in content.splitlines() if ' = ' in line and not line.startswith('#')}
    result = []
    for n in records:
        body = bodies.get(n['name'])
        if body is None or identity(body) != n['id']:
            raise RuntimeError('retained_node_identity_mismatch')
        result.append(dict(id=n['id'], body=body,
                           outbound=health.outbound(body, 'pending', resolve=lambda h: h.strip('[]'))))
    return result


def prepare(folder, smoke=False):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    previous = remote_json(PUBLIC, 'subscriptions/mainland/status.json', optional=True) or {}
    pending = [n['id'] for n in previous.get('node_results', []) if n.get('download_mbps') is None]
    retained = []
    if previous.get('nodes'):
        data = api(f'repos/{PUBLIC}/contents/subscriptions/mainland/free-nodes.txt?ref=main')
        retained = retained_nodes(previous, base64.b64decode(data['content']).decode('utf-8'))
    version, nodes, counts = combined_source(pending, retained)
    state = {}
    if previous.get('cycle'):
        state = remote_json(CONTROL, 'cycles/' + previous['cycle'] + '.json', ref='state')
        if state.get('cycle') != previous['cycle']:
            raise RuntimeError('previous_state_cycle_mismatch')
    cycle = hashlib.sha256((now() + os.environ.get('GITHUB_RUN_ID', 'local') + version).encode()).hexdigest()[:24]
    source_total = len(nodes)
    if smoke:
        nodes = nodes[:3]
    doc = dict(cycle=cycle, source_version=version, source_file='ecfg6 + ecfg6_en (daily rotation) + Pawdroid/sub', nodes=nodes,
               source_counts=counts, source_total=source_total, prepared_at=now(), smoke=smoke,
               previous_cycle=previous.get('cycle'))
    write(folder / 'input.json', doc)
    write(folder / 'previous-state.json', state)
    for name in ('mainland_worker.py', 'mainland_policy.py', 'ai_check.py', 'enrich.py', 'health.py'):
        shutil.copyfile(HERE / name, folder / name)
    filename = f'sing-box-{CORE_VERSION}-windows-amd64'
    blob = fetch_bytes(f'https://github.com/SagerNet/sing-box/releases/download/v{CORE_VERSION}/{filename}.zip')
    if hashlib.sha256(blob).hexdigest() != CORE_SHA:
        raise RuntimeError('core_checksum_failed')
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        (folder / 'sing-box.exe').write_bytes(z.read(filename + '/sing-box.exe'))
    # Install only a fixed ABI3 wheel into the artifact, with no install hook execution.
    wheel_folder = folder / 'wheels'
    subprocess.run(['python', '-m', 'pip', 'download', '--only-binary=:all:', '--no-deps',
                    '--platform', 'win_amd64', '--python-version', '312', '--implementation', 'cp',
                    '--abi', 'cp37m', '--abi', 'abi3', '--dest', str(wheel_folder), 'psutil==7.0.0'],
                   check=True, timeout=120, stdout=subprocess.DEVNULL)
    wheels = list(wheel_folder.glob('psutil-7.0.0-*-win_amd64.whl'))
    if len(wheels) != 1:
        raise RuntimeError('psutil_wheel_missing')
    with zipfile.ZipFile(wheels[0]) as z:
        target = folder / 'site-packages'
        for entry in z.infolist():
            if entry.filename.startswith('psutil/') and not entry.is_dir():
                destination = target / entry.filename
                if '..' in Path(entry.filename).parts:
                    raise RuntimeError('unsafe_wheel_path')
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(z.read(entry))
    shutil.rmtree(wheel_folder)
    print(json.dumps(dict(cycle=cycle, candidates=len(nodes), source_total=source_total, source='ecfg6', smoke=smoke)))


def validate(doc, result):
    if (not result or not result.get('complete') or result.get('cycle') != doc['cycle']
            or result.get('source_version') != doc['source_version']
            or result.get('measurement_profile') != policy.PROFILE):
        raise RuntimeError('incomplete_or_mismatched_result')
    expected = {n['id'] for n in doc['nodes']}
    baseline = result.get('baseline', {})
    if not policy.valid_baseline(baseline.get('before', {}), baseline.get('after', {})):
        if 'download_baseline_unverified' not in result.get('warnings', []) or any(n.get('download_mbps') is not None for n in result.get('results', [])):
            raise RuntimeError('invalid_server_baseline')
    rows = result.get('results', [])
    if len(rows) != len(expected) or {n['id'] for n in rows} != expected:
        raise RuntimeError('missing_candidate_results')
    for n in rows:
        for field in ('download_mbps', 'basic_latency_ms'):
            v = n.get(field)
            if v is not None and (type(v) not in (int, float) or not math.isfinite(v) or v <= 0):
                raise RuntimeError('invalid_measurement')
        if n.get('measurement_profile') != policy.PROFILE:
            raise RuntimeError('mixed_measurement_profile')
    return rows


def render_selection(doc, result, previous):
    rows = validate(doc, result)
    state = policy.update_history(previous, rows, result['tested_at'], doc['cycle'])
    selected = policy.choose(state, rows)
    if not selected:
        raise RuntimeError('no_eligible_nodes')
    bodies = {n['id']: n['body'] for n in doc['nodes']}
    for n in selected:
        n['body'] = bodies[n['id']]
    picks = policy.recommendations(selected)
    groups = [(key, labels, picks[key]) for key, labels in (
        ('ai', ('AI解锁丨', '备选AI解锁丨')),
        ('gpt', ('GPT 解锁|',)), ('gemini', ('Gemini解锁|',)),
        ('media', ('流媒体推荐',)), ('download', ('下载推荐', '备选下载')),
        ('daily', ('日常推荐',)))]
    content, counts, meta = health.render_results(selected, rows, len(rows), 0,
                                                selected_only=True, picks=picks, eligibility=policy.latency_eligible,
                                                recommendation_groups=groups)
    stamp = datetime.fromisoformat(result['tested_at']).astimezone(timezone(timedelta(hours=8)))
    lines = content.splitlines()
    lines = [f'西西多大陆用免费节点：{stamp:%m-%d %H:%M}（北京时间） = ' + selected[0]['body']] + lines
    content = '\n'.join(lines) + '\n'
    clash, rocket = render(content, title='免费节点大陆版')
    meta.update(updated_at=result['tested_at'], cycle=doc['cycle'], nodes=len(selected),
                published_rows=len(lines), source_version=doc['source_version'], source_file=doc.get('source_file', 'ecfg6'),
                source_counts=doc.get('source_counts', {}),
                checked=len(rows), tested_from='广州云测 · 100Mbps 服务器',
                measurement_profile=policy.PROFILE, country_limit=None, node_limit=30,
                filter_policy='mainland-latency1500-country2500-retained-v4', sort_by='latency, measured throughput',
                selection_tier='latency',
                thresholds={'basic_ms_max': 1500, 'country_fallback_ms_max': 2500, 'ai_pass_min': 0},
                preferred_countries=list(policy.PREFERRED_COUNTRIES),
                country_fallback_nodes=sum(n.get('selection_tier') == 'country_fallback' for n in selected),
                ai_min_pass=0, ai_rejected=0,
                unreachable=sum(n.get('status') != 'alive' for n in rows),
                latency_qualified=sum(policy.eligible(n) for n in rows),
                latency_rejected=sum(n.get('status') == 'alive' and not policy.eligible(n) for n in rows),
                ai_qualified=sum(n.get('ai', {}).get('pass_count', 0) >= 2 for n in rows),
                test_method='Verified proxy HTTPS; latency <=1500ms, common-country fallback <=2500ms; AI, media and download measured independently',
                server_baseline=result['baseline'], warnings=result.get('warnings', []),
                pending_download=sum(n.get('download_mbps') is None for n in selected),
                last_attempt={'at': now(), 'ok': True}, traffic=result.get('traffic', {}),
                selection_phase='stable' if all(n['stable'] for n in selected) else 'observation')
    state['cycle'] = doc['cycle']
    return {'free-nodes.txt': content, '免费节点大陆版': content,
            'free-nodes-clash.yaml': clash, 'free-nodes-shadowrocket.txt': rocket,
            'status.json': json.dumps(meta, ensure_ascii=False, indent=2) + '\n'}, state


def persist_state(state):
    # Immutable state snapshot first; public status points to it only after atomic public commit.
    try:
        api(f'repos/{CONTROL}/git/ref/heads/state')
    except RuntimeError:
        sha = api(f'repos/{CONTROL}/git/ref/heads/main')['object']['sha']
        r = subprocess.run(['gh', 'api', '--method', 'POST', f'repos/{CONTROL}/git/refs', '--input', '-'],
                           input=json.dumps({'ref': 'refs/heads/state', 'sha': sha}),
                           capture_output=True, text=True, timeout=45)
        if r.returncode:
            raise RuntimeError('state_branch_unavailable')
    path = 'cycles/' + state['cycle'] + '.json'
    existing = remote_json(CONTROL, path, ref='state', optional=True)
    if existing is not None:
        if existing != state:
            raise RuntimeError('immutable_state_conflict')
        return
    api(f'repos/{CONTROL}/contents/{path}', dict(message='Persist mainland cycle ' + state['cycle'],
        branch='state', content=base64.b64encode(json.dumps(state).encode()).decode()))


def commit_files(repo, files):
    folder = Path(repo) / 'subscriptions/mainland'
    folder.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (folder / name).write_text(content, encoding='utf-8', newline='\n')
    def git(*args):
        subprocess.run(['git', '-C', str(repo), *args], check=True, timeout=60,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    git('config', 'user.name', 'github-actions[bot]')
    git('config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
    git('add', 'subscriptions/mainland')
    changed = subprocess.run(['git', '-C', str(repo), 'diff', '--cached', '--quiet']).returncode
    if not changed:
        return
    git('commit', '-m', 'chore: update mainland node results')
    for attempt in range(3):
        try:
            git('push', 'origin', 'HEAD:main')
            return
        except subprocess.CalledProcessError:
            if attempt == 2:
                raise RuntimeError('publication_conflict')
            git('pull', '--rebase', 'origin', 'main')


def finish(folder, result_path, repo, smoke=False):
    doc = read(Path(folder) / 'input.json')
    result = read(result_path)
    if smoke:
        rows = validate(doc, result)
        if not any(n['status'] == 'alive' for n in rows):
            raise RuntimeError('smoke_no_reachable_node')
        render_selection(doc, result, {})
        print('Three-node smoke test completed; no subscriptions or history changed.')
        return
    if doc.get('smoke'):
        raise RuntimeError('smoke_result_cannot_publish')
    current = read(Path(repo) / 'subscriptions/mainland/status.json', {})
    if current.get('cycle') != doc.get('previous_cycle'):
        raise RuntimeError('publication_base_changed')
    try:
        files, state = render_selection(doc, result, read(Path(folder) / 'previous-state.json', {}))
    except Exception as e:
        reason = str(e) if isinstance(e, RuntimeError) else 'invalid_results'
        current['last_attempt'] = dict(at=now(), ok=False, reason=reason)
        commit_files(repo, {'status.json': json.dumps(current, ensure_ascii=False, indent=2) + '\n'})
        raise RuntimeError(reason)
    persist_state(state)
    commit_files(repo, files)
    print('Published complete mainland cycle ' + doc['cycle'])


def report_failure(repo, reason):
    status = read(Path(repo) / 'subscriptions/mainland/status.json', {})
    status['last_attempt'] = dict(at=now(), ok=False, reason=reason)
    commit_files(repo, {'status.json': json.dumps(status, ensure_ascii=False, indent=2) + '\n'})


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['prepare', 'finish', 'failure'])
    p.add_argument('--folder', default='bundle')
    p.add_argument('--result', default='result/result.json')
    p.add_argument('--repo', default='public')
    p.add_argument('--smoke', action='store_true')
    p.add_argument('--reason', choices=['source_preparation_failed', 'worker_failed'], default='worker_failed')
    a = p.parse_args()
    if a.command == 'prepare':
        prepare(a.folder, a.smoke)
    elif a.command == 'finish':
        finish(a.folder, a.result, a.repo, a.smoke)
    else:
        report_failure(a.repo, a.reason)
