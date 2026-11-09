import json
import subprocess
import unittest
from unittest.mock import patch

import health
from test_update import vmess
import update


class HealthTests(unittest.TestCase):
    def test_vmess_config_preserves_parameters(self):
        _, _, body = update.convert(vmess(path='/ws?a=1,b=2', host='cdn.example.com', sni='tls.example.com'))
        out = health.outbound(body, 'test', resolve=lambda _: '8.8.8.8')
        self.assertEqual(out['transport']['path'], '/ws?a=1,b=2')
        self.assertEqual(out['transport']['headers']['Host'], 'cdn.example.com')
        self.assertEqual(out['tls'], dict(enabled=True, server_name='tls.example.com', insecure=False))
        self.assertEqual(out['server'], '8.8.8.8')

    def test_hy2_config_preserves_credentials(self):
        _, _, body = update.convert('hy2://user%3Apass@node.example.com:8443?sni=tls.example.com')
        out = health.outbound(body, 'test', resolve=lambda _: '8.8.8.8')
        self.assertEqual(out['password'], 'user:pass')
        self.assertEqual(out['server_port'], 8443)
        self.assertFalse(out['tls']['insecure'])

    def test_trace_requires_valid_response(self):
        self.assertEqual(health.parse_trace('ip=8.8.8.8\nloc=US\n'), 'US')
        for value in ('ip=127.0.0.1\nloc=US', 'ip=8.8.8.8\nloc=unknown', '<html>403</html>'):
            with self.assertRaises(ValueError):
                health.parse_trace(value)

    def test_proxy_is_explicit_no_fallback_or_insecure_tls(self):
        response = subprocess.CompletedProcess([], 0, stdout='ip=8.8.8.8\nloc=US\n')
        with patch('health.subprocess.run', return_value=response) as run:
            self.assertEqual(health.request_trace(20001), 'US')
        args = run.call_args.args[0]
        self.assertEqual(args[args.index('--proxy') + 1], 'http://127.0.0.1:20001')
        self.assertNotIn('--insecure', args)
        self.assertNotIn('--location', args)

    def test_private_dns_rejected(self):
        with patch('health.socket.getaddrinfo', return_value=[(2, 1, 6, '', ('127.0.0.1', 0))]):
            with self.assertRaises(ValueError):
                health.public_ip('example.com')

    def test_country_label(self):
        self.assertEqual(health.country_label('JP'), '🇯🇵 日本')
        self.assertIn('IS', health.country_label('IS'))


if __name__ == '__main__':
    unittest.main()
