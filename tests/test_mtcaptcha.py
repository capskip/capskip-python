import json
import unittest

try:
    from .abstract import AbstractTest
except ImportError:
    from abstract import AbstractTest

from capskip.exceptions import ValidationException

URL = 'https://2captcha.com/demo/mtcaptcha'
SITEKEY = 'MTPublic-KzqLY1cKH'
TOKEN = ('v1(0f3c9e2a,7b1d4c88,MTPublic-KzqLY1cKH,5e0c2a9f61d84b37a0c1e9b2d6f4a873,'
         'Qm9ndXNUb2tlbkZvclRlc3RzT25seV9fTm90QVJlYWxNVENhcHRjaGFUb2tlbi1BYkNkRWZHaA**)')


class MtCaptchaApiClient():
    """Mock client answering as CapSkip's res.php does for MTCaptcha:
    {status, request: token} with json=1, OK|token without."""

    def __init__(self, json_reply=None):
        self.json_reply = json_reply

    def in_(self, files={}, **kwargs):
        self.incomings = kwargs
        self.incoming_files = files
        return 'OK|123'

    def res(self, **kwargs):
        if kwargs.get('json') in (1, '1'):
            return json.dumps(self.json_reply or {'status': 1, 'request': TOKEN})
        return 'OK|' + TOKEN


class MtCaptchaTest(AbstractTest):

    def setUp(self):
        super().setUp()
        self.solver.api_client = MtCaptchaApiClient()

    def solve(self, **kwargs):
        params = {'sitekey': SITEKEY, 'url': URL}
        params.update(kwargs)
        return self.solver.mtcaptcha(**params)

    def assert_sent(self, expected):
        expected.update({'key': 'API_KEY'})
        self.assertEqual(self.solver.api_client.incomings, expected)

    # -- what goes out ----------------------------------------------------

    def test_basic(self):
        result = self.solve()

        self.assert_sent({
            'method': 'mt_captcha',
            'sitekey': SITEKEY,
            'pageurl': URL,
        })
        self.assertEqual(result['captchaId'], '123')

    def test_every_option(self):
        self.solve(action='login', userAgent='Mozilla/5.0 (caller)',
                   proxy={'type': 'HTTPS', 'uri': 'login:password@203.0.113.7:3128'})

        self.assert_sent({
            'method': 'mt_captcha',
            'sitekey': SITEKEY,
            'pageurl': URL,
            'action': 'login',
            'useragent': 'Mozilla/5.0 (caller)',
            'proxy': 'login:password@203.0.113.7:3128',
            'proxytype': 'HTTPS',
        })

    def test_pageurl_keyword_is_accepted_for_url(self):
        self.solver.mtcaptcha(sitekey=SITEKEY, url=None, pageurl=URL)

        self.assertEqual(self.solver.api_client.incomings['pageurl'], URL)

    def test_sk_prefix_is_stripped(self):
        """MTCaptcha's getchallenge query names the key sk=MTPublic-...; callers copy it."""
        for value in ('sk=' + SITEKEY, ' SK=' + SITEKEY + ' ', '  ' + SITEKEY):
            self.solve(sitekey=value)
            self.assertEqual(self.solver.api_client.incomings['sitekey'], SITEKEY)

    def test_empty_optionals_are_not_sent(self):
        self.solve(action='', userAgent=None)

        self.assertNotIn('action', self.solver.api_client.incomings)
        self.assertNotIn('useragent', self.solver.api_client.incomings)

    # -- refused locally, as the server would refuse them -----------------

    def test_missing_sitekey_is_refused(self):
        for value in ('', None):
            with self.assertRaises(ValidationException):
                self.solve(sitekey=value)

    def test_malformed_sitekey_is_refused(self):
        for value in ('KzqLY1cKH', 'MTPublic-', 'mtpublic-KzqLY1cKH',
                      'MTPublic-Kzq LY1', 'MTPublic-Kzq.LY1', 'MTPublic-' + 'a' * 56):
            with self.assertRaises(ValidationException, msg=value):
                self.solve(sitekey=value)

    def test_longest_sitekey_is_accepted(self):
        self.solve(sitekey='MTPublic-' + 'a' * 55)

    def test_bad_pageurl_is_refused(self):
        for value in ('', '2captcha.com/demo/mtcaptcha', 'ftp://example.com/', 'https://'):
            with self.assertRaises(ValidationException, msg=value):
                self.solve(url=value)

    def test_unknown_parameter_is_refused(self):
        with self.assertRaises(ValidationException):
            self.solve(invisible=1)

    def test_socks4_is_refused(self):
        with self.assertRaises(ValidationException):
            self.solve(proxy={'type': 'SOCKS4', 'uri': '203.0.113.7:1080'})

    def test_nothing_is_sent_when_refused(self):
        with self.assertRaises(ValidationException):
            self.solve(sitekey='nope')
        self.assertFalse(hasattr(self.solver.api_client, 'incomings'))

    # -- what comes back --------------------------------------------------

    def test_token_is_code_and_token(self):
        result = self.solve()

        self.assertEqual(result['code'], TOKEN)
        self.assertEqual(result['token'], TOKEN)
        self.assertNotIn('solution', result)

    def test_solution_token_fills_an_empty_request(self):
        self.solver.api_client = MtCaptchaApiClient(
            {'status': 1, 'request': '', 'solution': {'token': TOKEN}})

        result = self.solve()

        self.assertEqual(result['code'], TOKEN)
        self.assertEqual(result['token'], TOKEN)

    def test_polls_with_json(self):
        calls = []
        client = self.solver.api_client
        original = client.res

        def res(**kwargs):
            calls.append(kwargs)
            return original(**kwargs)

        client.res = res
        self.solve()

        self.assertEqual(calls[0].get('json'), 1)

    def test_default_timeout_is_used(self):
        """No browser runs, so MTCaptcha keeps the default timeout like ALTCHA."""
        seen = {}
        original = self.solver.wait_result

        def wait_result(id_, timeout, polling_interval, json=0):
            seen['timeout'] = timeout
            return original(id_, timeout, polling_interval, json=json)

        self.solver.wait_result = wait_result
        self.solve()

        self.assertEqual(seen['timeout'], float(self.solver.default_timeout))


if __name__ == '__main__':
    unittest.main()
