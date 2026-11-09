# SPDX-License-Identifier: GPL-3.0-or-later
# 西西多；检测判据改编自仓库 service-check（FlClash service_rules.go）。
# 许可证全文：../service-check/COPYING。仅探测端点和地区，不执行登录或对话。
import json
import os
import re
import statistics
import subprocess

POLICY = 'ai-two-of-three-v1'
SERVICES = ('ChatGPT', 'Claude', 'Gemini')
CLAUDE_BLOCKED = {'AF', 'BY', 'CN', 'CU', 'HK', 'IR', 'KP', 'MO', 'RU', 'SY'}
GEMINI_BLOCKED = {'CHN', 'RUS', 'BLR', 'CUB', 'IRN', 'PRK', 'SYR', 'HKG', 'MAC'}


def fetch(port, url):
    env = {k: v for k, v in os.environ.items() if k.lower() not in
           ('http_proxy', 'https_proxy', 'all_proxy', 'no_proxy')}
    marker = '\n__LOON_RESPONSE__'
    command = ['curl', '-q', '--silent', '--location', '--max-redirs', '3',
               '--proto', '=https', '--proto-redir', '=https', '--compressed',
               '--max-time', '10', '--connect-timeout', '7', '--max-filesize', '2097152',
               '--noproxy', '', '--proxy', f'http://127.0.0.1:{port}',
               '--user-agent', 'Mozilla/5.0',
               '--write-out', marker + '%{http_code} %{time_total}', url]
    proc = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace',
                          timeout=13, env=env)
    if proc.returncode:
        raise ValueError('AI probe failed')
    body, timing = proc.stdout.rsplit(marker, 1)
    code, seconds = timing.split()
    return dict(code=int(code), body=body, ms=max(1, round(float(seconds) * 1000)))


def blocked(body):
    body = body.lower()
    return any(term in body for term in ('sorry, you have been blocked', 'cf-chl-',
               'you may be connected to a disallowed isp', 'unsupported_country',
               'just a moment...', 'verify you are human'))


def chatgpt(port, request=fetch):
    ios = request(port, 'https://ios.chat.openai.com/')
    body = ios['body'].lower()
    # 预期的未授权客户端提示是此端点的可达信号，不把任意 403 算通过。
    if ios['code'] not in (200, 400, 401, 403) or blocked(body) or 'request is not allowed. please try again later.' not in body:
        return None
    web = request(port, 'https://api.openai.com/compliance/cookie_requirements')
    if blocked(web['body']) or not 200 <= web['code'] < 300:
        return None
    if not isinstance(json.loads(web['body']), dict):
        return None
    return round(statistics.median([ios['ms'], web['ms']]))


def claude(port, request=fetch):
    r = request(port, 'https://claude.ai/cdn-cgi/trace')
    if r['code'] != 200 or blocked(r['body']):
        return None
    from health import parse_trace
    country = parse_trace(r['body'])
    return r['ms'] if country not in CLAUDE_BLOCKED else None


def gemini(port, request=fetch):
    r = request(port, 'https://gemini.google.com')
    if not 200 <= r['code'] < 300 or blocked(r['body']):
        return None
    match = re.search(r',2,1,200,"([A-Z]{3})', r['body'])
    return r['ms'] if match and match[1] not in GEMINI_BLOCKED else None


def check_ai(port):
    results, delays = {}, []
    for name, probe in zip(SERVICES, (chatgpt, claude, gemini)):
        try:
            delay = probe(port)
        except (ValueError, OSError, subprocess.SubprocessError):
            delay = None
        results[name] = dict(passed=delay is not None, latency_ms=delay)
        if delay is not None:
            delays.append(delay)
    return dict(passed=len(delays) >= 2, pass_count=len(delays), services=results,
                latency_ms=round(statistics.median(delays)) if delays else None)
