"""跨轮稳定精选策略。旧规格数据不用于新测速评分。"""
from datetime import datetime,timedelta
import statistics
from enrich import quality_key,qualified,clean_ip_best

PROFILE='steady-v1-3x8MiB-body-time'
PREFERRED=('US','JP','SG','DE')


def quantile(values,q):
    if not values:return None
    values=sorted(values);at=(len(values)-1)*q;lo=int(at);hi=min(lo+1,len(values)-1)
    return values[lo]+(values[hi]-values[lo])*(at-lo)


def age(a,b):return (datetime.fromisoformat(a)-datetime.fromisoformat(b)).total_seconds()


def observe(state,results,at,cycle,environment):
    state.setdefault('stable_policy_started_at',at)
    for r in results:
        n=state['nodes'][r['id']]
        if r.get('exit_ip') and n.get('performance_exit')!=r['exit_ip']:
            n['performance_exit']=r['exit_ip'];n['exit_epoch']=r.get('tested_at',at)
        epoch=n.get('exit_epoch',at)
        history=[h for h in n.get('observations',[]) if age(at,h['at'])<=7*86400]
        if not any(h['cycle']==cycle for h in history):
            # 未知样本不记成功或失败，不冒充一次有效观察。
            if r['status']=='dead' or r.get('basic_latency_ms') is not None:
                history.append(dict(at=r.get('tested_at',at),cycle=cycle,ok=r['status']!='dead',basic=r.get('basic_latency_ms'),
                    exit=r.get('exit_ip') or n.get('performance_exit',''),profile=r.get('measurement_profile'),
                    env=r.get('measurement_environment'),speed=r.get('download_mbps')))
        n['observations']=history
        window=[h for h in history if h['at']>=epoch]
        rate=sum(h['ok'] for h in window)/len(window) if window else 0
        perf=[h for h in window if age(at,h['at'])<=86400 and h.get('profile')==PROFILE
              and h.get('env')==environment and h.get('exit')==n.get('performance_exit') and h.get('speed') is not None]
        last=perf[-3:];p25=quantile([h['speed'] for h in last],.25)
        # Observation duration is independent of source-update frequency; the
        # throughput floor still uses the most recent three valid rounds.
        span=age(perf[-1]['at'],perf[0]['at']) if len(perf)>=3 else 0
        stable=len(last)>=3 and span>=12*3600 and rate>=.95 and p25>=10
        basic=[h['basic'] for h in window if h.get('basic') is not None]
        jitter=(quantile(basic,.95)-quantile(basic,.5)) if basic else 999999
        r.update(observation_cycle=cycle,success_rate=rate,conservative_mbps=p25,stable=stable,observation_rounds=len(perf),
                 observation_span_hours=round(span/3600,2),latency_variation_ms=jitter,
                 selection_score=(p25 or r.get('download_mbps') or 0)*rate)


def current_eligible(r):
    return (qualified(r) and r.get('basic_latency_ms') is not None and r['basic_latency_ms']<=1000
            and r.get('download_mbps',0)>=10 and bool(r.get('exit_ip')) and r.get('measurement_profile')==PROFILE)


def rank(r):
    return (-r.get('selection_score',0),r.get('latency_variation_ms',float('inf')),
            r.get('basic_latency_ms',999999),*quality_key(r['quality']),r['id'])


def choose(state,results,at):
    provisional=age(at,state['stable_policy_started_at'])<12*3600
    eligible=[r for r in results if current_eligible(r) and (provisional or r.get('stable'))]
    ordered=sorted(eligible,key=rank);selected=[];exits=set()
    def add(r):
        if r['exit_ip'] not in exits and len(selected)<30:selected.append(r);exits.add(r['exit_ip'])
    for country in PREFERRED:
        for r in ordered:
            if r['country']==country:add(r);break
    for r in ordered:add(r)
    return selected,'observation' if provisional else 'stable'


def recommendations(state,nodes,cycle):
    def distinct(items):
        result=[];exits=set()
        for n in items:
            if n['exit_ip'] not in exits:result.append(n);exits.add(n['exit_ip'])
            if len(result)==2:break
        return result
    groups={
        'ai':sorted(nodes,key=lambda n:(-n['ai']['pass_count'],*rank(n))),
        'media':sorted([n for n in nodes if n['media']['all_passed']],key=rank),
        'download':sorted(nodes,key=rank),
        'clean_ip':clean_ip_best(nodes)}
    incumbents=state.setdefault('recommended_ids',{});trials=state.setdefault('recommendation_trials',{})
    output={}
    for category,ordered in groups.items():
        old=incumbents.get(category,[]);eligible={n['id']:n for n in ordered};picks=[]
        for position in range(1 if category=='clean_ip' else 2):
            used={n['exit_ip'] for n in picks}
            remaining=[n for n in ordered if n['exit_ip'] not in used]
            if not remaining:break
            challenger=remaining[0];chosen=challenger;key=category+str(position)
            previous=eligible.get(old[position]) if position<len(old) else None
            if previous and previous['exit_ip'] not in used:
                if previous['id']==challenger['id']:
                    trials.pop(key,None)
                elif category!='ai' or previous['ai']['pass_count']>=challenger['ai']['pass_count']:
                    trial=trials.get(key,{})
                    improved=challenger.get('selection_score',0)>=previous.get('selection_score',0)*1.2
                    count=trial.get('count',0)+1 if improved and trial.get('id')==challenger['id'] else 1 if improved else 0
                    sample_cycle=challenger.get('observation_cycle',cycle)
                    if trial.get('cycle')==sample_cycle:count=trial.get('count',count)
                    trials[key]={'id':challenger['id'],'count':count,'cycle':sample_cycle}
                    if count<2:chosen=previous
            picks.append(chosen)
        output[category]=picks;incumbents[category]=[n['id'] for n in picks]
    return output


def assign_numbers(state,nodes):
    labels=state.setdefault('country_numbers',{})
    for n in nodes:
        country=labels.setdefault(n['country'],{})
        if n['id'] not in country:country[n['id']]=max(country.values(),default=0)+1
        n['serial']=country[n['id']]
