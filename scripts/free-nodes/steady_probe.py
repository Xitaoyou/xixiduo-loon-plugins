"""Independent HTTPS controls and reproducible, proxy-only throughput samples."""
import json
import os
import statistics
import subprocess
import time
import health

TARGETS = {
    'cloudflare': 'https://www.cloudflare.com/cdn-cgi/trace',
    'google': 'https://www.gstatic.com/generate_204',
    'apple': 'https://www.apple.com/library/test/success.html',
}
SIZE = 8 * 1024 * 1024


def request(provider, port=None):
    env = {k:v for k,v in os.environ.items() if k.lower() not in ('http_proxy','https_proxy','all_proxy','no_proxy')}
    cmd = ['curl','-q','--silent','--max-time','8','--connect-timeout','5',
           '--max-filesize','8192','--noproxy','','--proxy',f'http://127.0.0.1:{port}' if port else '',
           '--write-out','\n%{http_code} %{time_total}',TARGETS[provider]]
    p = subprocess.run(cmd,capture_output=True,text=True,timeout=11,env=env)
    body,stats = p.stdout.rsplit('\n',1);code,seconds = stats.split()
    valid = ((provider=='cloudflare' and code=='200' and health.parse_trace(body)) or
             (provider=='google' and code=='204' and not body.strip()) or
             (provider=='apple' and code=='200' and '<TITLE>Success</TITLE>' in body))
    if p.returncode or not valid:raise ValueError('invalid HTTPS probe')
    result={'ms':round(float(seconds)*1000)}
    if provider=='cloudflare':
        fields=dict(line.split('=',1) for line in body.splitlines() if '=' in line)
        result.update(ip=fields['ip'],country=fields['loc'])
    return result


def controls():
    healthy=[]
    for name in TARGETS:
        try:request(name);healthy.append(name)
        except (ValueError,OSError,subprocess.SubprocessError):pass
    if len(healthy)<2:raise RuntimeError('Independent HTTPS controls unavailable')
    return healthy


def basic(port, healthy):
    medians=[];providers={};trace={};successes=0
    for name in healthy:
        samples=[]
        for _ in range(3):
            try:
                r=request(name,port);samples.append(r['ms']);successes+=1
                if r.get('ip'):trace=r
            except (ValueError,OSError,subprocess.SubprocessError):pass
        providers[name]={'successes':len(samples),'median_ms':statistics.median(samples) if len(samples)>=2 else None}
        if len(samples)>=2:medians.append(statistics.median(samples))
    # At least two independent providers must each have two successful samples.
    return dict(status='dead' if not successes else 'alive',
                basic_latency_ms=round(statistics.median(medians)) if len(medians)>=2 else None,
                basic_providers=providers,exit_ip=trace.get('ip',''),country=trace.get('country','ZZ'))


def transfer(port,size=SIZE):
    env={k:v for k,v in os.environ.items() if k.lower() not in ('http_proxy','https_proxy','all_proxy','no_proxy')}
    cmd=['curl','-q','--silent','--fail','--max-time','30','--connect-timeout','7',
         '--max-filesize',str(size),'--noproxy','','--proxy',f'http://127.0.0.1:{port}' if port else '',
         '--output',os.devnull,'--write-out','%{http_code} %{size_download} %{time_total} %{time_starttransfer}',
         f'https://speed.cloudflare.com/__down?bytes={size}&nonce={time.time_ns()}']
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=33,env=env)
    code,count,total,first=p.stdout.split();duration=float(total)-float(first)
    if p.returncode or code!='200' or int(count)!=size or duration<=0:raise ValueError('incomplete throughput sample')
    return round(size*8/duration/1_000_000,2)


def detailed(port):
    try:
        transfer(port,256*1024)  # warm-up; never used as a speed observation
        rates=[transfer(port) for _ in range(3)]
        return {'download_mbps':round(statistics.median(rates),2),'download_samples_mbps':rates}
    except (ValueError,OSError,subprocess.SubprocessError):
        return {'download_mbps':None,'download_samples_mbps':[]}


def environment():
    trace=request('cloudflare');sample=detailed(None)
    if sample['download_mbps'] is None or sample['download_mbps']<30:
        raise RuntimeError('Runner direct throughput below 30 Mbps; measurements discarded')
    return {'country':trace['country'],'direct_mbps':sample['download_mbps'],
            'profile':'github-ubuntu-x64/'+trace['country']}
