import json
import unittest

try:
    from .abstract import AbstractTest
except ImportError:
    from abstract import AbstractTest

from capskip.exceptions import ValidationException
from capskip.solver import _apply_amazon_waf_solution

URL = 'https://www.example.com/'
SITEKEY = 'AQIDAHjcYuEXAMPLEghicBgQ/7bFaQZ+m5FKCMDnO+vTbNg96AHDh0IR5vgzHNceHYqZR+GOAAAAfjB8'
IV = 'CgAFRDIjfgAAA5yY'
CONTEXT = 'Rbp3r8fvbuhmrCqpUe8Mh1TLvs8OSKJZiSs2vCF4dt9rxVZI7xYJa2n5k/9r+XaXe7KUIu2I8nXTDHHkDvIOTDc2'
CHALLENGE_JS = 'https://3f2a9c7d41b0.edge.sdk.awswaf.com/3f2a9c7d41b0/8e51d0c7a2f4/challenge.js'
CAPTCHA_JS = 'https://3f2a9c7d41b0.edge.sdk.awswaf.com/3f2a9c7d41b0/8e51d0c7a2f4/captcha.js'
WIDGET_KEY = 'Xr9kEXAMPLE2bWQx1vTq8LmZ0aYc4dHs7nFp3gJt6uKw5eRi9AbCdEfGh=_0_1'
JSAPI_JS = 'https://5b7e0a19c3d8.us-east-1.captcha-sdk.awswaf.com/5b7e0a19c3d8/jsapi.js'

# What CapSkip hands back: not a token, but the pair AWS WAF trades for the
# aws-waf-token cookie on its own /voucher endpoint.
SOLUTION = {
    'captcha_voucher': 'eyJ2b3VjaGVyIjoiRVhBTVBMRSJ9.9QwZcEXAMPLEvoucherJk4LmN0pQ',
    'existing_token': '7d4c2a91-EXAMPLE-4f0b-9e6d-3a1b5c8e2f70:EQoAeXAMPLEtokenAAAA:Wm9wc2E=',
}


class AmazonWafApiClient():
    """Mock client returning a realistic AWS WAF answer (an object, not a token)."""

    def in_(self, files={}, **kwargs):
        self.incomings = kwargs
        self.incoming_files = files
        return 'OK|123'

    def res(self, **kwargs):
        if kwargs.get('json') in (1, '1'):
            return json.dumps({'status': 1, 'request': SOLUTION})
        return 'OK|' + json.dumps(SOLUTION)


class AmazonWafTest(AbstractTest):

    def setUp(self):
        super().setUp()
        self.solver.api_client = AmazonWafApiClient()

    def solve(self, **kwargs):
        params = {'sitekey': SITEKEY, 'iv': IV, 'context': CONTEXT, 'url': URL}
        params.update(kwargs)
        return self.solver.amazon_waf(**params)

    def assert_sent(self, expected):
        expected.update({'key': 'API_KEY'})
        self.assertEqual(self.solver.api_client.incomings, expected)

    # -- what goes out ----------------------------------------------------

    def test_challenge_page(self):
        result = self.solve(challenge_script=CHALLENGE_JS, captcha_script=CAPTCHA_JS)

        self.assert_sent({
            'method': 'amazon_waf',
            'sitekey': SITEKEY,
            'iv': IV,
            'context': CONTEXT,
            'pageurl': URL,
            'challenge_script': CHALLENGE_JS,
            'captcha_script': CAPTCHA_JS,
        })
        self.assertEqual(result['captchaId'], '123')

    def test_positional_arguments_follow_2captcha(self):
        """`amazon_waf(sitekey, iv, context, url)` is 2Captcha's order, so code
        written against it keeps working unchanged."""
        self.solver.amazon_waf(SITEKEY, IV, CONTEXT, URL)

        self.assert_sent({
            'method': 'amazon_waf',
            'sitekey': SITEKEY,
            'iv': IV,
            'context': CONTEXT,
            'pageurl': URL,
        })

    def test_iv_and_context_may_be_left_out(self):
        """Left out, CapSkip reads them from pageurl at solve time -- and an
        unset one must not reach the server as the string 'None'."""
        self.solver.amazon_waf(SITEKEY, url=URL)

        self.assert_sent({
            'method': 'amazon_waf',
            'sitekey': SITEKEY,
            'pageurl': URL,
        })

    def test_empty_iv_and_context_mean_not_sent(self):
        """The server treats '' exactly like an absent value."""
        self.solver.amazon_waf(SITEKEY, '', '', URL)

        self.assert_sent({
            'method': 'amazon_waf',
            'sitekey': SITEKEY,
            'pageurl': URL,
        })

    def test_widget_page(self):
        self.solver.amazon_waf(sitekey=WIDGET_KEY, url=URL, jsapiScript=JSAPI_JS)

        self.assert_sent({
            'method': 'amazon_waf',
            'sitekey': WIDGET_KEY,
            'pageurl': URL,
            'jsapiScript': JSAPI_JS,
        })

    def test_script_aliases(self):
        """createTask callers arrive with challengeScript / captchaScript, and
        jsapi_script is the snake-case spelling of the documented jsapiScript."""
        self.solve(challengeScript=CHALLENGE_JS, captchaScript=CAPTCHA_JS)
        sent = self.solver.api_client.incomings
        self.assertEqual(sent['challenge_script'], CHALLENGE_JS)
        self.assertEqual(sent['captcha_script'], CAPTCHA_JS)
        self.assertNotIn('challengeScript', sent)

        self.solver.amazon_waf(WIDGET_KEY, url=URL, jsapi_script=JSAPI_JS)
        self.assertEqual(self.solver.api_client.incomings['jsapiScript'], JSAPI_JS)

    def test_proxy(self):
        self.solve(proxy={'type': 'SOCKS5H', 'uri': 'login:pass@1.2.3.4:8080'})

        sent = self.solver.api_client.incomings
        self.assertEqual(sent['proxy'], 'login:pass@1.2.3.4:8080')
        self.assertEqual(sent['proxytype'], 'SOCKS5H')

    def test_uses_the_browser_timeout(self):
        """A browser mints the token the voucher belongs to, so the solve gets
        recaptchaTimeout like the other browser-backed methods."""
        captured = {}
        original = self.solver.solve

        def spy(**kwargs):
            captured.update(kwargs)
            return original(**kwargs)

        self.solver.recaptcha_timeout = 654
        self.solver.solve = spy
        self.solve()
        self.assertEqual(captured['timeout'], 654)

    # -- what is refused before it costs a round-trip ---------------------

    def test_missing_sitekey_is_refused(self):
        self.assertRaises(ValidationException, self.solver.amazon_waf, '', IV, CONTEXT, URL)

    def test_missing_pageurl_is_refused(self):
        self.assertRaises(ValidationException, self.solver.amazon_waf, SITEKEY, IV, CONTEXT)

    def test_non_http_pageurl_is_refused(self):
        self.assertRaises(ValidationException, self.solve, url='ftp://example.com/')
        self.assertRaises(ValidationException, self.solve, url='example.com')

    def test_iv_without_context_is_refused(self):
        with self.assertRaises(ValidationException) as caught:
            self.solve(context=None)
        self.assertIn('context', str(caught.exception))

    def test_context_without_iv_is_refused(self):
        self.assertRaises(ValidationException, self.solve, iv='')

    def test_off_aws_scripts_are_refused(self):
        """CapSkip POSTs the solution to the host the script names, so it
        refuses any script that is not on awswaf.com."""
        bad = [
            'https://evil.example.com/abc/challenge.js',
            'http://3f2a9c7d41b0.edge.sdk.awswaf.com/3f2a9c7d41b0/challenge.js',
            'https://awswaf.com.evil.example/3f2a9c7d41b0/challenge.js',
            'https://user:pw@3f2a9c7d41b0.edge.sdk.awswaf.com/3f2a9c7d41b0/challenge.js',
            'https://3f2a9c7d41b0.edge.sdk.awswaf.com:8443/3f2a9c7d41b0/challenge.js',
            'https://3f2a9c7d41b0.edge.sdk.awswaf.com/3f2a9c7d41b0/other.js',
            'https://3f2a9c7d41b0.edge.sdk.awswaf.com/challenge.js',
            'not a url',
        ]
        for url in bad:
            for key in ('challenge_script', 'captcha_script', 'jsapiScript'):
                with self.subTest(key=key, url=url):
                    self.assertRaises(ValidationException, self.solve, **{key: url})

    def test_script_with_query_string_is_accepted(self):
        self.solve(challenge_script=CHALLENGE_JS + '?v=2')
        self.assertEqual(
            self.solver.api_client.incomings['challenge_script'], CHALLENGE_JS + '?v=2')

    def test_unknown_parameter_is_refused(self):
        self.assertRaises(ValidationException, self.solve, gt='x')

    def test_socks4_is_refused(self):
        self.assertRaises(
            ValidationException, self.solve,
            proxy={'type': 'SOCKS4', 'uri': '1.2.3.4:1080'})

    # -- what comes back --------------------------------------------------

    def test_result_is_expanded_into_the_pair(self):
        result = self.solve()

        self.assertEqual(result['captcha_voucher'], SOLUTION['captcha_voucher'])
        self.assertEqual(result['existing_token'], SOLUTION['existing_token'])

    def test_raw_code_is_preserved(self):
        result = self.solve()

        raw = result['code']
        parsed = raw if isinstance(raw, dict) else json.loads(raw)
        self.assertEqual(parsed, SOLUTION)

    def test_a_json_string_answer_is_expanded_too(self):
        """Plain-text res.php sends the same object as one line after OK|."""
        result = _apply_amazon_waf_solution(
            {'captchaId': '123', 'code': json.dumps(SOLUTION)})

        self.assertEqual(result['captcha_voucher'], SOLUTION['captcha_voucher'])
        self.assertEqual(result['existing_token'], SOLUTION['existing_token'])

    def test_unparseable_answer_is_left_untouched(self):
        class Odd(AmazonWafApiClient):
            def res(self, **kwargs):
                return json.dumps({'status': 1, 'request': 'not-json-at-all'})

        self.solver.api_client = Odd()
        result = self.solve()

        self.assertEqual(result['code'], 'not-json-at-all')
        self.assertNotIn('captcha_voucher', result)


if __name__ == '__main__':
    unittest.main()
