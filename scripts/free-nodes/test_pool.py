import copy
from datetime import datetime, timezone
import unittest
from unittest.mock import patch
import pool
import health
import protocols
from update import convert
from export_clients import convert as export

UUID='52396e06-041a-4cc2-be5c-8525eb457809'
AT='2026-11-09T10:00:00+00:00'


class ProtocolTests(unittest.TestCase):
    def test_hy2_alias_same_connection(self):
        a=convert('hy2://secret@node.example.com:443?sni=tls.example.com')[2]
        b=convert('hysteria2://secret@node.example.com:443?sni=tls.example.com')[2]
        self.assertEqual(pool.identity(a),pool.identity(b))

    def test_reality_three_formats(self):
        uri=f'vless://{UUID}@node.example.com:443?security=reality&type=tcp&flow=xtls-rprx-vision&sni=tls.example.com&pbk='+('A'*43)+'&sid=aabb&fp=chrome'
        body=convert(uri)[2];out=health.outbound(body,'test',resolve=lambda _: '8.8.8.8');clash,sr=export('test',body)
        self.assertEqual(out['flow'],clash['flow'])
        self.assertEqual(out['tls']['reality']['public_key'],clash['reality-opts']['public-key'])
        self.assertIn('security=reality',sr)

    def test_trojan_ws_alpn_and_special_password(self):
        body=convert('trojan://p%3Aa%40ss@node.example.com:443?type=ws&host=cdn.example.com&path=%2Fa%3Fx%3D1%2C2&alpn=h2%2Chttp%2F1.1')[2]
        out=health.outbound(body,'test',resolve=lambda _: '8.8.8.8');clash,_=export('name',body)
        self.assertEqual(out['password'],'p:a@ss')
        self.assertEqual(out['tls']['alpn'],clash['alpn'])
        self.assertEqual(out['transport']['path'],clash['ws-opts']['path'])

    def test_ss_obfs(self):
        import base64
        auth=base64.urlsafe_b64encode(b'aes-128-gcm:pass=word').decode()
        body=convert('ss://'+auth+'@node.example.com:443?plugin=obfs-local%3Bobfs%3Dtls%3Bobfs-host%3Dcdn.example.com')[2]
        out=health.outbound(body,'test',resolve=lambda _: '8.8.8.8');clash,sr=export('SS',body)
        self.assertEqual(out['password'],'pass=word');self.assertEqual(clash['password'],'pass=word')
        self.assertEqual(clash['plugin-opts']['mode'],'tls');self.assertIn('plugin=',sr)

    def test_invalid_parameters_not_silently_discarded(self):
        for suffix in ('?type=grpc','?encryption=mlkem768x25519plus','?security=tls&insecure=1','?unknown=required'):
            with self.subTest(suffix=suffix),self.assertRaises(ValueError):convert(f'vless://{UUID}@node.example.com:443'+suffix)


class PoolTests(unittest.TestCase):
    def record(self,key='a'):
        return dict(id=key,body='test',first_seen=AT,status='active',high_latency_streak=0)
    def result(self,key='a',latency=100,status='alive',ai=0):
        r=pool.blank(self.record(key));r.update(country='US',exit_ip='8.8.8.8',basic_latency_ms=latency,status=status);r['ai']['pass_count']=ai;return r
    def test_source_absence_preserves_history_and_credentials(self):
        state={'nodes':{'history':self.record('history')}}
        pool.merge(state,[], 'new',AT)
        self.assertEqual(state['nodes']['history']['status'],'active')
        a=convert('trojan://a@node.example.com:443')[2];b=convert('trojan://b@node.example.com:443')[2]
        self.assertNotEqual(pool.identity(a),pool.identity(b))
    def test_name_and_option_order_ignored(self):
        a=convert('hy2://p@node.example.com:443?sni=x.example.com#one')[2]
        b=convert('hysteria2://p@node.example.com:443?sni=x.example.com#two')[2]
        self.assertEqual(pool.identity(a),pool.identity(b))
    def test_confirmed_failure_cooldown(self):
        state={'nodes':{'a':self.record()}}
        self.assertEqual(pool.reconcile(state,[self.result(status='dead')],AT),[])
        self.assertEqual(state['nodes']['a']['status'],'isolated')
        self.assertEqual(state['nodes']['a']['retry_at'],'2026-11-09T10:30:00+00:00')
        pool.reconcile(state,[self.result(status='dead')],AT)
        self.assertEqual(state['nodes']['a']['retry_at'],'2026-11-09T12:00:00+00:00')
        pool.reconcile(state,[self.result(status='dead')],AT)
        self.assertEqual(state['nodes']['a']['status'],'cooldown')
        self.assertEqual(state['nodes']['a']['cooldown_until'],'2026-11-16T10:00:00+00:00')
    def test_two_high_latency_rounds(self):
        state={'nodes':{'a':self.record()}}
        pool.reconcile(state,[self.result(latency=1600)],AT)
        self.assertEqual(state['nodes']['a']['status'],'active')
        pool.reconcile(state,[self.result(latency=1700)],AT)
        self.assertEqual(state['nodes']['a']['status'],'slow')
        self.assertEqual(state['nodes']['a']['retry_at'],'2026-11-10T10:00:00+00:00')
    def test_ai_failure_remains_candidate(self):
        state={'nodes':{'a':self.record()}}
        self.assertEqual(len(pool.reconcile(state,[self.result(ai=0)],AT)),1)
        self.assertEqual(state['nodes']['a']['status'],'active')
    def test_capacity_country_round_robin(self):
        state={'nodes':{x:self.record(x) for x in ('a','b','c')}}
        results=[self.result('a',ai=3),self.result('b',ai=2),self.result('c',ai=1)];results[2]['country']='JP'
        with patch('pool.CAPACITY',2):pool.reconcile(state,results,AT)
        self.assertEqual(sum(n['status']=='active' for n in state['nodes'].values()),2)
        self.assertEqual(state['nodes']['c']['status'],'active')
    def test_restricted_marker_removes_saved_connection(self):
        uri='trojan://p@node.example.com:443';body=convert(uri)[2];ident=pool.identity(body)
        state={'nodes':{ident:self.record(ident)}}
        pool.merge(state,[('en',uri+'#__LOCKED_V1__:VIP')],'v',AT)
        self.assertEqual(state['nodes'][ident]['status'],'restricted')
        self.assertNotIn('body',state['nodes'][ident])
        pool.merge(state,[('en',uri+'#__LOCKED_V1__:VIP'),('zh',uri+'#ordinary')],'v',AT)
        self.assertEqual(state['nodes'][ident]['status'],'restricted')

    def test_cooldown_not_reimported_early(self):
        uri='trojan://p@node.example.com:443';ident=pool.identity(convert(uri)[2])
        state={'nodes':{ident:self.record(ident)}}
        state['nodes'][ident].update(status='cooldown',cooldown_until='2026-11-16T10:00:00+00:00')
        pool.merge(state,[('en',uri)],'v',AT)
        self.assertEqual(state['nodes'][ident]['status'],'cooldown')

    def test_expired_cooldown_requeues_at_current_time(self):
        uri='trojan://p@node.example.com:443';body=convert(uri)[2];ident=pool.identity(body)
        state={'nodes':{ident:dict(id=ident,body=body,first_seen='2026-10-01T00:00:00+00:00',status='cooldown',cooldown_until='2026-11-01T00:00:00+00:00',failure_rounds=3,high_latency_streak=2)}}
        pool.merge(state,[('en',uri)],'v',AT)
        self.assertEqual(state['nodes'][ident]['status'],'pending')
        self.assertEqual(state['nodes'][ident]['queued_at'],AT)
        self.assertEqual(state['nodes'][ident]['failure_rounds'],0)
        self.assertEqual(state['nodes'][ident]['high_latency_streak'],0)

    def test_missing_or_mismatched_shard_never_publishes(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder,patch('pool.WORK',Path(folder)):
            pool.write(Path(folder)/'manifest.json',{'cycle':'a','shards':1,'ids':['a']})
            pool.write(Path(folder)/'state.json',{'nodes':{}})
            with self.assertRaises(RuntimeError):pool.finalize()
            pool.write(Path(folder)/'result-0.json',{'cycle':'b','index':0,'results':[]})
            with self.assertRaises(RuntimeError):pool.finalize()

    def test_upstream_outage_still_retests_existing_pool(self):
        import tempfile
        from pathlib import Path
        state={'nodes':{'a':self.record()},'source_version':'previous','last_cycle':'2026-11-09T01:00:00+00:00'}
        with tempfile.TemporaryDirectory() as folder,patch('pool.WORK',Path(folder)),patch('pool.state_load',return_value=state),patch('pool.api',side_effect=OSError),patch('pool.now',return_value=AT):
            pool.prepare(force=True)
            m=pool.read(Path(folder)/'manifest.json')
            self.assertEqual(m['source_version'],'previous')
            self.assertEqual(m['source_error'],'OSError')
            self.assertEqual(m['ids'],['a'])

    def test_no_ai_winners_does_not_destroy_live_candidates(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder,patch('pool.WORK',Path(folder)),patch('pool.ROOT',Path(folder)),patch('pool.now',return_value=AT),patch('export_clients.write_exports'):
            (Path(folder)/'subscriptions').mkdir()
            pool.write(Path(folder)/'state.json',{'nodes':{'a':self.record()}})
            pool.write(Path(folder)/'manifest.json',{'cycle':'a','shards':1,'ids':['a'],'source_version':'v','summary':{}})
            pool.write(Path(folder)/'result-0.json',{'cycle':'a','index':0,'results':[self.result(ai=0)]})
            pool.write(Path(folder)/'measured.json',{'cycle':'a','environment':{'profile':'test'},'results':[self.result(ai=0)]})
            pool.finalize()
            state=pool.read(Path(folder)/'published-state.json')
            self.assertEqual(state['nodes']['a']['status'],'active')
            self.assertEqual(pool.read(Path(folder)/'subscriptions/free-nodes.json')['nodes'],0)


if __name__=='__main__':unittest.main()
