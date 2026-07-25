import json
import unittest

try:
    from .abstract import AbstractTest
except ImportError:
    from abstract import AbstractTest

from capskip.exceptions import ValidationException

GT = '81388ea1fc187e0c335c0a8907ff2625'
CHALLENGE = '7cf6a8b1a2c34d5e6f7089abcdef0123'
URL = 'https://mysite.com/page/with/geetest'

SOLUTION = {
    'geetest_challenge': CHALLENGE,
    'geetest_validate': '9b1f4a2c8e7d6b5a4938271605f4e3d2',
    'geetest_seccode': '9b1f4a2c8e7d6b5a4938271605f4e3d2|jordan',
}


class GeeTestApiClient():
    """Mock client returning a realistic GeeTest v3 answer (JSON string in `request`)."""

    def in_(self, files={}, **kwargs):
        self.incomings = kwargs
        self.incoming_files = files
        return 'OK|123'

    def res(self, **kwargs):
        payload = json.dumps(SOLUTION)
        if kwargs.get('json') in (1, '1'):
            return json.dumps({'status': 1, 'request': payload})
        return 'OK|' + payload


class GeeTestTest(AbstractTest):

    def setUp(self):
        super().setUp()
        self.solver.api_client = GeeTestApiClient()

    def solve(self, **kwargs):
        params = {'gt': GT, 'challenge': CHALLENGE, 'url': URL}
        params.update(kwargs)
        return self.solver.geetest(**params)

    def assert_sent(self, expected):
        expected.update({'key': 'API_KEY'})
        self.assertEqual(self.solver.api_client.incomings, expected)

    def test_basic(self):
        result = self.solve()

        self.assert_sent({
            'method': 'geetest',
            'gt': GT,
            'challenge': CHALLENGE,
            'pageurl': URL,
        })
        self.assertEqual(result['captchaId'], '123')

    def test_api_server(self):
        self.solve(api_server='api-na.geetest.com')

        self.assert_sent({
            'method': 'geetest',
            'gt': GT,
            'challenge': CHALLENGE,
            'pageurl': URL,
            'api_server': 'api-na.geetest.com',
        })

    def test_api_server_camel_case_alias(self):
        self.solve(apiServer='api-na.geetest.com')

        self.assert_sent({
            'method': 'geetest',
            'gt': GT,
            'challenge': CHALLENGE,
            'pageurl': URL,
            'api_server': 'api-na.geetest.com',
        })

    def test_proxy(self):
        self.solve(proxy={'type': 'HTTP', 'uri': '1.2.3.4:3128'})

        self.assert_sent({
            'method': 'geetest',
            'gt': GT,
            'challenge': CHALLENGE,
            'pageurl': URL,
            'proxy': '1.2.3.4:3128',
            'proxytype': 'HTTP',
        })

    def test_returns_raw_json_in_code(self):
        # Kept verbatim so callers can forward it to code written against
        # another solver's API.
        result = self.solve()

        self.assertEqual(json.loads(result['code']), SOLUTION)

    def test_expands_solution_fields(self):
        result = self.solve()

        self.assertEqual(result['challenge'], SOLUTION['geetest_challenge'])
        self.assertEqual(result['validate'], SOLUTION['geetest_validate'])
        self.assertEqual(result['seccode'], SOLUTION['geetest_seccode'])

    def test_non_json_code_is_left_alone(self):
        class PlainClient(GeeTestApiClient):
            def res(self, **kwargs):
                return json.dumps({'status': 1, 'request': 'not-json'})

        self.solver.api_client = PlainClient()
        result = self.solve()

        self.assertEqual(result['code'], 'not-json')
        self.assertNotIn('validate', result)

    def test_caller_timeout_overrides_the_default(self):
        # GeeTest defaults to the longer recaptchaTimeout budget, but an explicit
        # timeout must win rather than collide with it.
        result = self.solve(timeout=42)

        self.assertEqual(result['captchaId'], '123')
        self.assertNotIn('timeout', self.solver.api_client.incomings)

    def test_missing_challenge_raises(self):
        with self.assertRaises(ValidationException):
            self.solver.geetest(gt=GT, challenge='', url=URL)

    def test_missing_gt_raises(self):
        with self.assertRaises(ValidationException):
            self.solver.geetest(gt='', challenge=CHALLENGE, url=URL)

    def test_missing_url_raises(self):
        # pageurl is documented as required; fail locally rather than paying a
        # round-trip for ERROR_PAGEURL.
        with self.assertRaises(ValidationException):
            self.solver.geetest(gt=GT, challenge=CHALLENGE, url='')

    def test_unsupported_parameter_raises(self):
        with self.assertRaises(ValidationException):
            self.solve(sitekey='not-a-geetest-param')

    def test_accepted_proxy_types(self):
        for proxytype in ('HTTP', 'HTTPS', 'SOCKS5', 'SOCKS5H', 'socks5h'):
            with self.subTest(proxytype=proxytype):
                self.solve(proxy={'type': proxytype, 'uri': '1.2.3.4:3128'})
                self.assertEqual(
                    self.solver.api_client.incomings['proxytype'], proxytype
                )

    def test_socks4_is_rejected(self):
        # CapSkip maps only HTTP/HTTPS/SOCKS5/SOCKS5H and answers
        # ERROR_BAD_PARAMETERS for SOCKS4, so fail before the round-trip.
        with self.assertRaises(ValidationException):
            self.solve(proxy={'type': 'SOCKS4', 'uri': '1.2.3.4:3128'})

    def test_unknown_proxy_type_is_rejected(self):
        with self.assertRaises(ValidationException):
            self.solve(proxy='1.2.3.4:3128', proxytype='FTP')


if __name__ == '__main__':
    unittest.main()
