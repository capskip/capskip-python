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

# What CapSkip hands back for a *legacy* challenge: base64 of the solved
# challenge document, with the winning counter in `number`.
SOLVED = dict(CHALLENGE_DOC, number=9661)
TOKEN = base64.b64encode(json.dumps(SOLVED).encode()).decode()

# A PoW v2 answer is shaped completely differently: no top-level `number`, and
# the counter sits at `solution.counter`. Captured from a real PBKDF2/SHA-256
# deployment (captcha.seventy9.co.uk), the scheme altcha.org documents today.
V2_PAYLOAD = {
    'challenge': {
        'parameters': {
            'algorithm': 'PBKDF2/SHA-256',
            'cost': 50000,
            'expiresAt': 1789224090,
            'keyLength': 32,
            'keyPrefix': '00',
            'nonce': '634c4f591fd086beb40d67312b85808a',
            'salt': '511e1c75edbf295278c9bfb68191053c',
        },
        'signature': '9197e4a35ebff399d669e747c7c5e6ab079b30fe3437df268dc7caf34cf9e281',
    },
    'solution': {
        'counter': 47,
        'derivedKey': '0099db7cb36864d8875ff8305c9a3d2649b1f72cb774de1c',
    },
}
V2_TOKEN = base64.b64encode(json.dumps(V2_PAYLOAD).encode()).decode()
V2_NUMBER = 47


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

    def test_expands_number_for_a_proof_of_work_v2_answer(self):
        # A v2 token carries no top-level `number` -- the counter is at
        # `solution.counter`, and the server reports it as `solution.number` in
        # the poll payload. Reading only the token's own `number` silently drops
        # it for every PBKDF2 site, which is the scheme ALTCHA recommends.
        class V2Client(AltchaApiClient):
            def res(self, **kwargs):
                return json.dumps({
                    'status': 1,
                    'request': V2_TOKEN,
                    'solution': {'token': V2_TOKEN, 'number': V2_NUMBER},
                })

        self.solver.api_client = V2Client()
        result = self.solve()

        self.assertEqual(result['token'], V2_TOKEN)
        self.assertEqual(result['number'], V2_NUMBER)

    def test_proof_of_work_v2_number_falls_back_to_the_token(self):
        # Without the server's solution object -- a plain-text poll -- the
        # counter is still recoverable from inside the payload.
        class V2NoSolution(AltchaApiClient):
            def res(self, **kwargs):
                return json.dumps({'status': 1, 'request': V2_TOKEN})

        self.solver.api_client = V2NoSolution()
        result = self.solve()

        self.assertEqual(result['number'], V2_NUMBER)

    def test_solution_is_not_leaked_into_the_result(self):
        # The poll's `solution` object is plumbing: its two fields are already
        # exposed as `token` and `number`.
        result = self.solve()

        self.assertNotIn('solution', result)

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
