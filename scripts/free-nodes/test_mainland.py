import base64
import copy
from datetime import datetime, timedelta, timezone
import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import mainland
import mainland_policy as policy
from mainland_worker import Budget, BudgetExceeded, download, make_config, RX_LIMIT, TX_LIMIT, MONTH_LIMIT, MiB
from test_update import vmess
import update
from export_clients import brand_overseas

AT = datetime(2026, 11, 10, 2, tzinfo=timezone.utc)


def row(i=0, country='US', speed=20, latency=100):
    return dict(id=str(i), country=country, exit_ip=f'8.8.{i // 250}.{i % 250 + 1}',
                status='alive', basic_latency_ms=latency, download_mbps=speed,
                download_samples_mbps=[speed] * 3, measurement_profile=policy.PROFILE,
                ai=dict(passed=True, pass_count=3, latency_ms=100, services={}),
                quality=dict(grade=1, risk_score=None, label='未知'),
                media=dict(all_passed=False, services=
                           {k: False for k in ('Netflix', 'Disney+', 'YouTube Premium', 'Prime Video')}))


class SelectionTests(unittest.TestCase):
    def observe(self, rows, previous=None, day=0):
        return policy.update_history(previous or {}, rows, (AT + timedelta(days=day)).isoformat(), str(day))

    def test_thresholds_and_unknown_quality(self):
        self.assertTrue(policy.eligible(row(speed=10, latency=1000)))
        for change in ({'download_mbps': 9.99}, {'basic_latency_ms': 1001},
                       {'download_mbps': None}, {'basic_latency_ms': None},
                       {'quality': {'grade': 0}}, {'ai': {'pass_count': 1}},
                       {'measurement_profile': 'overseas'}, {'status': 'dead'}):
            n = row()
            n.update(change)
            self.assertFalse(policy.eligible(n))

    def test_country_cap_30_cap_and_distinct_egress(self):
        rows = [row(i, country=f'{chr(65+i//6)}A') for i in range(60)]
        rows[1]['exit_ip'] = rows[0]['exit_ip']
        selected = policy.choose(self.observe(rows), rows)
        self.assertEqual(len(selected), 30)
        self.assertEqual(len({n['exit_ip'] for n in selected}), 30)
        self.assertLessEqual(max(sum(n['country'] == c for n in selected)
                                 for c in {n['country'] for n in selected}), 4)

    def test_no_historical_candidate_accumulation(self):
        previous = self.observe([row(1), row(2)])
        current = self.observe([row(1)], previous, 1)
        self.assertEqual(set(current['history']), {'1'})
        self.assertEqual([n['id'] for n in policy.choose(current, [row(1)])], ['1'])

    def test_daily_samples_failures_and_exit_changes(self):
        n = row()
        s = self.observe([n])
        s = self.observe([n], s)  # Same day is replaced, never counted twice.
        self.assertEqual(len(s['history']['0']), 1)
        s = self.observe([n], s, 1)
        failed = row()
        failed.update(status='dead', exit_ip='', download_mbps=None, basic_latency_ms=None)
        s = self.observe([failed], s, 2)
        s = self.observe([n], s, 3)
        self.assertEqual(policy.choose(s, [n]), [])
        n['exit_ip'] = '1.1.1.1'
        s = self.observe([n], s, 4)
        self.assertEqual(len(s['history']['0']), 1)
        self.assertEqual(len(policy.choose(s, [n])), 1)

    def test_recommendations_only_selected_and_distinct(self):
        rows = [row(i) for i in range(3)]
        for n in rows:
            n.update(conservative_mbps=20)
        rows[1]['exit_ip'] = rows[0]['exit_ip']
        picks = policy.recommendations(rows)
        for kind in ('ai', 'download'):
            self.assertEqual(len({n['exit_ip'] for n in picks[kind]}), 2)
        self.assertEqual(picks['media'], [])
        self.assertEqual(picks['clean_ip'], [])

    def test_download_uses_total_time_and_three_complete_samples(self):
        class Http:
            calls = 0
            def fetch(self, *args, **kwargs):
                self.calls += 1
                return dict(code=200, size=4 * MiB, seconds=4)
        http = Http()
        result = download(http, 21000)
        self.assertEqual(http.calls, 3)
        self.assertEqual(result['download_mbps'], 8.39)


class BudgetTests(unittest.TestCase):
    def test_reserve_survives_crash_and_final_settlement(self):
        with tempfile.TemporaryDirectory() as d:
            ledger = Path(d) / 'budget.json'
            values = [0, 0]
            b = Budget(ledger, counter=lambda: tuple(values)).start()
            self.assertEqual(json.loads(ledger.read_text())['tx_upper_bound'], TX_LIMIT)
            values[:] = [500, 200]
            b.close()
            self.assertEqual(json.loads(ledger.read_text())['tx_upper_bound'], 200)

    def test_round_and_monthly_cutoff(self):
        with tempfile.TemporaryDirectory() as d:
            ledger = Path(d) / 'budget.json'
            values = [0, 0]
            b = Budget(ledger, counter=lambda: tuple(values))
            values[0] = RX_LIMIT - 32 * MiB
            with self.assertRaises(BudgetExceeded):
                b.check()
            values[:] = [0, 0]
            ledger.write_text(json.dumps(dict(month=b.month, tx_upper_bound=MONTH_LIMIT - 1)))
            with self.assertRaises(BudgetExceeded):
                Budget(ledger, counter=lambda: tuple(values)).start()

    def test_counter_reset_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            values = [100, 100]
            b = Budget(Path(d) / 'b.json', counter=lambda: tuple(values))
            values[:] = [0, 0]
            with self.assertRaises(BudgetExceeded):
                b.check()


class PublicationTests(unittest.TestCase):
    def test_only_explicit_no_header_is_normalized(self):
        prefix = 'vless://52396e06-041a-4cc2-be5c-8525eb457809@node.example.com:443?security=none'
        ordinary = update.convert(prefix)[2]
        self.assertEqual(update.convert(mainland.normalize_source_uri(prefix+'&headerType=none'))[2], ordinary)
        for query in ('headerType=http', 'headerType=none&headerType=none', 'spx=/required', 'packetEncoding=xudp'):
            with self.assertRaises(ValueError):
                update.convert(mainland.normalize_source_uri(prefix+'&'+query))

    def test_only_ecfg6_and_source_cap(self):
        blob = b'verified-encrypted-placeholder'
        sha = hashlib.sha1(b'blob ' + str(len(blob)).encode() + b'\0' + blob).hexdigest()
        def api(path):
            return {'sha': 'commit'} if path.endswith('commits/main') else {'tree': [{'path': 'data/ecfg6', 'sha': sha}]}
        for count in (82, 129):
            text = '\n'.join(vmess(port=1000+i) for i in range(count))
            with patch('mainland.api', side_effect=api), patch('mainland.decrypt', return_value=text), patch('mainland.fetch_bytes', return_value=blob) as fetch:
                if count == 129:
                    with self.assertRaises(RuntimeError):
                        mainland.source()
                else:
                    _, nodes, _ = mainland.source()
                    self.assertEqual(len(nodes), 82)
                self.assertTrue(all(call.args[0].endswith('/data/ecfg6') for call in fetch.call_args_list))

    def fixture(self):
        n = row()
        _, _, body = update.convert(vmess())
        doc = dict(cycle='testcycle', source_version='commit', nodes=[dict(id='0', body=body)])
        result = dict(cycle='testcycle', source_version='commit', complete=True,
                      measurement_profile=policy.PROFILE, tested_at=AT.isoformat(), results=[n])
        return doc, result

    def test_three_exports_same_names_and_no_detection_time_rewrite(self):
        doc, result = self.fixture()
        files, state = mainland.render_selection(doc, result, {})
        loon = [line.split(' = ', 1)[0] for line in files['free-nodes.txt'].splitlines()]
        proxies = [json.loads(line.strip()[2:]) for line in
                   files['free-nodes-clash.yaml'].split('proxy-groups:')[0].splitlines()
                   if line.strip().startswith('- ')]
        self.assertEqual(loon, [p['name'] for p in proxies])
        uris = base64.b64decode(files['free-nodes-shadowrocket.txt']).decode().splitlines()
        self.assertEqual(len(uris), len(loon))
        self.assertEqual([json.loads(base64.b64decode(uri[8:]))['ps'] for uri in uris], loon)
        self.assertTrue(all(n.startswith('大陆测｜') for n in loon))
        status = json.loads(files['status.json'])
        self.assertEqual(status['updated_at'], AT.isoformat())
        self.assertEqual(state['cycle'], doc['cycle'])

    def test_missing_cycle_or_candidate_is_rejected(self):
        doc, result = self.fixture()
        for change in ({'cycle': 'wrong'}, {'results': []}, {'complete': False}):
            r = copy.deepcopy(result)
            r.update(change)
            with self.assertRaises(RuntimeError):
                mainland.validate(doc, r)

    def test_failure_preserves_content_and_success_time(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d) / 'bundle'
            folder.mkdir()
            doc, result = self.fixture()
            mainland.write(folder / 'input.json', doc)
            published = Path(d) / 'public/subscriptions/mainland'
            published.mkdir(parents=True)
            old = dict(updated_at=AT.isoformat(), nodes=4)
            mainland.write(published / 'status.json', old)
            (published / 'free-nodes.txt').write_text('previous')
            with patch('mainland.commit_files') as commit:
                with self.assertRaises(RuntimeError):
                    mainland.finish(folder, Path(d) / 'missing.json', Path(d) / 'public')
                updated = json.loads(commit.call_args.args[1]['status.json'])
                self.assertEqual(updated['updated_at'], old['updated_at'])
                self.assertEqual(updated['nodes'], 4)
                self.assertFalse(updated['last_attempt']['ok'])
            self.assertEqual((published / 'free-nodes.txt').read_text(), 'previous')

    def test_smoke_cannot_publish(self):
        with tempfile.TemporaryDirectory() as d:
            doc, result = self.fixture()
            doc['smoke'] = True
            mainland.write(Path(d) / 'input.json', doc)
            mainland.write(Path(d) / 'result.json', result)
            with self.assertRaises(RuntimeError), patch('mainland.commit_files') as commit:
                mainland.finish(d, Path(d) / 'result.json', d)
            commit.assert_not_called()

    def test_overseas_branding_is_idempotent(self):
        text = 'node = body\n'
        meta = dict(updated_at='unchanged', node_results=[{'name': 'node'}])
        once = brand_overseas(text, meta)
        self.assertEqual(brand_overseas(once, meta), once)
        self.assertEqual(meta['updated_at'], 'unchanged')
        self.assertEqual(meta['node_results'][0]['name'], '海外测｜node')

    def test_core_binds_loopback_and_never_installs_direct_fallback(self):
        doc, _ = self.fixture()
        doc['nodes'][0]['outbound'] = dict(type='vmess', server='node.example.com')
        with patch('health.public_ip', return_value='8.8.8.8'):
            config, ports, _ = make_config(doc['nodes'])
        self.assertTrue(all(i['listen'] == '127.0.0.1' for i in config['inbounds']))
        self.assertTrue(all(o['type'] != 'direct' for o in config['outbounds']))
        self.assertEqual(set(ports), {'0'})


if __name__ == '__main__':
    unittest.main()
