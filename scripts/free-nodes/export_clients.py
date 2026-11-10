"""从同一份已检测的 Loon 订阅导出 Clash Meta 和 Shadowrocket 格式。"""
import base64
import json
from pathlib import Path
from urllib.parse import quote, urlencode

from health import parse_body

ROOT = Path(__file__).resolve().parents[2]


def convert(name, body):
    head, opt = parse_body(body)
    kind, host, port = head[:3]
    if kind != 'VMess':
        from protocols import export
        return export(name,body)
    host = host.strip('[]')
    proxy = dict(name=name, type='vmess' if kind == 'VMess' else 'hysteria2', server=host, port=int(port), udp=True)
    if kind == 'VMess':
        tls = opt['over-tls'] == 'true'
        proxy.update(uuid=head[4], alterId=int(opt['alterId']),
                     cipher={'chacha20-ietf-poly1305':'chacha20-poly1305'}.get(head[3], head[3]), network=opt['transport'], tls=tls)
        vmess = dict(v='2', ps=name, add=host, port=str(port), id=head[4], aid=opt['alterId'],
                     scy=head[3], net=opt['transport'], type='none', host=opt.get('host',''),
                     path=opt.get('path',''), tls='tls' if tls else '', sni=opt.get('sni',''))
        if tls:
            proxy.update(servername=opt['sni'], **{'skip-cert-verify':False})
            if opt.get('tls-profile'):
                vmess['fp']='safari' if opt['tls-profile'].startswith('safari') else 'chrome'
                proxy['client-fingerprint']=vmess['fp']
        if opt['transport'] == 'ws':
            proxy['ws-opts'] = {'path':opt['path'], 'headers':{'Host':opt['host']}}
        uri = 'vmess://' + base64.b64encode(json.dumps(vmess,ensure_ascii=False,separators=(',',':')).encode()).decode()
    elif kind == 'Hysteria2':
        proxy.update(password=head[3], sni=opt['sni'], **{'skip-cert-verify':False})
        authority = '[' + host + ']' if ':' in host else host
        uri = f'hysteria2://{quote(head[3],safe="")}@{authority}:{port}?' + urlencode({'sni':opt['sni'],'insecure':'0'}) + '#' + quote(name,safe='')
    else:
        raise ValueError('unsupported export protocol')
    return proxy, uri


def render(content, allow_empty=False, title='免费节点'):
    proxies, uris = [], []
    for line in content.splitlines():
        if not line or line.startswith('#'):
            continue
        name, body = line.split(' = ',1)
        proxy, uri = convert(name,body)
        proxies.append(proxy)
        uris.append(uri)
    if (not proxies and not allow_empty) or len({p['name'] for p in proxies}) != len(proxies):
        raise ValueError('invalid export names or empty source')
    # JSON flow objects are valid YAML; use safe serialization instead of string interpolation.
    dump = lambda value: json.dumps(value,ensure_ascii=False,separators=(',',':'))
    yaml = 'mixed-port: 7890\nallow-lan: false\nmode: rule\nlog-level: warning\nproxies:\n'
    if not proxies: yaml = yaml.removesuffix('proxies:\n') + 'proxies: []\n'
    yaml += ''.join('  - ' + dump(p) + '\n' for p in proxies)
    yaml += 'proxy-groups:\n  - ' + dump({'name':title,'type':'select','proxies':['DIRECT']+[p['name'] for p in proxies]}) + '\n'
    yaml += 'rules:\n  - ' + dump('MATCH,' + title) + '\n'
    return yaml, base64.b64encode(('\n'.join(uris)+'\n').encode()).decode() + '\n'


def write_exports(content, folder=ROOT/'subscriptions', title='免费节点'):
    clash, shadowrocket = render(content, allow_empty=True, title=title)
    Path(folder).mkdir(parents=True,exist_ok=True)
    (Path(folder)/'free-nodes-clash.yaml').write_text(clash,encoding='utf-8',newline='\n')
    (Path(folder)/'free-nodes-shadowrocket.txt').write_text(shadowrocket,encoding='utf-8',newline='\n')


def brand_overseas(content, metadata):
    def brand(name):
        return name if name.startswith('海外测｜') else '海外测｜' + name
    lines = [brand(line.split(' = ', 1)[0]) + ' = ' + line.split(' = ', 1)[1]
             if ' = ' in line and not line.startswith('#') else line for line in content.splitlines()]
    for n in metadata.get('node_results', []):
        n['name'] = brand(n['name'])
    for group in metadata.get('recommendations', {}).values():
        for n in group:
            n['node'] = brand(n['node'])
    metadata['edition'] = 'overseas'
    metadata['subscription_name'] = '免费节点海外版'
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    path = ROOT/'subscriptions/free-nodes.txt'
    metadata = json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
    content = brand_overseas(path.read_text(encoding='utf-8'), metadata)
    for name in ('free-nodes.txt', '免费节点', '免费节点海外版'):
        path.with_name(name).write_text(content, encoding='utf-8', newline='\n')
    path.with_suffix('.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    write_exports(content, title='免费节点海外版')
