import json
import unittest

try:
    from .abstract import AbstractTest
except ImportError:
    from abstract import AbstractTest

from capskip.exceptions import ValidationException

URL = 'https://gt4.geetest.com/'
CAPTCHA_ID = '54088bb07d2df3c46b79f80300b0abbe'
SOLUTION = {
    'captcha_id': CAPTCHA_ID,
    'lot_number': '7c1a4f0e9b2d48a6b3e5f7d9c1a3b5e7',
    'pass_token': '2f6c0e4a8b1d5f9e3c7a0b4d8e2f6a1c5b9d3e7f0a4c8b2e6d1f5a9c3e7b0d4f8',
    'gen_time': '1793001600',
    'captcha_output': 'V2xH3kQp-Rz9a_TM-rSt-9GZ_6s_5-dyAo3ZzQxZ3nhs8agozV1dXHM52rdKikcSbx6m9Z==',
}
CODE = json.dumps(SOLUTION, separators=(',', ':'))


class GeeTestV4ApiClient():
    """Mock client answering as CapSkip's res.php does for GeeTest v4: `request`
    is the five values as a JSON string, after OK| or inside the JSON envelope,
    where the server escapes the inner quotes as \\u0022."""

    def __init__(self, code=CODE, raw_json=None):
        self.code = code
        self.raw_json = raw_json

    def in_(self, files={}, **kwargs):
        self.incomings = kwargs
        self.incoming_files = files
        return 'OK|123'

    def res(self, **kwargs):
        if kwargs.get('json') in (1, '1'):
            if self.raw_json is not None:
                return self.raw_json
            return json.dumps({'status': 1, 'request': self.code}).replace('\\"', '\\u0022')
        return 'OK|' + self.code


class GeeTestV4Test(AbstractTest):

    def setUp(self):
        super().setUp()
        self.solver.api_client = GeeTestV4ApiClient()

    def solve(self, **kwargs):
        params = {'captcha_id': CAPTCHA_ID, 'url': URL}
        params.update(kwargs)
        return self.solver.geetest_v4(**params)

    def assert_sent(self, expected):
        expected.update({'key': 'API_KEY'})
        self.assertEqual(self.solver.api_client.incomings, expected)

    # -- what goes out ----------------------------------------------------

    def test_basic(self):
        result = self.solve()

        self.assert_sent({
            'method': 'geetest_v4',
            'captcha_id': CAPTCHA_ID,
            'pageurl': URL,
        })
        self.assertEqual(result['captchaId'], '123')

    def test_every_option(self):
        self.solve(risk_type='slide',
                   proxy={'type': 'HTTPS', 'uri': 'login:password@203.0.113.7:3128'})

        self.assert_sent({
            'method': 'geetest_v4',
            'captcha_id': CAPTCHA_ID,
            'pageurl': URL,
            'risk_type': 'slide',
            'proxy': 'login:password@203.0.113.7:3128',
            'proxytype': 'HTTPS',
        })

    def test_camel_case_aliases(self):
        """The API documents riskType and also reads captchaId; both are accepted."""
        self.solver.geetest_v4(captcha_id=None, url=URL, captchaId=CAPTCHA_ID, riskType='icon')

        sent = self.solver.api_client.incomings
        self.assertEqual(sent['captcha_id'], CAPTCHA_ID)
        self.assertEqual(sent['risk_type'], 'icon')
        self.assertNotIn('captchaId', sent)
        self.assertNotIn('riskType', sent)

    def test_pageurl_keyword_is_accepted_for_url(self):
        self.solver.geetest_v4(captcha_id=CAPTCHA_ID, url=None, pageurl=URL)

        self.assertEqual(self.solver.api_client.incomings['pageurl'], URL)

    def test_captcha_id_is_trimmed(self):
        self.solve(captcha_id='  ' + CAPTCHA_ID + ' ')

        self.assertEqual(self.solver.api_client.incomings['captcha_id'], CAPTCHA_ID)

    def test_empty_optionals_are_not_sent(self):
        self.solve(risk_type='', proxy=None)

        self.assertNotIn('risk_type', self.solver.api_client.incomings)
        self.assertNotIn('proxy', self.solver.api_client.incomings)

    def test_string_proxy_defaults_to_http(self):
        self.solve(proxy='203.0.113.7:3128')

        self.assertEqual(self.solver.api_client.incomings['proxytype'], 'HTTP')

    # -- refused locally, as the server would refuse them -----------------

    def test_missing_captcha_id_is_refused(self):
        for value in ('', None, '   '):
            with self.assertRaises(ValidationException, msg=repr(value)):
                self.solve(captcha_id=value)

    def test_bad_pageurl_is_refused(self):
        for value in ('', 'gt4.geetest.com/', 'ftp://example.com/', 'https://'):
            with self.assertRaises(ValidationException, msg=value):
                self.solve(url=value)

    def test_v3_parameters_are_refused(self):
        for extra in ({'gt': 'abc'}, {'challenge': 'abc'}, {'api_server': 'api.geetest.com'}):
            with self.assertRaises(ValidationException, msg=extra):
                self.solve(**extra)

    def test_unknown_parameter_is_refused(self):
        with self.assertRaises(ValidationException):
            self.solve(userAgent='Mozilla/5.0')

    def test_conflicting_aliases_are_refused(self):
        with self.assertRaises(ValidationException):
            self.solve(captchaId='another-captcha-id')

    def test_socks4_is_refused(self):
        with self.assertRaises(ValidationException):
            self.solve(proxy={'type': 'SOCKS4', 'uri': '203.0.113.7:1080'})

    def test_nothing_is_sent_when_refused(self):
        with self.assertRaises(ValidationException):
            self.solve(captcha_id='')
        self.assertFalse(hasattr(self.solver.api_client, 'incomings'))

    # -- what comes back --------------------------------------------------

    def test_five_values_are_expanded(self):
        result = self.solve()

        self.assertEqual(result['code'], CODE)
        for field, value in SOLUTION.items():
            self.assertEqual(result[field], value)
        self.assertNotIn('isOffline', result)

    def test_plain_text_answer_is_expanded(self):
        result = self.solver.solve(method='geetest_v4', captcha_id=CAPTCHA_ID, url=URL)
        self.assertEqual(result['code'], CODE)

        from capskip.solver import _apply_geetest_v4_solution
        expanded = _apply_geetest_v4_solution(dict(result))
        self.assertEqual(expanded['pass_token'], SOLUTION['pass_token'])

    def test_offline_pass_is_reported(self):
        code = json.dumps({**SOLUTION, 'isOffline': True})
        self.solver.api_client = GeeTestV4ApiClient(code=code)

        result = self.solve()

        self.assertIs(result['isOffline'], True)
        self.assertEqual(result['lot_number'], SOLUTION['lot_number'])

    def test_object_request_is_expanded(self):
        """Should the server ever put the object itself in `request`, it still parses."""
        self.solver.api_client = GeeTestV4ApiClient(
            raw_json=json.dumps({'status': 1, 'request': SOLUTION}))

        result = self.solve()

        self.assertEqual(result['captcha_output'], SOLUTION['captcha_output'])

    def test_unparsable_answer_is_left_untouched(self):
        self.solver.api_client = GeeTestV4ApiClient(code='not-json')

        result = self.solve()

        self.assertEqual(result['code'], 'not-json')
        self.assertNotIn('lot_number', result)

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
        """A real browser solve, like GeeTest v3, so it takes the longer timeout."""
        seen = {}
        original = self.solver.wait_result

        def wait_result(id_, timeout, polling_interval, json=0):
            seen['timeout'] = timeout
            return original(id_, timeout, polling_interval, json=json)

        self.solver.wait_result = wait_result
        self.solve()

        self.assertEqual(seen['timeout'], self.solver.recaptcha_timeout)

    def test_explicit_timeout_wins(self):
        seen = {}
        original = self.solver.wait_result

        def wait_result(id_, timeout, polling_interval, json=0):
            seen['timeout'] = timeout
            return original(id_, timeout, polling_interval, json=json)

        self.solver.wait_result = wait_result
        self.solve(timeout=42)

        self.assertEqual(seen['timeout'], 42)


if __name__ == '__main__':
    unittest.main()
