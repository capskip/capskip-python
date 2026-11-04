import json
import unittest

try:
    from .abstract import AbstractTest
except ImportError:
    from abstract import AbstractTest

from capskip.exceptions import ValidationException

URL = 'https://accounts.hcaptcha.com/demo'
SITEKEY = 'a5f74b19-9e45-40e0-b45d-47ff91b7a6c2'
TOKEN = 'P1_eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.hadwYXNza2V5xQZ2f3Kq8nV2'
RESP_KEY = 'E0_eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6IjA09wB1'
RQDATA = 'Wk2qT7bX+fV9rL0pZ3mN8cJ1hYsD6uE4gA5oR2iK/0='

# The UA the browser earned the token with, as CapSkip reports it. Kept apart
# from the caller's own so a test can tell which one came back.
BROWSER_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36')
CALLER_UA = 'Mozilla/5.0 (the caller own UA)'


class HCaptchaApiClient():
    """Mock client answering as CapSkip's res.php does for hCaptcha with json=1:
    {status, request: token, respKey, useragent}."""

    def __init__(self, resp_key=RESP_KEY, user_agent=BROWSER_UA):
        self.resp_key = resp_key
        self.user_agent = user_agent

    def in_(self, files={}, **kwargs):
        self.incomings = kwargs
        self.incoming_files = files
        return 'OK|123'

    def res(self, **kwargs):
        if kwargs.get('json') in (1, '1'):
            payload = {'status': 1, 'request': TOKEN, 'respKey': self.resp_key}
            if self.user_agent:
                payload['useragent'] = self.user_agent
            return json.dumps(payload)
        return 'OK|' + TOKEN


class HCaptchaTest(AbstractTest):

    def setUp(self):
        super().setUp()
        self.solver.api_client = HCaptchaApiClient()

    def solve(self, **kwargs):
        params = {'sitekey': SITEKEY, 'url': URL}
        params.update(kwargs)
        return self.solver.hcaptcha(**params)

    def assert_sent(self, expected):
        expected.update({'key': 'API_KEY'})
        self.assertEqual(self.solver.api_client.incomings, expected)

    # -- what goes out ----------------------------------------------------

    def test_basic(self):
        result = self.solve()

        self.assert_sent({
            'method': 'hcaptcha',
            'sitekey': SITEKEY,
            'pageurl': URL,
        })
        self.assertEqual(result['captchaId'], '123')

    def test_pageurl_keyword_is_accepted_for_url(self):
        self.solver.hcaptcha(sitekey=SITEKEY, url=None, pageurl=URL)

        self.assertEqual(self.solver.api_client.incomings['pageurl'], URL)

    def test_invisible_is_sent_as_1(self):
        for value in (1, True, '1', 'true'):
            self.solve(invisible=value)
            self.assertEqual(self.solver.api_client.incomings['invisible'], 1)

    def test_invisible_off_is_not_sent(self):
        """0 is the server's default; a bool False must not reach it as 'False'."""
        for value in (0, False, '0', 'false'):
            self.solve(invisible=value)
            self.assertNotIn('invisible', self.solver.api_client.incomings)

    def test_bad_invisible_is_refused(self):
        for value in (2, 'yes', 'invisible'):
            self.assertRaises(ValidationException, self.solve, invisible=value)

    def test_enterprise_rqdata_is_sent_as_data(self):
        self.solve(data=RQDATA)

        self.assertEqual(self.solver.api_client.incomings['data'], RQDATA)

    def test_useragent_is_forwarded(self):
        self.solve(useragent=CALLER_UA)

        self.assertEqual(self.solver.api_client.incomings['useragent'], CALLER_UA)

    def test_camelcase_useragent_alias(self):
        self.solve(userAgent=CALLER_UA)

        sent = self.solver.api_client.incomings
        self.assertEqual(sent['useragent'], CALLER_UA)
        self.assertNotIn('userAgent', sent)

    def test_unset_optionals_are_not_sent(self):
        self.solve(invisible=None, data=None, userAgent=None, proxy=None)

        self.assert_sent({
            'method': 'hcaptcha',
            'sitekey': SITEKEY,
            'pageurl': URL,
        })

    def test_empty_optionals_are_not_sent(self):
        self.solve(data='', userAgent='')

        self.assert_sent({
            'method': 'hcaptcha',
            'sitekey': SITEKEY,
            'pageurl': URL,
        })

    def test_proxy(self):
        self.solve(proxy={'type': 'SOCKS5', 'uri': 'login:password@1.2.3.4:1080'})

        self.assert_sent({
            'method': 'hcaptcha',
            'sitekey': SITEKEY,
            'pageurl': URL,
            'proxy': 'login:password@1.2.3.4:1080',
            'proxytype': 'SOCKS5',
        })

    def test_a_bare_proxy_defaults_to_http(self):
        self.solve(proxy='1.2.3.4:8080')

        self.assertEqual(self.solver.api_client.incomings['proxytype'], 'HTTP')

    def test_everything_together(self):
        self.solve(invisible=1, data=RQDATA, userAgent=CALLER_UA,
                   proxy={'type': 'HTTPS', 'uri': '1.2.3.4:8080'}, json=1)

        self.assert_sent({
            'method': 'hcaptcha',
            'sitekey': SITEKEY,
            'pageurl': URL,
            'invisible': 1,
            'data': RQDATA,
            'useragent': CALLER_UA,
            'proxy': '1.2.3.4:8080',
            'proxytype': 'HTTPS',
            'json': 1,
        })

    # -- what is refused before it costs a round-trip ---------------------

    def test_missing_sitekey_is_refused(self):
        self.assertRaises(ValidationException, self.solver.hcaptcha, '', URL)
        self.assertRaises(ValidationException, self.solver.hcaptcha, '   ', URL)

    def test_missing_pageurl_is_refused(self):
        self.assertRaises(ValidationException, self.solver.hcaptcha, SITEKEY, '')

    def test_non_http_pageurl_is_refused(self):
        for url in ('accounts.hcaptcha.com/demo', 'ftp://example.com/', 'javascript:alert(1)'):
            self.assertRaises(ValidationException, self.solver.hcaptcha, SITEKEY, url)

    def test_unknown_parameter_is_refused(self):
        # 2Captcha's `domain` is not part of CapSkip's hCaptcha API.
        self.assertRaises(ValidationException, self.solve, domain='js.hcaptcha.com')
        self.assertRaises(ValidationException, self.solve, enterprise=1)

    def test_socks4_is_refused(self):
        self.assertRaises(
            ValidationException, self.solve,
            proxy={'type': 'SOCKS4', 'uri': '1.2.3.4:1080'})

    def test_nothing_is_sent_when_refused(self):
        self.assertRaises(ValidationException, self.solver.hcaptcha, '', URL)
        self.assertFalse(hasattr(self.solver.api_client, 'incomings'))

    # -- what comes back --------------------------------------------------

    def test_token_is_exposed(self):
        result = self.solve()

        self.assertEqual(result['token'], TOKEN)
        self.assertEqual(result['code'], TOKEN)

    def test_resp_key_is_exposed(self):
        result = self.solve()

        self.assertEqual(result['respKey'], RESP_KEY)

    def test_empty_resp_key_stays_empty(self):
        self.solver.api_client = HCaptchaApiClient(resp_key='')
        result = self.solve()

        self.assertEqual(result['respKey'], '')
        self.assertEqual(result['token'], TOKEN)

    def test_resp_key_is_present_even_when_the_reply_has_none(self):
        class NoRespKey(HCaptchaApiClient):
            def res(self, **kwargs):
                return json.dumps({'status': 1, 'request': TOKEN})

        self.solver.api_client = NoRespKey()
        result = self.solve()

        self.assertEqual(result['respKey'], '')

    def test_result_carries_the_user_agent_that_earned_the_token(self):
        result = self.solve(userAgent=CALLER_UA)

        self.assertEqual(result['userAgent'], BROWSER_UA)

    def test_user_agent_is_absent_when_the_solve_reported_none(self):
        self.solver.api_client = HCaptchaApiClient(user_agent=None)
        result = self.solve()

        self.assertNotIn('userAgent', result)

    def test_polls_with_json(self):
        calls = []

        class Recording(HCaptchaApiClient):
            def res(self, **kwargs):
                calls.append(kwargs)
                return super().res(**kwargs)

        self.solver.api_client = Recording()
        self.solve()

        self.assertEqual(calls[0].get('json'), 1)

    def _record_timeout(self):
        seen = {}
        original = self.solver.wait_result

        def wait_result(id_, timeout, polling_interval, json=0):
            seen['timeout'] = timeout
            return original(id_, timeout, polling_interval, json=json)

        self.solver.wait_result = wait_result
        return seen

    def test_uses_the_browser_timeout(self):
        seen = self._record_timeout()
        self.solver.recaptcha_timeout = 321
        self.solve()

        self.assertEqual(seen['timeout'], 321)

    def test_explicit_timeout_wins(self):
        seen = self._record_timeout()
        self.solve(timeout=42)

        self.assertEqual(seen['timeout'], 42)


if __name__ == '__main__':
    unittest.main()
