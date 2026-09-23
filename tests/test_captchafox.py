import json
import unittest

try:
    from .abstract import AbstractTest
except ImportError:
    from abstract import AbstractTest

from capskip.exceptions import ValidationException

URL = 'https://mysite.com/page/with/captchafox'
SITEKEY = 'sk_xtNxpk6fCdFbxh1_xJeGflSdCE9tn99G'
TOKEN = '177f50c25b845601e5c779cdb51b040d523e8ab69efb4d5b343e28df07d05076'

# The UA the browser actually minted the token under. CapSkip never applies the
# caller's own, so these two must stay distinguishable in the tests below.
BROWSER_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36')
CALLER_UA = 'Mozilla/5.0 (the caller\'s own UA)'

MAM_API_SERVER = 'https://s.uicdn.com/mampkg/@mamdev/core.frontend.libs.captchafox/'


class CaptchaFoxApiClient():
    """Mock client returning a realistic CaptchaFox answer (a token plus the UA)."""

    def __init__(self, user_agent=BROWSER_UA):
        self.user_agent = user_agent

    def in_(self, files={}, **kwargs):
        self.incomings = kwargs
        self.incoming_files = files
        return 'OK|123'

    def res(self, **kwargs):
        if kwargs.get('json') in (1, '1'):
            payload = {
                'status': 1,
                'request': TOKEN,
                'solution': {'token': TOKEN},
                'cost': '0.00145',
                'errorId': 0,
            }
            if self.user_agent:
                payload['userAgent'] = self.user_agent
                payload['solution']['userAgent'] = self.user_agent
            return json.dumps(payload)
        return 'OK|' + TOKEN


class CaptchaFoxTest(AbstractTest):

    def setUp(self):
        super().setUp()
        self.solver.api_client = CaptchaFoxApiClient()

    def solve(self, **kwargs):
        params = {'sitekey': SITEKEY, 'url': URL}
        params.update(kwargs)
        return self.solver.captchafox(**params)

    def assert_sent(self, expected):
        expected.update({'key': 'API_KEY'})
        self.assertEqual(self.solver.api_client.incomings, expected)

    # -- what goes out ----------------------------------------------------

    def test_basic(self):
        result = self.solve()

        self.assert_sent({
            'method': 'captchafox',
            'sitekey': SITEKEY,
            'pageurl': URL,
        })
        self.assertEqual(result['captchaId'], '123')

    def test_mam_api_server_is_forwarded(self):
        """The widget source decides the token format: the MAM package returns a
        MAM_ prefixed token, and sending the wrong one fails silently at the
        target site rather than erroring here."""
        self.solve(api_server=MAM_API_SERVER)

        self.assertEqual(
            self.solver.api_client.incomings['api_server'], MAM_API_SERVER)

    def test_camelcase_api_server_alias(self):
        self.solve(apiServer=MAM_API_SERVER)

        self.assertEqual(
            self.solver.api_client.incomings['api_server'], MAM_API_SERVER)

    def test_useragent_is_forwarded(self):
        self.solve(useragent=CALLER_UA)

        self.assertEqual(self.solver.api_client.incomings['useragent'], CALLER_UA)

    def test_camelcase_useragent_alias(self):
        self.solve(userAgent=CALLER_UA)

        sent = self.solver.api_client.incomings
        self.assertEqual(sent['useragent'], CALLER_UA)
        self.assertNotIn('userAgent', sent)

    def test_unset_optional_is_not_sent(self):
        self.solve(api_server=None, useragent=None)

        self.assert_sent({
            'method': 'captchafox',
            'sitekey': SITEKEY,
            'pageurl': URL,
        })

    def test_proxy(self):
        self.solve(proxy={'type': 'HTTP', 'uri': 'login:password@1.2.3.4:8080'})

        self.assert_sent({
            'method': 'captchafox',
            'sitekey': SITEKEY,
            'pageurl': URL,
            'proxy': 'login:password@1.2.3.4:8080',
            'proxytype': 'HTTP',
        })

    def test_a_bare_proxy_defaults_to_http(self):
        self.solve(proxy='1.2.3.4:8080')

        self.assertEqual(self.solver.api_client.incomings['proxytype'], 'HTTP')

    # -- what is refused before it costs a round-trip ---------------------

    def test_missing_sitekey_is_refused(self):
        self.assertRaises(ValidationException, self.solver.captchafox, '', URL)

    def test_missing_pageurl_is_refused(self):
        self.assertRaises(ValidationException, self.solver.captchafox, SITEKEY, '')

    def test_unknown_parameter_is_refused(self):
        self.assertRaises(ValidationException, self.solve, version='v2')

    def test_socks4_is_refused(self):
        self.assertRaises(
            ValidationException, self.solve,
            proxy={'type': 'SOCKS4', 'uri': '1.2.3.4:1080'})

    # -- what comes back --------------------------------------------------

    def test_token_is_exposed(self):
        result = self.solve()

        self.assertEqual(result['token'], TOKEN)
        self.assertEqual(result['code'], TOKEN)

    def test_result_carries_the_user_agent_that_minted_the_token(self):
        """Not the one the caller sent -- CapSkip solves in its own browser, and
        the token has to be submitted under the UA that produced it."""
        result = self.solve(useragent=CALLER_UA)

        self.assertEqual(result['userAgent'], BROWSER_UA)
        self.assertNotEqual(result['userAgent'], CALLER_UA)

    def test_user_agent_is_absent_when_the_solve_reported_none(self):
        """A UA the solve did not actually use must never be invented."""
        self.solver.api_client = CaptchaFoxApiClient(user_agent=None)
        result = self.solve()

        self.assertNotIn('userAgent', result)
        self.assertEqual(result['token'], TOKEN)

    def test_solution_object_is_not_leaked_to_the_caller(self):
        result = self.solve()

        self.assertNotIn('solution', result)

    def test_token_is_read_from_solution_when_request_is_empty(self):
        """A client must never be left without the token the poll carried."""
        class Requestless(CaptchaFoxApiClient):
            def res(self, **kwargs):
                return json.dumps({
                    'status': 1, 'request': '', 'solution': {'token': TOKEN}})

        self.solver.api_client = Requestless()
        result = self.solve()

        self.assertEqual(result['token'], TOKEN)


if __name__ == '__main__':
    unittest.main()
