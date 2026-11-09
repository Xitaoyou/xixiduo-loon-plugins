"""西西多：公开免费节点的保守转换器。只输出节点，不输出规则或 DNS。"""
import base64
from collections import Counter
from datetime import datetime, timezone, timedelta
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs, unquote, urlsplit
from urllib.request import Request, urlopen
import uuid

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

ROOT = Path(__file__).resolve().parents[2]
MIRRORS = (
    'https://raw.githubusercontent.com/pixelor/ecfg/refs/heads/main/data/ecfg6_en',
    'https://cdn.shadowrockets.app/ecfg/data/ecfg6_en',
    'https://files.shadowrockets.app/ecfg/data/ecfg6_en',
)
LIMIT = 8 * 1024 * 1024


def decrypt(payload):
    # 来自公开 APK 的格式常量；不是个人订阅或账号密钥。
    key = b'd3JV8tcWGPzgcVbB'
    raw = base64.b64decode(b''.join(payload.split()), validate=True)
    dec = Cipher(algorithms.AES(key), modes.CBC(key)).decryptor()
    padded = dec.update(raw) + dec.finalize()
    unpad = PKCS7(128).unpadder()
    return (unpad.update(padded) + unpad.finalize()).decode('utf-8-sig')


def safe(value):
    value = str(value)
    if any(ord(c) < 32 or ord(c) == 127 for c in value) or any(c in value for c in '"\\'):
        raise ValueError('unsafe value')
    return '"' + value + '"'


def server(value):
    value = str(value).strip().strip('[]')
    try:
        address = ipaddress.ip_address(value)
        if not address.is_global:
            raise ValueError('non-public address')
        return '[' + value + ']' if address.version == 6 else value
    except ValueError:
        if ':' in value or not re.fullmatch(r'[A-Za-z0-9.-]+', value) or '.' not in value:
            raise ValueError('invalid server')
        if re.fullmatch(r'[0-9.]+', value) or value.lower().endswith(('.local', '.localhost', '.internal')):
            raise ValueError('non-public address')
        return value.lower()


def port(value):
    n = int(value)
    if not 1 <= n <= 65535:
        raise ValueError('invalid port')
    return str(n)


def marked(name):
    return '__LOCKED_V1__' in name or '\u2063' in name or '\u2060' in name


def true(value):
    return str(value).lower() in ('1', 'true')


def convert(line):
    if line.startswith('vmess://'):
        encoded = line[8:]
        d = json.loads(base64.b64decode(encoded + '=' * (-len(encoded) % 4)))
        if marked(str(d.get('ps', ''))) or marked(str(d.get('name', ''))):
            raise ValueError('restricted')
        transport = d.get('net') or 'tcp'
        if transport == 'raw':
            transport = 'tcp'
        if transport not in ('tcp', 'ws') or d.get('type', 'none') not in ('', 'none'):
            raise ValueError('unsupported transport')
        if d.get('tls', '') not in ('', 'none', 'tls'):
            raise ValueError('unsupported tls')
        if any(d.get(k) for k in ('echConfigList', 'echServerKeys', 'xhttp_extra', 'pbk', 'sid')):
            raise ValueError('unsupported options')
        if any(true(d.get(k)) for k in ('insecure', 'allowInsecure', 'skip-cert-verify')):
            raise ValueError('insecure tls')
        cipher = d.get('scy') or 'auto'
        if cipher not in ('auto', 'none', 'aes-128-gcm', 'chacha20-ietf-poly1305', 'aes-128-cfb'):
            raise ValueError('unsupported cipher')
        aid = int(d.get('aid') or 0)
        if aid != 0:
            raise ValueError('legacy vmess')
        uid = str(uuid.UUID(d['id']))
        parts = ['VMess', server(d['add']), port(d['port']), cipher, safe(uid),
                 'transport=' + transport, 'alterId=0']
        if transport == 'ws':
            parts += ['path=' + safe(d.get('path') or '/'), 'host=' + safe(d.get('host') or d['add'])]
        tls = d.get('tls') == 'tls'
        parts += ['over-tls=' + str(tls).lower()]
        if tls:
            parts += ['sni=' + safe(d.get('sni') or d.get('host') or d['add']), 'skip-cert-verify=false']
            # VMess 文档未列出 ALPN 参数，避免悄悄丢失必需设置。
            if d.get('alpn'):
                raise ValueError('unsupported alpn')
        parts += ['udp=true']
    elif line.startswith('hy2://'):
        u = urlsplit(line)
        if marked(unquote(u.fragment)):
            raise ValueError('restricted')
        q = parse_qs(u.query, keep_blank_values=True)
        if any(len(v) != 1 for v in q.values()) or set(q) - {'security', 'sni', 'insecure'}:
            raise ValueError('unsupported options')
        q = {k: v[0] for k, v in q.items()}
        if true(q.get('insecure')):
            raise ValueError('insecure tls')
        if q.get('security', 'tls') not in ('', 'tls'):
            raise ValueError('unsupported tls')
        password = unquote(u.netloc.rsplit('@', 1)[0]) if '@' in u.netloc else ''
        if not password:
            raise ValueError('missing password')
        parts = ['Hysteria2', server(u.hostname), port(u.port or 443), safe(password),
                 'sni=' + safe(q.get('sni') or u.hostname), 'skip-cert-verify=false', 'udp=true']
    else:
        raise ValueError('outside free protocol subset')
    # 连接参数而非名称去重。名称哈希稳定，不暴露原始推广文字。
    body = ','.join(parts)
    identity = hashlib.sha256(body.encode()).hexdigest()
    return identity, parts[0], body


def build(text):
    nodes, rejected = {}, Counter()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        try:
            identity, protocol, body = convert(line)
            nodes[identity] = (protocol, body)
        except (ValueError, KeyError, TypeError, OverflowError):
            rejected['filtered'] += 1
    if len(nodes) < 5:
        raise ValueError('too few compatible nodes; previous subscription retained')
    result = []
    counts = Counter()
    for identity, (protocol, body) in sorted(nodes.items()):
        result.append(f'免费-{protocol}-{identity[:12]} = {body}')
        counts[protocol] += 1
    return '\n'.join(result) + '\n', dict(counts), dict(rejected)


def publish(text, output=ROOT / 'subscriptions/free-nodes.txt'):
    content, counts, rejected = build(text)
    metadata = {'connection_tested': False}
    binary = os.environ.get('SING_BOX_BINARY')
    if binary:
        from health import check
        content, counts, metadata = check(content, binary)
    output = Path(output)
    if output.exists():
        old_count = len(output.read_text(encoding='utf-8').splitlines())
        old_status_path = output.with_suffix('.json')
        old_status = json.loads(old_status_path.read_text(encoding='utf-8')) if old_status_path.exists() else {}
        same_policy = old_status.get('filter_policy') == metadata.get('filter_policy')
        if (not binary or (old_status.get('connection_tested') and same_policy)) and len(content.splitlines()) < old_count * 0.25:
            raise ValueError('abnormal shrink; previous subscription retained')
    output.parent.mkdir(parents=True, exist_ok=True)
    updated_at = datetime.now(timezone.utc)
    if metadata['connection_tested']:
        # 在真实已通过节点上显示时间；不增加占位节点或重复连接。
        lines = content.splitlines()
        local_time = updated_at.astimezone(timezone(timedelta(hours=8)))
        lines[0] = f'🕒 {local_time:%m-%d %H:%M} 更新（北京） · ' + lines[0]
        content = '\n'.join(lines) + '\n'
    tmp = output.with_suffix('.tmp')
    tmp.write_text(content, encoding='utf-8', newline='\n')
    os.replace(tmp, output)
    status = {'updated_at': updated_at.isoformat(),
              'nodes': sum(counts.values()), 'protocols': counts,
              **metadata, 'filtered': rejected.get('filtered', 0)}
    output.with_suffix('.json').write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    # 中文文件名作为导入名称的兼容提示；旧地址继续提供相同内容。
    if output == ROOT / 'subscriptions/free-nodes.txt':
        output.with_name('免费节点').write_text(content, encoding='utf-8', newline='\n')
    print(json.dumps(status, ensure_ascii=True))


def main():
    text = None
    for index, url in enumerate(MIRRORS):
        try:
            with urlopen(Request(url, headers={'User-Agent': 'xixiduo-loon-free-nodes/1.0'}), timeout=25) as response:
                payload = response.read(LIMIT + 1)
            if len(payload) > LIMIT:
                raise ValueError('oversized source')
            text = decrypt(payload)
            build(text)
            break
        except Exception as exc:
            # 不记录响应正文、节点凭据或带参数 URL。
            print(f'Source {index + 1} failed: {type(exc).__name__}', file=sys.stderr)
    if text is None:
        raise SystemExit('All sources failed; previous subscription retained')
    publish(text)


if __name__ == '__main__':
    main()
