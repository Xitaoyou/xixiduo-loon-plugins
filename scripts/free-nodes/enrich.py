# SPDX-License-Identifier: GPL-3.0-or-later
# 西西多；流媒体端点判据改编自 FlClash，许可证见 ../service-check/COPYING。
from functools import lru_cache
import ipaddress
import json
import os
import re
import statistics
import subprocess
from urllib.parse import urlencode
from urllib.request import build_opener, ProxyHandler, Request

from ai_check import fetch, blocked

MEDIA = ('Netflix', 'Disney+', 'YouTube Premium', 'Prime Video')
# Disney 浏览器公开客户端标识，不是个人账户令牌。
DISNEY_AUTH = 'Bearer ZGlzbmV5JmJyb3dzZXImMS4wLjA.Cu56AgSfBTDag5NiRA81oLHkDZfu5L3CKadnefEAY84'


def good(response):
    return 200 <= response['code'] < 300 and not blocked(response['body'])


def netflix(port):
    # 要求两个非自制剧页面都正常返回片目特征；不把 fast.com 可达当成解锁。
    for title in ('81280792', '70143836'):
        r = fetch(port, 'https://www.netflix.com/title/' + title)
        if not good(r) or title not in r['body'] or not re.search(r'"@type"\s*:\s*"(?:TVSeries|Movie|TVEpisode)"', r['body']):
            return False
    return True


def disney(port):
    headers = {'authorization': DISNEY_AUTH, 'content-type': 'application/json; charset=UTF-8'}
    r = fetch(port, 'https://disney.api.edge.bamgrid.com/devices', headers,
              json.dumps(dict(deviceFamily='browser', applicationRuntime='chrome', deviceProfile='windows', attributes={})))
    if not good(r):
        return False
    assertion = json.loads(r['body']).get('assertion')
    if not isinstance(assertion, str) or not assertion:
        return False
    headers = {**headers, 'content-type': 'application/x-www-form-urlencoded'}
    data = urlencode(dict(grant_type='urn:ietf:params:oauth:grant-type:token-exchange', latitude=0, longitude=0,
                          platform='browser', subject_token=assertion, subject_token_type='urn:bamtech:params:oauth:token-type:device'))
    r = fetch(port, 'https://disney.api.edge.bamgrid.com/token', headers, data)
    if not good(r) or 'forbidden-location' in r['body']:
        return False
    token = json.loads(r['body']).get('refresh_token')
    if not isinstance(token, str) or not token:
        return False
    data = json.dumps({'query': 'mutation refreshToken($input: RefreshTokenInput!) { refreshToken(refreshToken: $input) { activeSession { sessionId } } }',
                       'variables': {'input': {'refreshToken': token}}})
    r = fetch(port, 'https://disney.api.edge.bamgrid.com/graph/v1/device/graphql',
              {**headers, 'content-type': 'application/json'}, data)
    return good(r) and bool(re.search(r'"inSupportedLocation"\s*:\s*true', r['body'])) and bool(re.search(r'"countryCode"\s*:\s*"[A-Z]{2}"', r['body']))


def youtube(port):
    r = fetch(port, 'https://www.youtube.com/premium?hl=en')
    text = r['body'].lower()
    return good(r) and not any(x in text for x in ('premium is not available in your country', 'premium is not available in your region')) and any(x in text for x in ('youtube premium', 'ad-free', '"browseid":"spunlimited"'))


def prime(port):
    r = fetch(port, 'https://www.primevideo.com')
    return good(r) and bool(re.search(r'"currentTerritory"\s*:\s*"[A-Z]{2}"', r['body'])) and 'isServiceRestricted' not in r['body']


def check_media(port):
    results = {}
    for name, probe in zip(MEDIA, (netflix, disney, youtube, prime)):
        try:
            results[name] = bool(probe(port))
        except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError):
            results[name] = False
    return dict(services=results, pass_count=sum(results.values()), all_passed=all(results.values()))


def quality_from(data, ip):
    unknown = dict(grade=1, risk_score=None, label='未知', source='ipquery.io')
    if not isinstance(data, dict) or data.get('ip') != ip:
        return unknown
    risk = data.get('risk', {})
    if not isinstance(risk, dict):
        return unknown
    fields = ('is_vpn', 'is_tor', 'is_proxy', 'is_datacenter')
    score = risk.get('risk_score')
    if any(risk.get(k) is True for k in ('is_vpn','is_tor','is_proxy')) or (type(score) in (int,float) and score>=50):
        return dict(grade=0,risk_score=score if type(score) in (int,float) else None,label='风险',source='ipquery.io',flags={k:risk.get(k) for k in fields})
    if not all(type(risk.get(k)) is bool for k in fields) or type(score) not in (int, float) or not 0 <= score <= 100:
        return unknown
    risky = any(risk[k] for k in ('is_vpn', 'is_tor', 'is_proxy')) or score >= 50
    grade = 0 if risky else 2 if risk['is_datacenter'] else 3
    return dict(grade=grade, risk_score=score, label={0:'风险', 2:'机房', 3:'低风险非机房'}[grade],
                flags={k:risk[k] for k in fields}, source='ipquery.io')


@lru_cache(maxsize=512)
def quality(ip):
    try:
        if not ipaddress.ip_address(ip).is_global:
            raise ValueError('invalid exit')
        opener = build_opener(ProxyHandler({}))
        with opener.open(Request('https://api.ipquery.io/' + ip + '?format=json', headers={'User-Agent':'xixiduo-loon/1.0'}), timeout=8) as response:
            data = json.loads(response.read(65536))
        return quality_from(data, ip)
    except (ValueError, OSError, TypeError):
        return dict(grade=1, risk_score=None, label='未知', source='ipquery.io')


def quality_key(q):
    return -q['grade'], q['risk_score'] if q['risk_score'] is not None else 101


def download(port):
    # 两次 2 MiB 小样本，严格校验状态码和实际字节数；不是峰值带宽测量。
    size = 2 * 1024 * 1024
    env = {k:v for k,v in os.environ.items() if k.lower() not in ('http_proxy','https_proxy','all_proxy','no_proxy')}
    rates = []
    for _ in range(2):
        command = ['curl','-q','--silent','--fail','--max-time','15','--connect-timeout','7',
                   '--max-filesize',str(size),'--noproxy','','--proxy',f'http://127.0.0.1:{port}',
                   '--output',os.devnull,'--write-out','%{http_code} %{size_download} %{time_total}',
                   f'https://speed.cloudflare.com/__down?bytes={size}']
        try:
            r = subprocess.run(command,capture_output=True,text=True,timeout=18,env=env)
            code, count, seconds = r.stdout.split()
            if r.returncode or code != '200' or int(count) != size or float(seconds) <= 0:
                return None
            rates.append(size * 8 / float(seconds) / 1_000_000)
        except (ValueError,OSError,subprocess.SubprocessError):
            return None
    return round(statistics.median(rates), 2)


def ai_key(node):
    return (-node['ai']['pass_count'], *quality_key(node['quality']), node['ai']['latency_ms'], node['id'])


def pick_two(nodes, key):
    selected, seen = [], set()
    for node in sorted(nodes, key=key):
        if node['exit_ip'] not in seen:
            selected.append(node)
            seen.add(node['exit_ip'])
        if len(selected) == 2:
            break
    return selected


def select(nodes):
    ai = pick_two(nodes, ai_key)
    media = pick_two([n for n in nodes if n['media']['all_passed'] and n.get('download_mbps')],
                     lambda n: (-n['download_mbps'], *quality_key(n['quality']), n['ai']['latency_ms'], n['id']))
    return ai, media


def qualified(node):
    """保留未知质量；已标记风险、AI 不足两项及下载失败的候选不用于发布。"""
    return (node['quality']['grade'] >= 1 and node['ai']['pass_count'] >= 2
            and bool(node.get('download_mbps')) and node['download_mbps'] > 0)


def country_best(nodes, limit=4):
    """每国最多四个不同出口，按质量和延迟精选；不使用不合格候选凑数。"""
    result = {}
    seen = {}
    key = lambda n: (*quality_key(n['quality']), n['ai']['latency_ms'], -(n.get('download_mbps') or 0), n['id'])
    for node in sorted(nodes, key=key):
        if not qualified(node):
            continue
        code = node['country']
        group, exits = result.setdefault(code, []), seen.setdefault(code, set())
        if len(group) < limit and node['exit_ip'] not in exits:
            group.append(node)
            exits.add(node['exit_ip'])
    return [node for code in sorted(result) for node in result[code]]


def clean_ip_best(nodes):
    clean = []
    fields = ('is_vpn', 'is_tor', 'is_proxy', 'is_datacenter')
    for node in nodes:
        q = node['quality']
        flags = q.get('flags', {})
        if (qualified(node) and q['grade'] == 3 and type(q.get('risk_score')) in (int, float)
                and q['risk_score'] == 0 and all(flags.get(k) is False for k in fields)):
            clean.append(node)
    return sorted(clean, key=ai_key)[:1]


def download_best(nodes):
    measured = [n for n in nodes if n.get('download_mbps') and n['download_mbps'] > 0]
    if not measured:
        return []
    return pick_two(measured, key=lambda n: (-n['download_mbps'], *quality_key(n['quality']), n['ai']['latency_ms'], n['id']))


def measured_name(name, node):
    suffix = f'{node.get("basic_latency_ms",node["ai"]["latency_ms"])}ms'
    if node.get('download_mbps') is not None:
        suffix += f' · {node["download_mbps"]:.2f}Mbps'
    return name + '｜' + suffix
