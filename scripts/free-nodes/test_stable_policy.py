import copy
from datetime import datetime,timedelta,timezone
import unittest
from unittest.mock import patch
import pool
import stable_policy as policy
import steady_probe
from enrich import quality_from

AT=datetime(2026,11,9,tzinfo=timezone.utc)


def result(i=0,country='US',speed=20,latency=100,exit_ip=None):
    r=pool.blank({'id':str(i),'body':'test'})
    r.update(country=country,exit_ip=exit_ip or f'8.8.{i//250}.{i%250+1}',basic_latency_ms=latency,
             download_mbps=speed,measurement_profile=policy.PROFILE,measurement_environment='test')
    r['ai'].update(passed=True,pass_count=3,latency_ms=200)
    return r


class StableTests(unittest.TestCase):
    def history(self,speeds=(20,20,20),hours=(0,6,12)):
        state={'nodes':{'0':{'id':'0'}}}
        for i,(speed,hour) in enumerate(zip(speeds,hours)):
            r=result(speed=speed);at=(AT+timedelta(hours=hour)).isoformat();r['tested_at']=at
            policy.observe(state,[r],at,str(i),'test')
        return state,r,at

    def test_three_rounds_twelve_hours(self):
        state,r,at=self.history()
        self.assertTrue(r['stable']);self.assertEqual(r['observation_span_hours'],12)
        self.assertEqual(policy.choose(state,[r],at)[1],'stable')
        self.assertEqual(len(policy.choose(state,[r],at)[0]),1)

    def test_fast_rounds_do_not_fake_stability(self):
        _,r,_=self.history(hours=(0,1,2));self.assertFalse(r['stable'])

    def test_frequent_source_updates_do_not_prevent_stability(self):
        _,r,_=self.history(speeds=(20,)*14,hours=tuple(range(14)))
        self.assertTrue(r['stable']);self.assertEqual(r['observation_span_hours'],13)

    def test_spike_does_not_hide_slow_history(self):
        state,r,at=self.history((1,1,100));self.assertFalse(r['stable'])
        self.assertEqual(policy.choose(state,[r],at)[0],[])

    def test_egress_or_profile_change_resets_performance(self):
        for change in ({'exit_ip':'1.1.1.1'},{'measurement_profile':'old-profile'},{'measurement_environment':'elsewhere'}):
            state,r,at=self.history()
            r.update(change)
            policy.observe(state,[r],(AT+timedelta(hours=18)).isoformat(),'four','test')
            if 'exit_ip' in change:self.assertFalse(r['stable'])
            # Unknown profiles cannot supply the current qualification sample.
            if 'measurement_profile' in change:self.assertEqual(r['observation_rounds'],3)

    def test_recent_failure_reduces_seven_day_success_rate(self):
        state,r,at=self.history();r['status']='dead';r['basic_latency_ms']=None
        policy.observe(state,[r],(AT+timedelta(hours=18)).isoformat(),'failure','test')
        self.assertEqual(r['success_rate'],.75);self.assertFalse(r['stable'])

    def test_30_unique_exits_and_country_reservation(self):
        rows=[result(i,speed=100-i) for i in range(40)]
        rows += [result(41,'JP',10),result(42,'SG',10),result(43,'DE',10),result(44,exit_ip=rows[0]['exit_ip'])]
        state={'stable_policy_started_at':AT.isoformat()}
        chosen,phase=policy.choose(state,rows,AT.isoformat())
        self.assertEqual(len(chosen),30);self.assertEqual(len({r['exit_ip'] for r in chosen}),30)
        self.assertTrue(set(policy.PREFERRED)<={r['country'] for r in chosen})
        self.assertEqual(phase,'observation')

    def test_hard_cutoffs_unknown_quality_allowed(self):
        self.assertTrue(policy.current_eligible(result(speed=10,latency=1000)))
        self.assertFalse(policy.current_eligible(result(speed=9.99)))
        self.assertFalse(policy.current_eligible(result(latency=1001)))
        r=result();r['quality']['grade']=0;self.assertFalse(policy.current_eligible(r))

    def test_known_risk_not_hidden_by_missing_fields(self):
        for risk in ({'is_tor':True},{'risk_score':99},{'is_proxy':True,'is_datacenter':None}):
            self.assertEqual(quality_from({'ip':'8.8.8.8','risk':risk},'8.8.8.8')['grade'],0)

    def test_country_numbers_survive_reordering(self):
        state={};a,b=result(0),result(1);policy.assign_numbers(state,[a,b]);policy.assign_numbers(state,[b,a])
        self.assertEqual((a['serial'],b['serial']),(1,2))

    def test_unknown_latency_does_not_reset_high_streak(self):
        state={'nodes':{'0':{'id':'0','status':'active','high_latency_streak':1}}}
        r=result();r['basic_latency_ms']=None;pool.reconcile(state,[r],AT.isoformat())
        self.assertEqual(state['nodes']['0']['high_latency_streak'],1)

    def test_hysteresis_and_distinct_backups(self):
        state={};a,b,c=result(0),result(1),result(2)
        for r,score in zip((a,b,c),(20,19,18)):r['selection_score']=score
        picks=policy.recommendations(state,[a,b,c],'1');self.assertEqual(picks['download'][0]['id'],'0')
        c['selection_score']=30
        picks=policy.recommendations(state,[a,b,c],'2');self.assertEqual(picks['download'][0]['id'],'0')
        picks=policy.recommendations(state,[a,b,c],'3');self.assertEqual(picks['download'][0]['id'],'2')
        self.assertNotEqual(*[r['exit_ip'] for r in picks['download']])

    def test_state_read_failure_cannot_reset_history(self):
        with patch('pool.subprocess.run') as run:
            run.return_value.returncode=1
            with self.assertRaises(RuntimeError):pool.state_load()

    def test_two_providers_required_and_unknown_not_zero(self):
        def fake(name,port):
            if name=='google':return {'ms':100}
            raise ValueError('unavailable')
        with patch('steady_probe.request',side_effect=fake):
            r=steady_probe.basic(20000,list(steady_probe.TARGETS))
        self.assertEqual(r['status'],'alive');self.assertIsNone(r['basic_latency_ms'])

    def test_download_three_samples_after_warmup(self):
        with patch('steady_probe.transfer',side_effect=[1000,10,20,30]) as transfer:
            r=steady_probe.detailed(20000)
        self.assertEqual(r['download_mbps'],20)
        self.assertEqual(r['download_samples_mbps'],[10,20,30])
        self.assertEqual(transfer.call_args_list[0].args,(20000,256*1024))


if __name__=='__main__':unittest.main()
