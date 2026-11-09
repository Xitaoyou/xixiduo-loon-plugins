import base64
import json
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
import update


def vmess(**changes):
    d = dict(add='node.example.com', port=443, id='52396e06-041a-4cc2-be5c-8525eb457809',
             net='ws', type='none', tls='tls', scy='auto', aid=0, ps='test', path='/ws', host='cdn.example.com')
    d.update(changes)
    return 'vmess://' + base64.b64encode(json.dumps(d).encode()).decode()


class ConversionTests(unittest.TestCase):
    def test_tls_ws_preserved(self):
        _, _, body = update.convert(vmess(sni='tls.example.com'))
        self.assertIn('transport=ws', body)
        self.assertIn('sni="tls.example.com"', body)
        self.assertIn('skip-cert-verify=false', body)

    def test_parameter_dedup(self):
        self.assertEqual(update.convert(vmess(ps='a'))[0], update.convert(vmess(ps='b'))[0])
        self.assertNotEqual(update.convert(vmess(path='/a'))[0], update.convert(vmess(path='/b'))[0])

    def test_restricted_and_unsupported(self):
        for changes in (dict(ps='__LOCKED_V1__:VIP'), dict(ps='a\u2063'), dict(net='grpc'),
                        dict(type='http'), dict(insecure=1), dict(aid=64), dict(add='127.0.0.1'),
                        dict(path='/ws\n[Rule]'), dict(echConfigList='required')):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                update.convert(vmess(**changes))

    def test_hy2_password_and_tls(self):
        _, _, body = update.convert('hy2://user%3Apass@node.example.com:443?sni=tls.example.com#name')
        self.assertIn('"user:pass"', body)
        self.assertIn('sni="tls.example.com"', body)
        for query in ('insecure=1', 'obfs=salamander', 'sni=a&sni=b'):
            with self.assertRaises(ValueError):
                update.convert('hy2://secret@node.example.com:443?' + query)

    def test_bad_update_preserves_old(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'nodes.txt'
            p.write_text('old-successful-content')
            with self.assertRaises(ValueError):
                update.publish('invalid', p)
            self.assertEqual(p.read_text(), 'old-successful-content')

    def test_decrypt_and_bad_padding(self):
        key = b'd3JV8tcWGPzgcVbB'
        pad = PKCS7(128).padder()
        plain = pad.update(b'test\n') + pad.finalize()
        enc = Cipher(algorithms.AES(key), modes.CBC(key)).encryptor()
        blob = base64.b64encode(enc.update(plain) + enc.finalize())
        self.assertEqual(update.decrypt(blob), 'test\n')
        with self.assertRaises(ValueError):
            update.decrypt(base64.b64encode(b'\0' * 16))


if __name__ == '__main__':
    unittest.main()
