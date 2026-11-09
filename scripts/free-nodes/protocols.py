"""三端共同支持的协议适配；不忽略未知的必需连接参数。"""
import base64
import json
import re
import uuid
from urllib.parse import urlsplit, parse_qs, unquote, quote, urlencode

SS_CIPHERS = {'aes-128-gcm','aes-256-gcm','chacha20-ietf-poly1305','2022-blake3-aes-128-gcm','2022-blake3-aes-256-gcm'}
PROFILES = {'chrome','safari-ios18'}


def b64(value):
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4)).decode('utf-8')


def parse(line):
    from update import safe, server, port, marked, true
    scheme = line.split('://',1)[0]
    if scheme == 'ss' and '@' not in line.split('#',1)[0]:
        line = 'ss://' + b64(line[5:].split('#',1)[0].split('?',1)[0]) + ('#'+line.split('#',1)[1] if '#' in line else '')
    u = urlsplit(line)
    if marked(unquote(u.fragment)):
        raise ValueError('restricted')
    q = parse_qs(u.query,keep_blank_values=True)
    if any(len(v)!=1 for v in q.values()):
        raise ValueError('duplicate options')
    q = {k:v[0] for k,v in q.items()}
    known = {'type','security','sni','peer','allowInsecure','insecure','skip-cert-verify','fp','pbk','sid','flow','host','path','alpn','encryption','plugin','obfs','obfs-password','mport','ports','name','remarks','remark','group'}
    if set(q)-known:
        raise ValueError('unsupported options')
    if any(true(q.get(k)) for k in ('insecure','allowInsecure','skip-cert-verify')):
        raise ValueError('insecure tls')
    transport = q.get('type') or 'tcp'
    if transport == 'raw': transport='tcp'
    if transport not in ('tcp','ws'):
        raise ValueError('unsupported transport')
    kind = {'vless':'VLESS','trojan':'Trojan','hy2':'Hysteria2','hysteria2':'Hysteria2','ss':'Shadowsocks'}[scheme]
    shared={'security','sni','peer','insecure','allowInsecure','skip-cert-verify','name','remarks','remark','group'}
    allowed=shared | ({'type','host','path','fp','pbk','sid','flow','encryption'} if kind=='VLESS' else {'type','host','path','fp','alpn'} if kind=='Trojan' else {'alpn','obfs','obfs-password'} if kind=='Hysteria2' else {'plugin'})
    if set(q)-allowed: raise ValueError('unsupported protocol options')
    host = server(u.hostname)
    head = [kind,host,port(u.port or 443)]
    auth = unquote(u.netloc.rsplit('@',1)[0])
    options = {}
    if kind == 'Shadowsocks':
        if ':' not in auth: auth=b64(auth)
        cipher,password=auth.split(':',1)
        if cipher not in SS_CIPHERS: raise ValueError('unsupported cipher')
        head += [cipher,safe(password)]
        if set(q)-{'plugin','name','remarks','remark','group'}: raise ValueError('unsupported SS options')
        if q.get('plugin'):
            plugin=q['plugin'].split(';'); opts=dict(x.split('=',1) for x in plugin[1:] if '=' in x)
            if plugin[0] not in ('obfs-local','simple-obfs') or set(opts)-{'obfs','obfs-host'} or opts.get('obfs') not in ('http','tls'):
                raise ValueError('unsupported SS plugin')
            if any('=' not in x for x in plugin[1:]): raise ValueError('unsupported SS plugin')
            options.update({'obfs-name':opts['obfs'],'obfs-host':opts.get('obfs-host',u.hostname)})
    else:
        if not auth: raise ValueError('missing credential')
        if kind=='VLESS': auth=str(uuid.UUID(auth))
        head += [safe(auth)]
        tls=q.get('security') or ('none' if kind=='VLESS' else 'tls')
        if tls not in ('none','tls','reality'): raise ValueError('unsupported tls')
        if kind=='VLESS' and q.get('encryption','none')!='none': raise ValueError('unsupported VLESS encryption')
        if kind in ('Trojan','Hysteria2') and tls=='none': raise ValueError('TLS required')
        if kind!='Hysteria2': options['transport']=transport
        if transport=='ws':
            if kind=='Hysteria2' or tls=='reality': raise ValueError('unsupported transport')
            options.update(path=q.get('path') or '/',host=q.get('host') or u.hostname)
        if kind=='VLESS':
            options['over-tls']=str(tls!='none').lower()
            if q.get('flow'):
                if q['flow']!='xtls-rprx-vision' or transport!='tcp' or tls=='none': raise ValueError('unsupported flow')
                options['flow']=q['flow']
        elif q.get('flow'): raise ValueError('unsupported flow')
        if tls!='none':
            options.update(sni=q.get('sni') or q.get('peer') or q.get('host') or u.hostname, **{'skip-cert-verify':'false'})
            if q.get('fp'):
                profile={'chrome':'chrome','safari':'safari-ios18'}.get(q['fp'],q['fp'])
                if profile not in PROFILES: raise ValueError('unsupported fingerprint')
                options['tls-profile']=profile
            if q.get('alpn'):
                if kind=='VLESS': raise ValueError('ALPN not portable for VLESS')
                options['alpn']=q['alpn']
            if tls=='reality':
                if kind!='VLESS' or not q.get('pbk'): raise ValueError('invalid reality')
                if not re.fullmatch(r'[A-Za-z0-9_-]{43}',q['pbk']) or not re.fullmatch(r'(?:[0-9a-fA-F]{2}){0,8}',q.get('sid','')): raise ValueError('invalid reality key')
                options.update({'public-key':q['pbk'],'short-id':q.get('sid',''),'tls-profile':options.get('tls-profile','chrome')})
            elif q.get('pbk') or q.get('sid'): raise ValueError('unexpected reality options')
        if kind=='Hysteria2':
            if q.get('obfs'):
                if q['obfs']!='salamander' or not q.get('obfs-password'): raise ValueError('unsupported obfs')
                options['salamander-password']=q['obfs-password']
            if q.get('mport') or q.get('ports'): raise ValueError('port hopping not portable')
    options['udp']='true'
    bare={'udp','transport','over-tls','skip-cert-verify','flow','tls-profile','obfs-name'}
    return ','.join(head+[k+'='+(v if k in bare else safe(v)) for k,v in sorted(options.items())])


def core(body,tag,resolve):
    from health import parse_body
    h,o=parse_body(body);kind,host,port=h[:3]
    out=dict(type={'VLESS':'vless','Trojan':'trojan','Shadowsocks':'shadowsocks','Hysteria2':'hysteria2'}[kind],tag=tag,server=resolve(host),server_port=int(port),connect_timeout='8s')
    if kind=='VLESS':
        out['uuid']=h[3]
        if o.get('flow'):out['flow']=o['flow']
    elif kind=='Shadowsocks':
        out.update(method=h[3],password=h[4])
        if o.get('obfs-name'):out.update(plugin='obfs-local',plugin_opts='obfs='+o['obfs-name']+';obfs-host='+o['obfs-host'])
    else: out['password']=h[3]
    if o.get('transport')=='ws':out['transport']={'type':'ws','path':o['path'],'headers':{'Host':o['host']}}
    if o.get('sni'):
        tls={'enabled':True,'server_name':o['sni'],'insecure':False}
        if o.get('alpn'):tls['alpn']=o['alpn'].split(',')
        if o.get('tls-profile'):tls['utls']={'enabled':True,'fingerprint':'safari' if o['tls-profile'].startswith('safari') else 'chrome'}
        if o.get('public-key'):tls['reality']={'enabled':True,'public_key':o['public-key'],'short_id':o['short-id']}
        out['tls']=tls
    if o.get('salamander-password'):out['obfs']={'type':'salamander','password':o['salamander-password']}
    return out


def export(name,body):
    from health import parse_body
    h,o=parse_body(body);kind,host,port=h[:3];host=host.strip('[]')
    p=dict(name=name,type={'VLESS':'vless','Trojan':'trojan','Shadowsocks':'ss','Hysteria2':'hysteria2'}[kind],server=host,port=int(port),udp=True)
    address=('['+host+']' if ':' in host else host)+':'+str(port)
    if kind=='Shadowsocks':
        p.update(cipher=h[3],password=h[4]);auth=base64.urlsafe_b64encode((h[3]+':'+h[4]).encode()).decode().rstrip('=');q={}
        if o.get('obfs-name'):
            p.update(plugin='obfs',**{'plugin-opts':{'mode':o['obfs-name'],'host':o['obfs-host']}})
            q['plugin']='obfs-local;obfs='+o['obfs-name']+';obfs-host='+o['obfs-host']
        uri='ss://'+auth+'@'+address+('?' + urlencode(q) if q else '')
    else:
        scheme={'VLESS':'vless','Trojan':'trojan','Hysteria2':'hysteria2'}[kind]
        p['uuid' if kind=='VLESS' else 'password']=h[3]
        q={}
        if kind!='Hysteria2':p['network']=o.get('transport','tcp');q['type']=p['network']
        if kind=='VLESS':p['tls']=o.get('over-tls')=='true';q['encryption']='none'
        if o.get('sni'):
            p['servername' if kind=='VLESS' else 'sni']=o['sni'];p['skip-cert-verify']=False
            q.update(sni=o['sni'],security='reality' if o.get('public-key') else 'tls')
        if o.get('transport')=='ws':p['ws-opts']={'path':o['path'],'headers':{'Host':o['host']}};q.update(path=o['path'],host=o['host'])
        if o.get('flow'):p['flow']=o['flow'];q['flow']=o['flow']
        if o.get('public-key'):p['reality-opts']={'public-key':o['public-key'],'short-id':o['short-id']};q.update(pbk=o['public-key'],sid=o['short-id'])
        if o.get('tls-profile'):
            fp='safari' if o['tls-profile'].startswith('safari') else 'chrome';p['client-fingerprint']=fp;q['fp']=fp
        if o.get('alpn'):p['alpn']=o['alpn'].split(',');q['alpn']=o['alpn']
        if o.get('salamander-password'):p.update(obfs='salamander',**{'obfs-password':o['salamander-password']});q.update(obfs='salamander',**{'obfs-password':o['salamander-password']})
        uri=scheme+'://'+quote(h[3],safe='')+'@'+address+('?' + urlencode(q) if q else '')
    return p,uri+'#'+quote(name,safe='')
