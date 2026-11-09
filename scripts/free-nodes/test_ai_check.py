import unittest
from unittest.mock import patch

import ai_check


class AITests(unittest.TestCase):
    def test_two_distinct_services_required(self):
        with patch('ai_check.chatgpt', return_value=200), patch('ai_check.claude', return_value=None), patch('ai_check.gemini', return_value=None):
            self.assertFalse(ai_check.check_ai(1)['passed'])
        with patch('ai_check.chatgpt', return_value=200), patch('ai_check.claude', return_value=400), patch('ai_check.gemini', return_value=None):
            result = ai_check.check_ai(1)
            self.assertTrue(result['passed'])
            self.assertEqual(result['pass_count'], 2)
            self.assertEqual(result['latency_ms'], 300)

    def test_chatgpt_challenge_and_country_block_not_pass(self):
        def req(port, url):
            if 'ios.' in url:
                return dict(code=403, body='Request is not allowed. Please try again later.', ms=100)
            return dict(code=403, body='{"error":"unsupported_country"}', ms=200)
        self.assertIsNone(ai_check.chatgpt(1, req))
        self.assertIsNone(ai_check.chatgpt(1, lambda *_: dict(code=403, body='Just a moment...', ms=100)))

    def test_chatgpt_expected_marker_and_valid_compliance(self):
        def req(port, url):
            return dict(code=403, body='Request is not allowed. Please try again later.', ms=100) if 'ios.' in url else dict(code=200, body='{}', ms=300)
        self.assertEqual(ai_check.chatgpt(1, req), 200)

    def test_claude_trace_is_region_check(self):
        self.assertEqual(ai_check.claude(1, lambda *_: dict(code=200, body='ip=8.8.8.8\nloc=US', ms=150)), 150)
        self.assertIsNone(ai_check.claude(1, lambda *_: dict(code=200, body='ip=8.8.8.8\nloc=HK', ms=150)))
        self.assertIsNone(ai_check.claude(1, lambda *_: dict(code=403, body='ip=8.8.8.8\nloc=US', ms=150)))

    def test_gemini_requires_marker_and_not_blocked_country(self):
        self.assertEqual(ai_check.gemini(1, lambda *_: dict(code=200, body=',2,1,200,"USA"', ms=300)), 300)
        for body in ('hello', ',2,1,200,"CHN"', 'verify you are human ,2,1,200,"USA"'):
            self.assertIsNone(ai_check.gemini(1, lambda *_: dict(code=200, body=body, ms=300)))

    def test_timeout_does_not_count(self):
        with patch('ai_check.chatgpt', side_effect=ValueError), patch('ai_check.claude', return_value=200), patch('ai_check.gemini', return_value=None):
            self.assertFalse(ai_check.check_ai(1)['passed'])


if __name__ == '__main__':
    unittest.main()
