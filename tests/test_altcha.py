import base64
import json
import unittest

try:
    from .abstract import AbstractTest
except ImportError:
    from abstract import AbstractTest

from capskip.exceptions import ValidationException

URL = 'https://mysite.com/signup'
CHALLENGE_URL = 'https://mysite.com/captcha/api/altcha/challenge'
CHALLENGE_DOC = {
    'algorithm': 'SHA-256',
    'challenge': '3dd28253be6cc0c54d95f7f98c517e68',
    'salt': '46d5b1c8871e5152d902ee3f?expires=1893456000',
    'signature': '4b1cf0e0be0f4e5247e50b0f9a449830',
    'maxnumber': 1000000,
}
CHALLENGE_JSON = json.dumps(CHALLENGE_DOC)

# What CapSkip hands back: base64 of the solved challenge document, with the
# winning counter in `number`.
SOLVED = dict(CHALLENGE_DOC, number=9661)
TOKEN = base64.b64encode(json.dumps(SOLVED).encode()).decode()


class AltchaApiClient():
    """Mock client returning a realistic ALTCHA answer (base64 token in `request`)."""

    def in_(self, files={}, **kwargs):
        self.incomings = kwargs
        self.incoming_files = files
        return 'OK|123'

    def res(self, **kwargs):
        if kwargs.get('json') in (1, '1'):
            return json.dumps({
                'status': 1,
                'request': TOKEN,
                'solution': {'token': TOKEN, 'number': 9661},
            })
        return 'OK|' + TOKEN


class AltchaTest(AbstractTest):

    def setUp(self):
        super().setUp()
        self.solver.api_client = AltchaApiClient()

    def solve(self, **kwargs):
        params = {'url': URL, 'challenge_url': CHALLENGE_URL}
        params.update(kwargs)
        return self.solver.altcha(**params)

    def assert_sent(self, expected):
        expected.update({'key': 'API_KEY'})
        self.assertEqual(self.solver.api_client.incomings, expected)

    def test_basic(self):
        result = self.solve()

        self.assert_sent({
            'method': 'altcha',
            'pageurl': URL,
            'challenge_url': CHALLENGE_URL,
        })
        self.assertEqual(result['captchaId'], '123')

    def test_challenge_json_string(self):
        self.solve(challenge_url=None, challenge_json=CHALLENGE_JSON)

        self.assert_sent({
            'method': 'altcha',
            'pageurl': URL,
            'challenge_json': CHALLENGE_JSON,
        })

    def test_challenge_json_accepts_a_dict(self):
        # The form body can only carry a string, so a document passed as a dict
        # is serialized rather than stringified into Python's repr.
        self.solve(challenge_url=None, challenge_json=CHALLENGE_DOC)

        sent = self.solver.api_client.incomings['challenge_json']
        self.assertEqual(json.loads(sent), CHALLENGE_DOC)

    def test_camel_case_aliases(self):
        self.solve(challenge_url=None, challengeUrl=CHALLENGE_URL)

        self.assert_sent({
            'method': 'altcha',
            'pageurl': URL,
            'challenge_url': CHALLENGE_URL,
        })

    def test_challenge_json_camel_case_alias(self):
        self.solve(challenge_url=None, challengeJSON=CHALLENGE_JSON)

        self.assert_sent({
            'method': 'altcha',
            'pageurl': URL,
            'challenge_json': CHALLENGE_JSON,
        })

    def test_both_challenge_params_are_allowed(self):
        # CapSkip is deliberately more permissive than 2Captcha here: sending
        # both is not an error, the inline document simply wins.
        self.solve(challenge_json=CHALLENGE_JSON)

        self.assert_sent({
            'method': 'altcha',
            'pageurl': URL,
            'challenge_url': CHALLENGE_URL,
            'challenge_json': CHALLENGE_JSON,
        })

    def test_proxy(self):
        self.solve(proxy={'type': 'HTTP', 'uri': '1.2.3.4:3128'})

        self.assert_sent({
            'method': 'altcha',
            'pageurl': URL,
            'challenge_url': CHALLENGE_URL,
            'proxy': '1.2.3.4:3128',
            'proxytype': 'HTTP',
        })

    def test_returns_raw_token_in_code(self):
        result = self.solve()

        self.assertEqual(result['code'], TOKEN)

    def test_expands_token_and_number(self):
        result = self.solve()

        self.assertEqual(result['token'], TOKEN)
        self.assertEqual(result['number'], 9661)

    def test_undecodable_token_is_left_alone(self):
        class PlainClient(AltchaApiClient):
            def res(self, **kwargs):
                return json.dumps({'status': 1, 'request': 'not-base64-json'})

        self.solver.api_client = PlainClient()
        result = self.solve()

        self.assertEqual(result['code'], 'not-base64-json')
        self.assertNotIn('number', result)

    def test_uses_the_default_timeout_not_the_recaptcha_one(self):
        # ALTCHA is CPU proof-of-work measured in milliseconds, not a browser
        # solve, so it must not inherit reCAPTCHA's much longer budget.
        captured = {}
        original = self.solver.wait_result

        def spy(id_, timeout, polling_interval, json=0):
            captured['timeout'] = timeout
            return original(id_, timeout, polling_interval, json=json)

        self.solver.wait_result = spy
        self.solve()

        self.assertEqual(captured['timeout'], self.solver.default_timeout)
        self.assertNotEqual(captured['timeout'], self.solver.recaptcha_timeout)

    def test_missing_url_raises(self):
        with self.assertRaises(ValidationException):
            self.solver.altcha(url='', challenge_url=CHALLENGE_URL)

    def test_missing_both_challenge_params_raises(self):
        # CapSkip answers ERROR_BAD_PARAMETERS; fail locally instead of paying
        # for the round-trip.
        with self.assertRaises(ValidationException):
            self.solver.altcha(url=URL)

    def test_empty_challenge_params_raise(self):
        with self.assertRaises(ValidationException):
            self.solver.altcha(url=URL, challenge_url='', challenge_json='')

    def test_unsupported_parameter_raises(self):
        with self.assertRaises(ValidationException):
            self.solve(sitekey='not-an-altcha-param')

    def test_accepted_proxy_types(self):
        for proxytype in ('HTTP', 'HTTPS', 'SOCKS5', 'SOCKS5H', 'socks5h'):
            with self.subTest(proxytype=proxytype):
                self.solve(proxy={'type': proxytype, 'uri': '1.2.3.4:3128'})
                self.assertEqual(
                    self.solver.api_client.incomings['proxytype'], proxytype
                )

    def test_socks4_is_rejected(self):
        with self.assertRaises(ValidationException):
            self.solve(proxy={'type': 'SOCKS4', 'uri': '1.2.3.4:3128'})

    def test_unknown_proxy_type_is_rejected(self):
        with self.assertRaises(ValidationException):
            self.solve(proxy='1.2.3.4:3128', proxytype='FTP')


if __name__ == '__main__':
    unittest.main()
