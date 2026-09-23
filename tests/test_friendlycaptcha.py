import json
import unittest

try:
    from .abstract import AbstractTest
except ImportError:
    from abstract import AbstractTest

from capskip.exceptions import ValidationException

URL = 'https://mysite.com/signup'
SITEKEY = 'FCMGEMUD2M567T8G'

# A v1 token: four dot-separated parts, a few hundred characters.
V1_TOKEN = ('c62c4da36bbaf7f253873035832709ef.aqwpWwdbzRWKY/UQAQwwpgAAAAAAAAAAM7hBvJOzqjc=.'
            'AAAAAArcCQABAAAAxv8QAAIAAACKYRgA.AgAB')

V1_MODULE_SCRIPT = 'https://cdn.example.com/friendly-challenge@0.9.19/widget.module.min.js'
V2_MODULE_SCRIPT = 'https://cdn.example.com/@friendlycaptcha/sdk@0.1.6/site.min.js'


class FriendlyCaptchaApiClient():
    """Mock client returning a realistic Friendly Captcha answer."""

    def __init__(self, token=V1_TOKEN):
        self.token = token

    def in_(self, files={}, **kwargs):
        self.incomings = kwargs
        self.incoming_files = files
        return 'OK|123'

    def res(self, **kwargs):
        if kwargs.get('json') in (1, '1'):
            return json.dumps({
                'status': 1,
                'request': self.token,
                'solution': {'token': self.token},
                'cost': '0.00299',
                'errorId': 0,
            })
        return 'OK|' + self.token


class FriendlyCaptchaTest(AbstractTest):

    def setUp(self):
        super().setUp()
        self.solver.api_client = FriendlyCaptchaApiClient()

    def solve(self, **kwargs):
        params = {'sitekey': SITEKEY, 'url': URL}
        params.update(kwargs)
        return self.solver.friendly_captcha(**params)

    def assert_sent(self, expected):
        expected.update({'key': 'API_KEY'})
        self.assertEqual(self.solver.api_client.incomings, expected)

    # -- what goes out ----------------------------------------------------

    def test_basic(self):
        result = self.solve()

        self.assert_sent({
            'method': 'friendly_captcha',
            'sitekey': SITEKEY,
            'pageurl': URL,
        })
        self.assertEqual(result['captchaId'], '123')

    def test_method_uses_the_documented_underscore_spelling(self):
        """The server accepts friendlycaptcha too, but friendly_captcha is what
        the parameter table documents and what 2Captcha's own SDKs send."""
        self.solve()

        self.assertEqual(
            self.solver.api_client.incomings['method'], 'friendly_captcha')

    def test_explicit_version(self):
        for version in ('v1', 'v2'):
            with self.subTest(version=version):
                self.solve(version=version)
                self.assertEqual(
                    self.solver.api_client.incomings['version'], version)

    def test_bare_digit_version_is_accepted(self):
        """The server takes a bare 1 or 2 as well as v1/v2."""
        self.solve(version=2)

        self.assertEqual(self.solver.api_client.incomings['version'], 2)

    def test_module_script_is_forwarded(self):
        """The script URL is the most reliable version signal there is: it is the
        build the site actually loads."""
        self.solve(module_script=V2_MODULE_SCRIPT)

        self.assertEqual(
            self.solver.api_client.incomings['module_script'], V2_MODULE_SCRIPT)

    def test_camelcase_script_aliases(self):
        self.solve(moduleScript=V1_MODULE_SCRIPT, nomoduleScript='https://x/widget.min.js')

        sent = self.solver.api_client.incomings
        self.assertEqual(sent['module_script'], V1_MODULE_SCRIPT)
        self.assertEqual(sent['nomodule_script'], 'https://x/widget.min.js')

    def test_eu_tenant_is_forwarded(self):
        """Both tenants mint a token for the same sitekey, so the wrong one is
        only caught by the target site's own verification."""
        self.solve(api_server='eu')

        self.assertEqual(self.solver.api_client.incomings['api_server'], 'eu')

    def test_unset_optional_is_not_sent(self):
        self.solve(version=None, module_script=None, api_server=None)

        self.assert_sent({
            'method': 'friendly_captcha',
            'sitekey': SITEKEY,
            'pageurl': URL,
        })

    def test_proxy(self):
        self.solve(proxy={'type': 'SOCKS5H', 'uri': 'login:pass@1.2.3.4:8080'})

        self.assert_sent({
            'method': 'friendly_captcha',
            'sitekey': SITEKEY,
            'pageurl': URL,
            'proxy': 'login:pass@1.2.3.4:8080',
            'proxytype': 'SOCKS5H',
        })

    # -- what is refused before it costs a round-trip ---------------------

    def test_unknown_version_is_refused_locally(self):
        """Solving the wrong version returns a well-formed token the site
        rejects, so a typo must not reach the server as a silent default."""
        with self.assertRaises(ValidationException) as caught:
            self.solve(version='v3')

        self.assertIn('v1', str(caught.exception))

    def test_missing_sitekey_is_refused(self):
        self.assertRaises(
            ValidationException, self.solver.friendly_captcha, '', URL)

    def test_missing_pageurl_is_refused(self):
        self.assertRaises(
            ValidationException, self.solver.friendly_captcha, SITEKEY, '')

    def test_unknown_parameter_is_refused(self):
        self.assertRaises(ValidationException, self.solve, challenge_url='https://x')

    def test_socks4_is_refused(self):
        self.assertRaises(
            ValidationException, self.solve,
            proxy={'type': 'SOCKS4', 'uri': '1.2.3.4:1080'})

    # -- what comes back --------------------------------------------------

    def test_token_is_exposed(self):
        result = self.solve()

        self.assertEqual(result['token'], V1_TOKEN)
        self.assertEqual(result['code'], V1_TOKEN)

    def test_token_is_passed_through_verbatim(self):
        """A v1 token's dot-separated parts include base64 padding and slashes;
        nothing may trim or re-encode them."""
        result = self.solve()

        self.assertEqual(result['token'].count('.'), 3)
        self.assertIn('/', result['token'])
        self.assertIn('=', result['token'])

    def test_a_large_v2_token_survives_intact(self):
        """A v2 token is a single opaque string of roughly six kilobytes."""
        v2_token = 'AQQA.' + ('a' * 6000)
        self.solver.api_client = FriendlyCaptchaApiClient(token=v2_token)
        result = self.solve()

        self.assertEqual(result['token'], v2_token)
        self.assertEqual(len(result['token']), len(v2_token))

    def test_solution_object_is_not_leaked_to_the_caller(self):
        result = self.solve()

        self.assertNotIn('solution', result)


if __name__ == '__main__':
    unittest.main()
