import json
import unittest

try:
    from .abstract import AbstractTest
except ImportError:
    from abstract import AbstractTest

from capskip.exceptions import ValidationException

URL = 'https://smartcaptcha.yandexcloud.net/demo'
SITEKEY = 'ysc1_DAo8nFPdNCMHkAwYxIUJFxW5IIJd99BBfeeeee'
# base64 of t=...;i=203.0.113.25;D=...: shaped like a real token, carrying a
# documentation address.
TOKEN = ('dD0xNzk0NDE5NTg3O2k9MjAzLjAuMTEzLjI1O0Q9QjQ1RjJBN0MxRTkwRDM2ODU0QzA1M0M3QTFF'
         'MkIzQzRENUU2RjcwODE5MkEzQjRDNUQ2RTdGODA5MUEyQjNDNEQ1RTZGNzA4MTt1PTE3OTQ0MTk1'
         'ODcxMjM0NTY3ODk7aD01ZjBjMmE5ZTYxZDg0YjM3YTBjMWU5YjJkNmY0YTg3Mw==')


class YandexApiClient():
    """Mock client answering as CapSkip's res.php does for a SmartCaptcha token:
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


class YandexSmartTest(AbstractTest):

    def setUp(self):
        super().setUp()
        self.solver.api_client = YandexApiClient()

    def solve(self, **kwargs):
        params = {'sitekey': SITEKEY, 'url': URL}
        params.update(kwargs)
        return self.solver.yandex_smart(**params)

    def assert_sent(self, expected):
        expected.update({'key': 'API_KEY'})
        self.assertEqual(self.solver.api_client.incomings, expected)

    # -- what goes out ----------------------------------------------------

    def test_basic(self):
        result = self.solve()

        self.assert_sent({
            'method': 'yandex',
            'sitekey': SITEKEY,
            'pageurl': URL,
        })
        self.assertEqual(result['captchaId'], '123')

    def test_every_option(self):
        self.solve(userAgent='Mozilla/5.0 (caller)',
                   proxy={'type': 'SOCKS5', 'uri': 'login:password@203.0.113.7:1080'})

        self.assert_sent({
            'method': 'yandex',
            'sitekey': SITEKEY,
            'pageurl': URL,
            'useragent': 'Mozilla/5.0 (caller)',
            'proxy': 'login:password@203.0.113.7:1080',
            'proxytype': 'SOCKS5',
        })

    def test_pageurl_keyword_is_accepted_for_url(self):
        self.solver.yandex_smart(sitekey=SITEKEY, url=None, pageurl=URL)

        self.assertEqual(self.solver.api_client.incomings['pageurl'], URL)

    def test_sitekey_is_trimmed(self):
        self.solve(sitekey='  ' + SITEKEY + '\n')

        self.assertEqual(self.solver.api_client.incomings['sitekey'], SITEKEY)

    def test_sitekey_without_ysc1_prefix_is_accepted(self):
        """Older client keys carry no ysc1_ prefix; the server takes them."""
        self.solve(sitekey='FEXfAbHQsToo97VidNVk3j4dC74nGW1DgdxjtNB9')

    def test_sitekey_length_bounds(self):
        self.solve(sitekey='a' * 16)
        self.solve(sitekey='a' * 120)

    def test_empty_optionals_are_not_sent(self):
        self.solve(userAgent='', proxy=None)

        self.assertNotIn('useragent', self.solver.api_client.incomings)
        self.assertNotIn('proxy', self.solver.api_client.incomings)

    # -- refused locally, as the server would refuse them -----------------

    def test_missing_sitekey_is_refused(self):
        for value in ('', None):
            with self.assertRaises(ValidationException):
                self.solve(sitekey=value)

    def test_malformed_sitekey_is_refused(self):
        for value in ('a' * 15, 'a' * 121, 'ysc1_has space in it', 'ysc1_dotted.key.value',
                      'ysc1_" onload="x'):
            with self.assertRaises(ValidationException, msg=value):
                self.solve(sitekey=value)

    def test_bad_pageurl_is_refused(self):
        for value in ('', 'smartcaptcha.yandexcloud.net/demo', 'ftp://example.com/', 'https://'):
            with self.assertRaises(ValidationException, msg=value):
                self.solve(url=value)

    def test_unknown_parameter_is_refused(self):
        for extra in ({'action': 'login'}, {'img_type': 'smart_captcha'}):
            with self.assertRaises(ValidationException, msg=extra):
                self.solve(**extra)

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
        self.solver.api_client = YandexApiClient(
            {'status': 1, 'request': '', 'solution': {'token': TOKEN}})

        result = self.solve()

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

    def test_recaptcha_timeout_is_used(self):
        """The widget runs in a real browser, so it takes the longer timeout."""
        seen = {}
        original = self.solver.wait_result

        def wait_result(id_, timeout, polling_interval, json=0):
            seen['timeout'] = timeout
            return original(id_, timeout, polling_interval, json=json)

        self.solver.wait_result = wait_result
        self.solve()

        self.assertEqual(seen['timeout'], self.solver.recaptcha_timeout)


if __name__ == '__main__':
    unittest.main()
