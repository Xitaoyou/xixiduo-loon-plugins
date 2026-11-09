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
import time
from urllib.request import urlopen

import health
from update import convert, decrypt, marked, ROOT
from enrich import quality, check_media, download, quality_key
from ai_check import check_ai

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
    if result.returncode:return {'schema':1,'nodes':{},'source_version':None,'last_cycle':None}
    return json.loads(result.stdout)


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
                node.update(status='pending',queued_at=at)
            elif node['status']=='restricted':node.update(status='pending',queued_at=at)
    for ident in restricted_ids:state['nodes'][ident]['status']='restricted'
    for node in state['nodes'].values():
        if json.dumps(health.parse_body(node['body'])[0],ensure_ascii=True) in restricted_credentials:node['status']='restricted'
    return dict(counts)


def prepare(force=False):
    WORK.mkdir(exist_ok=True)
    state=state_load();at=now();source_error=None
    due=not state.get('last_cycle') or datetime.fromisoformat(at)-datetime.fromisoformat(state['last_cycle'])>=timedelta(hours=6)
    try:version=api('repos/pixelor/ecfg/commits/main')['sha']
    except Exception as error:
        if not state['nodes']:raise
        version=state['source_version'];source_error=type(error).__name__
    run=force or due or state.get('source_version')!=version
    output=os.environ.get('GITHUB_OUTPUT')
    if not run:
        if output:
            with open(output,'a') as f:f.write('run=false\nmatrix={"index":[0]}\n')
        print('Upstream unavailable; historical retest not due' if source_error else 'Verified source unchanged; next historical retest not due');return
    # 迁移已有精选配置；保留原凭据，不把别名当作不同节点。
    if not state['nodes']:
        for line in (ROOT/'subscriptions/free-nodes.txt').read_text(encoding='utf-8').splitlines():
            if ' = ' not in line:continue
            body=line.split(' = ',1)[1];ident=identity(body)
            state['nodes'][ident]={'id':ident,'body':body,'first_seen':at,'last_seen':at,'status':'active','high_latency_streak':0,'source_version':'migration'}
    try:
        if source_error:raise RuntimeError('Source head unavailable')
        _,documents=fetch_source(version)
    except Exception as error:
        if not state.get('source_version'):raise
        source_error=source_error or type(error).__name__;version=state['source_version'];documents=[]
        if not (force or due):
            if output:
                with open(output,'a') as f:f.write('run=false\nmatrix={"index":[0]}\n')
            print('Upstream unavailable; previous state retained; historical retest not due');return
    summary=merge(state,documents,version,at)
    active=[n for n in state['nodes'].values() if n['status']=='active']
    pending=sorted((n for n in state['nodes'].values() if n['status']=='pending'),key=lambda n:(n.get('queued_at',n.get('last_queue_test',n['first_seen'])),n['id']))
    selected=active+pending[:max(0,CAPACITY-len(active))+200]
    cycle=hashlib.sha256((at+version).encode()).hexdigest()[:20]
    manifest={'cycle':cycle,'at':at,'source_version':version,'source_error':source_error,'ids':[n['id'] for n in selected],'summary':summary,'shards':(len(selected)+49)//50}
    if not selected:raise RuntimeError('Empty candidate selection')
    write(WORK/'state.json',state);write(WORK/'manifest.json',manifest)
    for index in range(manifest['shards']):write(WORK/f'shard-{index}.json',{'cycle':cycle,'nodes':selected[index*50:(index+1)*50]})
    if output:
        with open(output,'a') as f:f.write('run=true\nmatrix='+json.dumps({'index':list(range(manifest['shards']))})+'\n')
    print(json.dumps({'cycle':cycle,'candidates':len(selected),'shards':manifest['shards'],'merge':summary}))


def blank(node):
    return dict(id=node['id'],body=node['body'],country='ZZ',exit_ip='',status='alive',basic_latency_ms=None,
                ai={'passed':False,'pass_count':0,'latency_ms':None,'services':{}},
                quality={'grade':1,'risk_score':None,'label':'未知','source':'not-tested'},
                media={'all_passed':False,'services':{k:False for k in ('Netflix','Disney+','YouTube Premium','Prime Video')}},download_mbps=None)


def controls():
    for target in health.TARGETS:health.request_trace(target=target)


def shard(index,binary):
    doc=read(WORK/f'shard-{index}.json');nodes=doc['nodes'];controls()
    config={'log':{'disabled':True},'inbounds':[],'outbounds':[],'route':{'rules':[]}}
    rejected={}
    for i,node in enumerate(nodes):
        try:out=health.outbound(node['body'],f'n{i}')
        except (ValueError,OSError,KeyError):rejected[node['id']]='endpoint_rejected';continue
        config['inbounds'].append({'type':'mixed','tag':f'in{i}','listen':'127.0.0.1','listen_port':20000+i})
        config['outbounds'].append(out);config['route']['rules'].append({'inbound':[f'in{i}'],'action':'route','outbound':f'n{i}'})
    results=[]
    if config['outbounds']:
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'config.json';write(path,config);path.chmod(0o600)
            if subprocess.run([binary,'check','-c',str(path)],capture_output=True,timeout=20).returncode:raise RuntimeError('Core rejected shard configuration')
            process=subprocess.Popen([binary,'run','-c',str(path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                time.sleep(1)
                if process.poll() is not None:raise RuntimeError('Core startup failed')
                def probe(pair):
                    i,node=pair;r=blank(node)
                    if node['id'] in rejected:r['status']='dead';return r
                    samples=[];traces=[]
                    for target in (health.TARGETS[0],health.TARGETS[1],health.TARGETS[0]):
                        start=time.monotonic()
                        try:
                            trace=health.request_trace(20000+i,target,details=True)
                            samples.append(round((time.monotonic()-start)*1000));traces.append(trace)
                        except (ValueError,OSError,subprocess.SubprocessError):pass
                    if not traces:r['status']='dead';return r
                    r.update(country=traces[-1]['country'],exit_ip=traces[-1]['ip'])
                    if len(samples)<2:return r
                    r['basic_latency_ms']=round(statistics.median(samples))
                    if r['basic_latency_ms']>1500:return r
                    r['ai']=check_ai(20000+i)
                    if r['ai']['passed']:
                        r['quality']=quality(r['exit_ip']);r['media']=check_media(20000+i);r['download_mbps']=download(20000+i)
                    return r
                with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(probe,enumerate(nodes)))
                if process.poll() is not None:raise RuntimeError('Core stopped during shard')
            finally:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait()
    else:
        for node in nodes:r=blank(node);r['status']='dead';results.append(r)
    controls() # 检测服务整体异常时整片失败，不提交淘汰结论。
    write(WORK/f'result-{index}.json',{'cycle':doc['cycle'],'index':index,'results':results})
    print(json.dumps({'shard':index,'checked':len(results),'alive':sum(r['status']=='alive' for r in results)}))


def reconcile(state,results,at):
    good=[];cooldown=(datetime.fromisoformat(at)+timedelta(days=7)).isoformat()
    for r in results:
        n=state['nodes'][r['id']];n['last_result']=r;n['last_checked']=at;n['last_queue_test']=at
        latency=r['basic_latency_ms']
        n['high_latency_streak']=n.get('high_latency_streak',0)+1 if latency is not None and latency>1500 else 0
        if r['status']=='dead' or n['high_latency_streak']>=2:
            n.update(status='cooldown',cooldown_until=cooldown);continue
        good.append(n)
    groups=defaultdict(list)
    def rank(n):
        r=n['last_result'];return (-r['ai']['pass_count'],*quality_key(r['quality']),r['basic_latency_ms'] if r['basic_latency_ms'] is not None else 999999,n['id'])
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
    return [n['last_result'] for n in winners]


def finalize():
    manifest=read(WORK/'manifest.json');state=read(WORK/'state.json');all_results=[]
    for i in range(manifest['shards']):
        doc=read(WORK/f'result-{i}.json')
        if not doc or doc['cycle']!=manifest['cycle'] or doc['index']!=i:raise RuntimeError('Missing or mismatched shard')
        all_results+=doc['results']
    ids=[r['id'] for r in all_results]
    if len(ids)!=len(set(ids)) or set(ids)!=set(manifest['ids']):raise RuntimeError('Incomplete candidate results')
    if len(all_results)>=20 and sum(r['status']=='dead' for r in all_results)/len(all_results)>=0.95:
        raise RuntimeError('Global failure circuit breaker; no state or subscription changes published')
    at=now();alive=reconcile(state,all_results,at)
    selected=[r for r in alive if r['basic_latency_ms'] is not None and r['basic_latency_ms']<=1500 and r['ai']['passed']]
    from enrich import qualified
    if any(qualified(r) for r in selected):
        content,counts,metadata=health.render_results(selected,alive,len(ids),0)
    else:
        content='# No eligible nodes in this completed cycle.\n';counts={}
        metadata={'connection_tested':True,'recommendation_rows':0,'recommendations':{},'node_results':[],
                  'country_count':0,'country_best_count':0,'selection_reason':'no_eligible_nodes'}
    stamp=datetime.fromisoformat(at).astimezone(timezone(timedelta(hours=8)))
    lines=content.splitlines()
    if ' = ' in lines[0]:lines.insert(metadata['recommendation_rows'],f'🕒 免费节点刷新 {stamp:%m-%d %H:%M}（北京） = '+lines[0].split(' = ',1)[1])
    content='\n'.join(lines)+'\n'
    # 先完整生成和验证三端格式，再接触发布文件。
    from export_clients import render,write_exports
    render(content,allow_empty=True)
    folder=ROOT/'subscriptions'
    for name in ('free-nodes.txt','免费节点'):(folder/name).write_text(content,encoding='utf-8',newline='\n')
    write_exports(content)
    metadata.update(updated_at=at,nodes=sum(counts.values()),protocols=counts,published_rows=len(lines),cycle=manifest['cycle'],source_version=manifest['source_version'],source_error=manifest.get('source_error'),pool=dict(Counter(n['status'] for n in state['nodes'].values())),merge=manifest['summary'],checked=len(ids),workflow_run='https://github.com/'+os.environ.get('GITHUB_REPOSITORY','Xitaoyou/xixiduo-loon-plugins')+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID','local'))
    write(folder/'free-nodes.json',metadata)
    state.update(source_version=manifest['source_version'],last_cycle=at,last_cycle_id=manifest['cycle'])
    write(WORK/'published-state.json',state)
    print(json.dumps({k:metadata[k] for k in ('cycle','checked','nodes','pool','merge')}))


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
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','shard','finalize','publish']);p.add_argument('--index',type=int);p.add_argument('--force',action='store_true');p.add_argument('--binary',default=os.environ.get('SING_BOX_BINARY'));a=p.parse_args()
    if a.command=='prepare':prepare(a.force)
    elif a.command=='shard':shard(a.index,a.binary)
    elif a.command=='finalize':finalize()
    else:publish()
