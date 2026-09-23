import json
import unittest

try:
    from .abstract import AbstractTest
except ImportError:
    from abstract import AbstractTest

from capskip.exceptions import ValidationException
from capskip.solver import _apply_capy_solution

URL = 'https://mysite.com/login'
CAPTCHA_KEY = 'PUZZLE_Abc1dEFghIJKLM2no34P56q7rStu8v'

# What CapSkip hands back: not a token, but the three values the Capy widget
# would have written into the target form, plus respKey for shape-compatibility
# with 2Captcha's documented response.
SOLUTION = {
    'captchakey': CAPTCHA_KEY,
    'challengekey': 'BalY2gJaI8uA2SGVOZhqBQ3V0CYSNNGP',
    'answer': '0xax8ex0xax84x0xkx7qx0x18x76x0x1ix6sx0x26x68x0x2gx5kx0x34x50x',
    'respKey': '',
}


class CapyApiClient():
    """Mock client returning a realistic Capy answer (an object, not a token)."""

    def in_(self, files={}, **kwargs):
        self.incomings = kwargs
        self.incoming_files = files
        return 'OK|123'

    def res(self, **kwargs):
        if kwargs.get('json') in (1, '1'):
            return json.dumps({
                'status': 1,
                'request': SOLUTION,
                'solution': SOLUTION,
                'cost': '0.00299',
                'errorId': 0,
            })
        return 'OK|' + json.dumps(SOLUTION)


class CapyTest(AbstractTest):

    def setUp(self):
        super().setUp()
        self.solver.api_client = CapyApiClient()

    def solve(self, **kwargs):
        params = {'sitekey': CAPTCHA_KEY, 'url': URL}
        params.update(kwargs)
        return self.solver.capy(**params)

    def assert_sent(self, expected):
        expected.update({'key': 'API_KEY'})
        self.assertEqual(self.solver.api_client.incomings, expected)

    # -- what goes out ----------------------------------------------------

    def test_basic(self):
        result = self.solve()

        self.assert_sent({
            'method': 'capy',
            'captchakey': CAPTCHA_KEY,
            'pageurl': URL,
        })
        self.assertEqual(result['captchaId'], '123')

    def test_sitekey_is_sent_as_captchakey(self):
        """The SDK argument is `sitekey`, matching every other method; the wire
        name is `captchakey`, which is what the API documents."""
        self.solve()

        sent = self.solver.api_client.incomings
        self.assertEqual(sent['captchakey'], CAPTCHA_KEY)
        self.assertNotIn('sitekey', sent)

    def test_api_server_is_forwarded(self):
        self.solve(api_server='https://jp.api.capy.me/')

        self.assert_sent({
            'method': 'capy',
            'captchakey': CAPTCHA_KEY,
            'pageurl': URL,
            'api_server': 'https://jp.api.capy.me/',
        })

    def test_camelcase_api_server_alias(self):
        self.solve(apiServer='https://jp.api.capy.me/')

        self.assertEqual(
            self.solver.api_client.incomings['api_server'],
            'https://jp.api.capy.me/')

    def test_user_agent_is_lowercased_to_the_documented_spelling(self):
        """The server reads both, so the SDK settles on one rather than passing
        through whichever the caller happened to use."""
        self.solve(userAgent='Mozilla/5.0')

        sent = self.solver.api_client.incomings
        self.assertEqual(sent['useragent'], 'Mozilla/5.0')
        self.assertNotIn('userAgent', sent)

    def test_explicit_puzzle_version_is_allowed(self):
        self.solve(version='puzzle')

        self.assertEqual(self.solver.api_client.incomings['version'], 'puzzle')

    def test_unset_optional_is_not_sent(self):
        """`capy(key, url, api_server=None)` must behave as if it were omitted --
        a form body can only carry strings, so None would arrive as 'None'."""
        self.solve(api_server=None, version=None)

        self.assert_sent({
            'method': 'capy',
            'captchakey': CAPTCHA_KEY,
            'pageurl': URL,
        })

    def test_proxy(self):
        self.solve(proxy={'type': 'SOCKS5', 'uri': 'login:pass@1.2.3.4:8080'})

        self.assert_sent({
            'method': 'capy',
            'captchakey': CAPTCHA_KEY,
            'pageurl': URL,
            'proxy': 'login:pass@1.2.3.4:8080',
            'proxytype': 'SOCKS5',
        })

    # -- what is refused before it costs a round-trip ---------------------

    def test_avatar_version_is_refused_locally(self):
        """CapSkip solves the puzzle family only. Returning a puzzle answer for
        an avatar request would bill for a solve the target site rejects."""
        with self.assertRaises(ValidationException) as caught:
            self.solve(version='avatar')

        self.assertIn('puzzle', str(caught.exception))

    def test_unknown_version_is_refused(self):
        self.assertRaises(ValidationException, self.solve, version='slider')

    def test_missing_captchakey_is_refused(self):
        self.assertRaises(ValidationException, self.solver.capy, '', URL)

    def test_missing_pageurl_is_refused(self):
        self.assertRaises(ValidationException, self.solver.capy, CAPTCHA_KEY, '')

    def test_unknown_parameter_is_refused(self):
        self.assertRaises(ValidationException, self.solve, challenge='x')

    def test_socks4_is_refused(self):
        """CapSkip maps four proxy schemes and answers ERROR_BAD_PARAMETERS for
        SOCKS4, so the SDK refuses it locally with a clearer message."""
        self.assertRaises(
            ValidationException, self.solve,
            proxy={'type': 'SOCKS4', 'uri': '1.2.3.4:1080'})

    # -- what comes back --------------------------------------------------

    def test_result_is_expanded_into_the_three_form_fields(self):
        result = self.solve()

        self.assertEqual(result['captchakey'], SOLUTION['captchakey'])
        self.assertEqual(result['challengekey'], SOLUTION['challengekey'])
        self.assertEqual(result['answer'], SOLUTION['answer'])
        self.assertEqual(result['respKey'], '')

    def test_answer_is_not_reencoded(self):
        """The answer is the drag path the widget would have recorded, and the
        target site verifies it against the challenge it issued."""
        result = self.solve()

        self.assertEqual(result['answer'], SOLUTION['answer'])
        self.assertNotIn(' ', result['answer'])

    def test_raw_code_is_preserved(self):
        result = self.solve()

        self.assertIn('code', result)
        raw = result['code']
        parsed = raw if isinstance(raw, dict) else json.loads(raw)
        self.assertEqual(parsed, SOLUTION)

    def test_a_json_string_answer_is_expanded_too(self):
        """`capy()` polls with json=1, where the object arrives already parsed in
        `request`. A client reading res.php as plain text gets the same object as
        a single line of JSON after OK|, so the expansion has to read both."""
        result = _apply_capy_solution(
            {'captchaId': '123', 'code': json.dumps(SOLUTION)})

        self.assertEqual(result['challengekey'], SOLUTION['challengekey'])
        self.assertEqual(result['answer'], SOLUTION['answer'])
        self.assertEqual(result['captchakey'], SOLUTION['captchakey'])

    def test_solution_object_is_not_leaked_to_the_caller(self):
        result = self.solve()

        self.assertNotIn('solution', result)

    def test_unparseable_answer_is_left_untouched(self):
        """A reply the SDK cannot read must reach the caller as the server sent
        it, rather than being masked by a parse failure."""
        class Odd(CapyApiClient):
            def res(self, **kwargs):
                return json.dumps({'status': 1, 'request': 'not-json-at-all'})

        self.solver.api_client = Odd()
        result = self.solve()

        self.assertEqual(result['code'], 'not-json-at-all')
        self.assertNotIn('answer', result)


if __name__ == '__main__':
    unittest.main()
