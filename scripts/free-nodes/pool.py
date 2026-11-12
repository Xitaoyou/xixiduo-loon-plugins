"""版本锁定来源、持久候选队列、分片检测与双分支原子发布。"""
import argparse
import base64
from collections import Counter, defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile
import threading
import time
from urllib.request import urlopen

import health
from update import convert, decrypt, marked, ROOT
from enrich import quality, check_media, download, quality_key
from ai_check import check_ai
import steady_probe
import stable_policy

WORK=ROOT/'.pool-work'
CAPACITY=2000
FILES=['ecfg6','ecfg6_en','ecfg6_zh','ecfg6_ru','ecfg6_ja','ecfg6_de']


def now():return datetime.now(timezone.utc).isoformat()
def read(path,default=None):return json.loads(Path(path).read_text(encoding='utf-8')) if Path(path).exists() else default
def write(path,data):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def git(*args,input=None):return subprocess.check_output(['git',*args],input=input,text=True,encoding='utf-8').strip()
def api(path):return json.loads(subprocess.check_output(['gh','api',path],text=True,encoding='utf-8'))


def identity(body):
    head,opt=health.parse_body(body);head[1]=head[1].lower();head[2]=str(int(head[2]))
    # 名称、参数顺序不参与；连接凭据和全部已解析参数参与。
    return hashlib.sha256(json.dumps([head,opt],sort_keys=True,ensure_ascii=True).encode()).hexdigest()


def state_load():
    result=subprocess.run(['git','show','refs/remotes/origin/pool-state:pool.json'],capture_output=True,text=True,encoding='utf-8')
    if result.returncode:
        raise RuntimeError('Persistent state unavailable; refusing to reset existing history')
    state=json.loads(result.stdout)
    if not isinstance(state.get('nodes'),dict):raise RuntimeError('Invalid persistent state')
    return state


def fetch_source(version):
    tree=api('repos/pixelor/ecfg/git/trees/'+version+'?recursive=1')
    entries={x['path']:x for x in tree['tree']}
    documents=[]
    for name in FILES:
        expected=entries['data/'+name]['sha'];payload=None
        urls=[f'https://raw.githubusercontent.com/pixelor/ecfg/{version}/data/{name}',
              f'https://cdn.jsdelivr.net/gh/pixelor/ecfg@{version}/data/{name}',
              f'https://cdn.shadowrockets.app/ecfg/data/{name}',f'https://files.shadowrockets.app/ecfg/data/{name}']
        for url in urls:
            try:
                with urlopen(url,timeout=20) as r:b=r.read(8*1024*1024+1)
                if len(b)>8*1024*1024:continue
                if hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()!=expected:continue
                payload=decrypt(b);break
            except Exception:continue
        if payload is None:raise RuntimeError('No verified mirror for '+name)
        documents.append((name,payload))
    return version,documents


def merge(state,documents,version,at):
    counts=Counter();seen=set();restricted_ids=set();restricted_credentials=set()
    for source,text in documents:
        for line in text.splitlines():
            line=line.strip()
            if not line or line.startswith('#'):continue
            restricted=False
            try:_,_,body=convert(line)
            except (ValueError,KeyError,TypeError,OverflowError) as e:
                if str(e)=='restricted':
                    restricted=True
                    try:
                        if line.startswith('vmess://'):
                            d=json.loads(base64.b64decode(line[8:]+'==='));d['ps']='';d['name']=''
                            line='vmess://'+base64.b64encode(json.dumps(d).encode()).decode()
                        else:line=line.split('#',1)[0]
                        _,_,body=convert(line)
                    except Exception:counts['restricted_unparsed']+=1;continue
                else:
                    reason=str(e) if str(e) in {'insecure tls','unsupported transport','unsupported options','unsupported cipher','outside free protocol subset','ALPN not portable for VLESS','unsupported fingerprint'} else 'invalid_or_nonportable'
                    counts['reject_'+reason]+=1;continue
            ident=identity(body)
            if ident in seen:counts['duplicates']+=1
            seen.add(ident)
            node=state['nodes'].get(ident)
            if node is None:
                node={'id':ident,'body':body,'first_seen':at,'queued_at':at,'status':'pending','high_latency_streak':0}
                state['nodes'][ident]=node;counts['new']+=1
            node.update(last_seen=at,source_version=version)
            node['sources']=sorted(set(node.get('sources',[]))|{source})
            if restricted:
                node['status']='restricted';restricted_ids.add(ident);counts['restricted']+=1
                restricted_credentials.add(json.dumps(health.parse_body(body)[0],ensure_ascii=True))
            elif node['status']=='cooldown' and node['cooldown_until']<=at:
                node.update(status='pending',queued_at=at,failure_rounds=0,high_latency_streak=0)
            elif node['status']=='restricted':node.update(status='pending',queued_at=at)
            if not restricted:node['body']=body
    for ident in restricted_ids:state['nodes'][ident]['status']='restricted'
    for node in state['nodes'].values():
        if node.get('body') and json.dumps(health.parse_body(node['body'])[0],ensure_ascii=True) in restricted_credentials:node['status']='restricted'
        if node['status']=='restricted':
            for key in list(node):
                if key not in ('id','status','first_seen','last_seen','source_version','sources'):node.pop(key,None)
    return dict(counts)


def prepare(force=False,retry_only=False):
    WORK.mkdir(exist_ok=True)
    state=state_load();at=now();source_error=None
    due=not state.get('last_cycle') or datetime.fromisoformat(at)-datetime.fromisoformat(state['last_cycle'])>=timedelta(hours=6)
    try:version=state['source_version'] if retry_only else api('repos/pixelor/ecfg/commits/main')['sha']
    except Exception as error:
        if not state['nodes']:raise
        version=state['source_version'];source_error=type(error).__name__
    retry_due=any(n['status'] in ('isolated','slow') and n.get('retry_at',at)<=at for n in state['nodes'].values())
    # Once a full refresh is due, quarter-hour jobs defer to the hourly full
    # cycle rather than republishing a partial, increasingly stale selection.
    run=(retry_due and not due if retry_only else force or due or state.get('source_version')!=version or retry_due)
    output=os.environ.get('GITHUB_OUTPUT')
    if not run:
        if output:
            with open(output,'a') as f:f.write('run=false\nmatrix={"index":[0]}\n')
        print('Targeted retry deferred or not due' if retry_only else 'Upstream unavailable; historical retest not due' if source_error else 'Verified source unchanged; next historical retest not due');return
    # 迁移已有精选配置；保留原凭据，不把别名当作不同节点。
    if not state['nodes']:
        for line in (ROOT/'subscriptions/free-nodes.txt').read_text(encoding='utf-8').splitlines():
            if ' = ' not in line:continue
            body=line.split(' = ',1)[1];ident=identity(body)
            state['nodes'][ident]={'id':ident,'body':body,'first_seen':at,'last_seen':at,'status':'active','high_latency_streak':0,'source_version':'migration'}
    try:
        if source_error:raise RuntimeError('Source head unavailable')
        documents=[] if retry_only else fetch_source(version)[1]
    except Exception as error:
        if not state.get('source_version'):raise
        source_error=source_error or type(error).__name__;version=state['source_version'];documents=[]
        if not (force or due):
            if output:
                with open(output,'a') as f:f.write('run=false\nmatrix={"index":[0]}\n')
            print('Upstream unavailable; previous state retained; historical retest not due');return
    summary=merge(state,documents,version,at)
    for n in state['nodes'].values():
        if n['status']=='cooldown' and n.get('cooldown_until','')<=at:
            n.update(status='pending',queued_at=at,failure_rounds=0,high_latency_streak=0)
    full=not retry_only and (force or due or state.get('source_version')!=version)
    active=[n for n in state['nodes'].values() if n['status']=='active']
    pending=sorted((n for n in state['nodes'].values() if n['status']=='pending'),key=lambda n:(n.get('queued_at',n.get('last_queue_test',n['first_seen'])),n['id']))
    retries=[n for n in state['nodes'].values() if n['status'] in ('isolated','slow') and n.get('retry_at',at)<=at]
    selected=active+pending[:max(0,CAPACITY-len(active))+200]+retries if full else retries
    cycle=hashlib.sha256((at+version).encode()).hexdigest()[:20]
    manifest={'cycle':cycle,'at':at,'full':full,'source_version':version,'source_error':source_error,'ids':[n['id'] for n in selected],'summary':summary,'shards':(len(selected)+49)//50}
    if not selected:raise RuntimeError('Empty candidate selection')
    write(WORK/'state.json',state);write(WORK/'manifest.json',manifest)
    for index in range(manifest['shards']):write(WORK/f'shard-{index}.json',{'cycle':cycle,'nodes':[{k:n[k] for k in ('id','body')} for n in selected[index*50:(index+1)*50]]})
    if output:
        with open(output,'a') as f:f.write('run=true\nmatrix='+json.dumps({'index':list(range(manifest['shards']))})+'\n')
    print(json.dumps({'cycle':cycle,'candidates':len(selected),'shards':manifest['shards'],'merge':summary}))


def blank(node):
    return dict(id=node['id'],body=node['body'],country='ZZ',exit_ip='',status='alive',basic_latency_ms=None,
                ai={'passed':False,'pass_count':0,'latency_ms':None,'services':{}},
                quality={'grade':1,'risk_score':None,'label':'未知','source':'not-tested'},
                media={'all_passed':False,'services':{k:False for k in ('Netflix','Disney+','YouTube Premium','Prime Video')}},download_mbps=None)


def controls():
    return steady_probe.controls()


from contextlib import contextmanager


@contextmanager
def running_core(nodes,binary):
    config={'log':{'disabled':True},'inbounds':[],'outbounds':[],'route':{'rules':[]}}
    ports={}
    for i,node in enumerate(nodes):
        try:out=health.outbound(node['body'],f'n{i}')
        except (ValueError,OSError,KeyError):continue
        ports[node['id']]=20000+i
        config['inbounds'].append({'type':'mixed','tag':f'in{i}','listen':'127.0.0.1','listen_port':20000+i})
        config['outbounds'].append(out);config['route']['rules'].append({'inbound':[f'in{i}'],'action':'route','outbound':f'n{i}'})
    if not ports:
        yield ports
        return
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/'config.json';write(path,config);path.chmod(0o600)
        if subprocess.run([binary,'check','-c',str(path)],capture_output=True,timeout=20).returncode:raise RuntimeError('Core rejected configuration')
        process=subprocess.Popen([binary,'run','-c',str(path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            time.sleep(1)
            if process.poll() is not None:raise RuntimeError('Core startup failed')
            yield ports
            if process.poll() is not None:raise RuntimeError('Core stopped during measurement')
        finally:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()


def shard(index,binary):
    doc=read(WORK/f'shard-{index}.json');nodes=doc['nodes'];healthy=controls()
    with running_core(nodes,binary) as ports:
        def probe(node):
            r=blank(node);r['tested_at']=now()
            if node['id'] not in ports:r['status']='dead';return r
            port=ports[node['id']];r.update(steady_probe.basic(port,healthy))
            if r['basic_latency_ms'] is not None and r['basic_latency_ms']<=1000:
                r['ai']=check_ai(port)
            return r
        with ThreadPoolExecutor(max_workers=4) as executor:results=list(executor.map(probe,nodes))
    if not set(healthy)<=set(controls()):raise RuntimeError('Control provider changed during shard; no penalties')
    write(WORK/f'result-{index}.json',{'cycle':doc['cycle'],'index':index,'results':results})
    print(json.dumps({'shard':index,'checked':len(results),'alive':sum(r['status']=='alive' for r in results)}))


def collect_results(manifest):
    results=[]
    for i in range(manifest['shards']):
        doc=read(WORK/f'result-{i}.json')
        if not doc or doc['cycle']!=manifest['cycle'] or doc['index']!=i:raise RuntimeError('Missing or mismatched shard')
        results+=doc['results']
    ids=[r['id'] for r in results]
    if len(ids)!=len(set(ids)) or set(ids)!=set(manifest['ids']):raise RuntimeError('Incomplete candidate results')
    if len(results)>=20 and sum(r['status']=='dead' for r in results)/len(results)>=.95:
        raise RuntimeError('Global failure circuit breaker; previous publication retained')
    return results


def measure(binary):
    manifest=read(WORK/'manifest.json');results=collect_results(manifest)
    controls();env=steady_probe.environment()
    targets=[r for r in results if r.get('basic_latency_ms') is not None and r['basic_latency_ms']<=1000 and r['ai']['pass_count']>=2]
    download_slots=threading.BoundedSemaphore(2)
    for start in range(0,len(targets),50):
        batch=targets[start:start+50]
        with running_core(batch,binary) as ports:
            def detailed(r):
                if r['id'] not in ports:return r
                port=ports[r['id']]
                # Resolve actual egress on the same runner as the throughput sample.
                try:trace=health.request_trace(port,details=True)
                except (ValueError,OSError,subprocess.SubprocessError):
                    r['measurement_error']='exit_lookup_failed';return r
                r.update(exit_ip=trace['ip'],country=trace['country'],tested_at=now())
                r['quality']=quality(r['exit_ip'])
                if r['quality']['grade']==0:return r
                # Recheck latency/AI here; shard-region results cannot authorize this egress.
                r.update(steady_probe.basic(port,list(steady_probe.TARGETS)))
                if not r.get('basic_latency_ms') or r['basic_latency_ms']>1000 or not r.get('exit_ip'):return r
                if r['exit_ip']!=trace['ip']:
                    r['measurement_error']='rotating_exit';return r
                r['ai']=check_ai(port)
                if r['ai']['pass_count']<2:return r
                with download_slots:r.update(steady_probe.detailed(port))
                # Slow nodes cannot be published; avoid large media page probes
                # for them without reducing throughput sampling or history.
                if r.get('download_mbps') is not None and r['download_mbps']>=10:
                    r['media']=check_media(port)
                try:after=health.request_trace(port,details=True)
                except (ValueError,OSError,subprocess.SubprocessError):after={}
                if after.get('ip')!=r['exit_ip']:
                    r['download_mbps']=None;r['measurement_error']='rotating_exit'
                r.update(measurement_profile=stable_policy.PROFILE,measurement_environment=env['profile'])
                return r
            with ThreadPoolExecutor(max_workers=4) as executor:list(executor.map(detailed,batch))
        print(json.dumps({'detailed_completed':min(start+50,len(targets)),'total':len(targets)}),flush=True)
    after=steady_probe.environment();controls()
    if env['profile']!=after['profile'] or max(env['direct_mbps'],after['direct_mbps'])/min(env['direct_mbps'],after['direct_mbps'])>4:
        raise RuntimeError('Runner environment unstable; previous publication retained')
    write(WORK/'measured.json',{'cycle':manifest['cycle'],'environment':env,'environment_after':after,'results':results})


def reconcile(state,results,at):
    good=[]
    def later(seconds):return (datetime.fromisoformat(at)+timedelta(seconds=seconds)).isoformat()
    for r in results:
        n=state['nodes'][r['id']];n['last_result']=r;n['last_checked']=at;n['last_queue_test']=at
        latency=r['basic_latency_ms']
        if latency is not None:
            n['high_latency_streak']=n.get('high_latency_streak',0)+1 if latency>1000 else 0
        if r['status']=='dead':
            failures=n.get('failure_rounds',0)+1;n['failure_rounds']=failures
            if failures>=3:n.update(status='cooldown',cooldown_until=later(7*86400))
            else:n.update(status='isolated',retry_at=later(1800 if failures==1 else 7200))
            continue
        # Unknown latency is not a recovery observation.
        if latency is None and n.get('status') in ('isolated','slow'):
            n['retry_at']=later(7200 if n['status']=='isolated' else 86400);continue
        n['failure_rounds']=0
        if n.get('high_latency_streak',0)>=2:
            n.update(status='slow',retry_at=later(86400));continue
        good.append(n)
    groups=defaultdict(list)
    def rank(n):
        r=n['last_result'];return (-r['ai']['pass_count'],*quality_key(r['quality']),r['basic_latency_ms'] if r['basic_latency_ms'] is not None else 999999,n['id'])
    # Retry-only rounds must not forget existing, untested active nodes.
    tested={r['id'] for r in results}
    good += [n for n in state['nodes'].values() if n['status']=='active' and n['id'] not in tested]
    for n in good:groups[n['last_result']['country']].append(n)
    queues=[deque(sorted(groups[k],key=rank)) for k in sorted(groups)]
    winners=[]
    while queues and len(winners)<CAPACITY:
        for queue in list(queues):
            if len(winners)==CAPACITY:break
            winners.append(queue.popleft())
            if not queue:queues.remove(queue)
    chosen={n['id'] for n in winners}
    for n in good:
        n['status']='active' if n['id'] in chosen else 'pending'
        if n['status']=='pending':n['queued_at']=at
    return [n['last_result'] for n in winners if n.get('last_result')]


def finalize():
    manifest=read(WORK/'manifest.json');state=read(WORK/'state.json')
    raw=collect_results(manifest)
    measured=read(WORK/'measured.json')
    if not measured or measured['cycle']!=manifest['cycle']:raise RuntimeError('Missing same-cycle detailed measurements')
    all_results=measured['results'];ids=[r['id'] for r in all_results]
    if len(ids)!=len(set(ids)) or set(ids)!=set(manifest['ids']):raise RuntimeError('Incomplete detailed measurements')
    at=now()
    stable_policy.observe(state,all_results,at,manifest['cycle'],measured['environment']['profile'])
    alive=reconcile(state,all_results,at)
    # Retry rounds retain untested active records from the last completed full
    # cycle. The next due full cycle refreshes them; a time boundary must not
    # empty the subscription during an otherwise successful targeted retry.
    fresh=alive
    selected,phase=stable_policy.choose(state,fresh,at)
    stable_policy.assign_numbers(state,selected)
    picks=stable_policy.recommendations(state,selected,manifest['cycle'])
    if selected:
        content,counts,metadata=health.render_results(selected,alive,len(ids),0,selected_only=True,picks=picks)
    else:
        content='# No eligible nodes in this completed cycle.\n';counts={}
        metadata={'connection_tested':True,'recommendation_rows':0,'recommendations':{},'node_results':[],
                  'country_count':0,'country_best_count':0,'selection_reason':'no_eligible_nodes','node_limit':30}
    stamp=datetime.fromisoformat(at).astimezone(timezone(timedelta(hours=8)))
    lines=content.splitlines()
    if ' = ' in lines[0]:lines.insert(metadata['recommendation_rows'],f'🕒 免费节点刷新 {stamp:%m-%d %H:%M}（北京时间） = '+lines[0].split(' = ',1)[1])
    content='\n'.join(lines)+'\n'
    from export_clients import render,write_exports,brand_overseas
    content=brand_overseas(content,metadata)
    render(content,allow_empty=True)
    folder=ROOT/'subscriptions'
    for name in ('free-nodes.txt','免费节点','免费节点海外版'):(folder/name).write_text(content,encoding='utf-8',newline='\n')
    write_exports(content,title='免费节点海外版')
    metadata.update(updated_at=at,nodes=sum(counts.values()),protocols=counts,published_rows=len(lines),cycle=manifest['cycle'],
        source_version=manifest['source_version'],source_error=manifest.get('source_error'),
        pool=dict(Counter(n['status'] for n in state['nodes'].values())),merge=manifest['summary'],checked=len(ids),
        unreachable=sum(r['status']=='dead' for r in all_results),
        reachable_checked=sum(r['status']=='alive' for r in all_results),active_candidates=len(alive),
        ai_qualified=sum(r['ai']['pass_count']>=2 for r in all_results),
        quality_qualified=sum(stable_policy.current_eligible(r) for r in all_results),
        quality_rejected=sum(r['ai']['pass_count']>=2 and r['quality']['grade']==0 for r in all_results),
        selection_phase=phase,measurement_profile=stable_policy.PROFILE,measurement_environment=measured['environment'],
        thresholds={'basic_ms_max':1000,'current_mbps_min':10,'stability_hard_gate':False},
        stability_weighting={'history_days':7,'throughput_history_hours':24,'bonus_max':.25,'full_bonus_rounds':3,'full_bonus_span_hours':12},
        workflow_run='https://github.com/'+os.environ.get('GITHUB_REPOSITORY','Xitaoyou/xixiduo-loon-plugins')+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID','local'))
    write(folder/'free-nodes.json',metadata)
    state.update(source_version=manifest['source_version'],last_cycle_id=manifest['cycle'])
    if manifest.get('full',True):state['last_cycle']=at
    write(WORK/'published-state.json',state)
    print(json.dumps({k:metadata[k] for k in ('cycle','checked','nodes','pool','selection_phase')}))


def publish():
    # 同一 git receive-pack 原子更新两个分支，任何一个引用冲突则两边均不更新。
    git('add','subscriptions')
    git('commit','-m','chore: publish verified persistent pool selection')
    blob=git('hash-object','-w','--stdin',input=(WORK/'published-state.json').read_text(encoding='utf-8'))
    tree=git('mktree',input=f'100644 blob {blob}\tpool.json\n')
    args=['commit-tree',tree,'-m','Persist completed pool cycle']
    try:parent=git('rev-parse','refs/remotes/origin/pool-state');args+=['-p',parent]
    except subprocess.CalledProcessError:pass
    commit=git(*args)
    git('push','--atomic','origin','HEAD:refs/heads/main',commit+':refs/heads/pool-state')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','shard','measure','finalize','publish']);p.add_argument('--index',type=int);p.add_argument('--force',action='store_true');p.add_argument('--retry-only',action='store_true');p.add_argument('--binary',default=os.environ.get('SING_BOX_BINARY'));a=p.parse_args()
    if a.command=='prepare':prepare(a.force,a.retry_only)
    elif a.command=='shard':shard(a.index,a.binary)
    elif a.command=='measure':measure(a.binary)
    elif a.command=='finalize':finalize()
    else:publish()
