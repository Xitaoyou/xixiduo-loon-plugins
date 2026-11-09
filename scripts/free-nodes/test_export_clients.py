import base64
import json
import unittest
from urllib.parse import urlsplit,unquote,parse_qs
from export_clients import convert,render
from test_update import vmess
import update


class ExportTests(unittest.TestCase):
    def test_ws_tls_parameters_and_unicode_names(self):
        _,_,body=update.convert(vmess(path='/a?b=1,c=2',sni='tls.example.com'))
        name='🇯🇵 日本 01｜100ms · 20.00Mbps'
        clash,uri=convert(name,body)
        sr=json.loads(base64.b64decode(uri[8:]))
        self.assertEqual(clash['ws-opts']['path'],sr['path'])
        self.assertEqual(sr['ps'],name)
        self.assertEqual(clash['uuid'],sr['id'])
        self.assertEqual(clash['servername'],sr['sni'])
        self.assertFalse(clash['skip-cert-verify'])

    def test_hysteria_password_ipv6_and_sni(self):
        body='Hysteria2,[2606:4700:4700::1111],443,"user:p@ss",sni="tls.example.com",skip-cert-verify=false,udp=true'
        clash,uri=convert('test',body)
        u=urlsplit(uri)
        self.assertEqual(unquote(u.username),clash['password'])
        self.assertEqual(u.hostname,clash['server'])
        self.assertEqual(parse_qs(u.query)['sni'][0],clash['sni'])

    def test_format_outputs_have_identical_entries_and_direct_default(self):
        _,_,body=update.convert(vmess())
        yaml,sr=render('first = '+body+'\nsecond = '+body+'\n')
        uris=base64.b64decode(sr).decode().splitlines()
        self.assertEqual(len(uris),2)
        self.assertIn('"proxies":["DIRECT","first","second"]',yaml)
        self.assertNotIn('url-test',yaml)


if __name__=='__main__':
    unittest.main()
