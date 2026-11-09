import copy
import unittest
from unittest.mock import patch
import enrich


def node(identity, ip, ai=3, grade=2, risk=0, delay=100, speed=10, media=True, country='US'):
    return dict(id=identity, exit_ip=ip, country=country, ai={'pass_count':ai,'latency_ms':delay},
                quality={'grade':grade,'risk_score':risk,'flags':dict(is_vpn=False,is_tor=False,is_proxy=False,is_datacenter=grade==2)}, media={'all_passed':media},download_mbps=speed)


class RecommendationTests(unittest.TestCase):
    def test_one_country_winner_quality_before_latency(self):
        candidates=[node('fast','1',grade=2,delay=1),node('best','2',grade=3,delay=500),
                    node('jp-slow','3',country='JP',delay=300),node('jp-fast','4',country='JP',delay=100)]
        self.assertEqual([n['id'] for n in enrich.country_best(candidates,limit=1)],['jp-fast','best'])

    def test_country_top_four_distinct_exits_without_padding(self):
        candidates=[node(str(i),str(i),delay=10+i) for i in range(8)]
        candidates += [node('duplicate','0',delay=1),node('unknown','20',grade=1),node('bad','21',grade=0),
                       node('no-speed','22',speed=None),node('only-one-ai','23',ai=1),node('jp','30',country='JP')]
        result=enrich.country_best(candidates)
        us=[n for n in result if n['country']=='US']
        self.assertEqual([n['id'] for n in us],['duplicate','1','2','3'])
        self.assertEqual(len([n for n in result if n['country']=='JP']),1)

    def test_clean_ip_requires_complete_zero_risk_nonhosting_flags(self):
        clean=node('clean','1',grade=3,risk=0)
        dirty=copy.deepcopy(clean);dirty['id']='dirty';dirty['quality']['flags']['is_proxy']=True
        unknown=copy.deepcopy(clean);unknown['id']='unknown';unknown['quality'].pop('flags')
        candidates=[dirty,unknown,node('hosting','4',grade=2,risk=0),node('nonzero','5',grade=3,risk=1)]
        self.assertEqual(enrich.clean_ip_best(candidates),[])
        self.assertEqual(enrich.clean_ip_best(candidates+[clean])[0]['id'],'clean')

    def test_download_selection_not_limited_to_media_unlock(self):
        candidates=[node('slow','1',speed=10),node('fast','2',speed=100,media=False),node('failed','3',speed=None)]
        self.assertEqual(enrich.download_best(candidates)[0]['id'],'fast')
        self.assertEqual(enrich.download_best([node('failed','3',speed=None)]),[])

    def test_names_include_only_real_measurements(self):
        self.assertEqual(enrich.measured_name('US 01',node('a','1',speed=12.345,delay=99)),'US 01｜99ms · 12.35Mbps')
        self.assertEqual(enrich.measured_name('US 01',node('a','1',speed=None,delay=99)),'US 01｜99ms')

    def test_ai_service_count_before_quality_then_latency(self):
        candidates=[node('two','1',ai=2,grade=3,delay=1),node('three','2',ai=3,grade=2,delay=500)]
        self.assertEqual(enrich.select(candidates)[0][0]['id'],'three')
        candidates=[node('fast','1',grade=2,delay=1),node('quality','2',grade=3,delay=500)]
        self.assertEqual(enrich.select(candidates)[0][0]['id'],'quality')
        candidates=[node('slow','1',delay=500),node('fast','2',delay=100)]
        self.assertEqual(enrich.select(candidates)[0][0]['id'],'fast')

    def test_backup_requires_distinct_exit(self):
        ai,_=enrich.select([node('a','same'),node('b','same'),node('c','different',delay=500)])
        self.assertEqual([n['id'] for n in ai],['a','c'])

    def test_media_must_pass_all_and_have_measured_speed(self):
        candidates=[node('bad','1',media=False,speed=999),node('missing','2',speed=None),
                    node('slow','3',speed=10),node('fast','4',speed=20)]
        self.assertEqual([n['id'] for n in enrich.select(candidates)[1]],['fast','slow'])
        self.assertEqual(enrich.select([node('bad','1',media=False)])[1],[])

    def test_unknown_quality_not_assumed_clean(self):
        self.assertEqual(enrich.quality_from({},'8.8.8.8')['label'],'未知')
        self.assertEqual(enrich.quality_from({'ip':'8.8.8.8','risk':{}},'8.8.8.8')['label'],'未知')
        d={'ip':'8.8.8.8','risk':dict(is_vpn=False,is_tor=False,is_proxy=False,is_datacenter=True,risk_score=0)}
        self.assertEqual(enrich.quality_from(d,'8.8.8.8')['label'],'机房')
        self.assertEqual(enrich.quality_from(d,'1.1.1.1')['label'],'未知')
        d['risk']['is_tor']=True
        self.assertEqual(enrich.quality_from(d,'8.8.8.8')['label'],'风险')

    def test_netflix_login_does_not_count_as_unlock(self):
        with patch('enrich.fetch',return_value={'code':200,'body':'og:title Netflix Login 81280792 70143836'}):
            self.assertFalse(enrich.netflix(1))

    def test_media_unknown_or_blocked_is_not_pass(self):
        with patch('enrich.netflix',return_value=True),patch('enrich.disney',return_value=False),patch('enrich.youtube',return_value=True),patch('enrich.prime',return_value=True):
            result=enrich.check_media(1)
            self.assertEqual(result['pass_count'],3)
            self.assertFalse(result['all_passed'])


if __name__=='__main__':
    unittest.main()
