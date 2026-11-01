import json
import unittest

try:
    from .abstract import AbstractTest
except ImportError:
    from abstract import AbstractTest

from capskip.exceptions import ValidationException
from capskip.solver import _apply_datadome_solution

PAGE_URL = 'https://www.example.com/'
CAPTCHA_URL = (
    'https://geo.captcha-delivery.com/captcha/?initialCid=AHrlqAAAAAMA7KBvCr0n4cEAG330MA%3D%3D'
    '&hash=D013AA612AB2224D03B2318D0F5B19&cid=KzE6_pZBBTHdCdvZkauT9VAshi0wS7~v5_M_MacEtdw8'
    '&t=fe&referer=https%3A%2F%2Fwww.example.com%2F&s=45225&e=549255a0289eaf17af60822309ab8db4&dm=cd'
)
INTERSTITIAL_URL = (
    'https://geo.captcha-delivery.com/interstitial/?initialCid=AHrlqAAAAAMA7KBvCr0n4cEAG330MA%3D%3D'
    '&hash=D013AA612AB2224D03B2318D0F5B19&cid=KzE6_pZBBTHdCdvZkauT9VAshi0wS7~v5_M_MacEtdw8'
    '&referer=https%3A%2F%2Fwww.example.com%2F&s=45225&b=1612345&dm=cd'
)
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36'
)

# What CapSkip hands back: the cookie exactly as DataDome set it, the
# User-Agent it was earned with, and the proxy its own list supplied.
COOKIE = (
    'datadome=FAPPpli4jkT1MZGtgF8ez7mjSz8MrJ9fGRNE51Gj79cq9fXp5xn~F1P5APWjqvJojf4U9dq0R81Xaj2hpYtjle95mkg; '
    'Max-Age=31536000; Domain=.example.com; Path=/; Secure; SameSite=Lax'
)
COOKIE_PAIR = 'datadome=FAPPpli4jkT1MZGtgF8ez7mjSz8MrJ9fGRNE51Gj79cq9fXp5xn~F1P5APWjqvJojf4U9dq0R81Xaj2hpYtjle95mkg'
LIST_PROXY = '203.0.113.10:8080'


class DataDomeApiClient():
    """Mock client answering as CapSkip does for a DataDome task."""

    def __init__(self, proxy=LIST_PROXY):
        self.proxy = proxy

    def in_(self, files={}, **kwargs):
        self.incomings = kwargs
        self.incoming_files = files
        return 'OK|123'

    def res(self, **kwargs):
        self.polled = kwargs
        if kwargs.get('json') in (1, '1'):
            reply = {'status': 1, 'request': COOKIE, 'userAgent': USER_AGENT}
            if self.proxy:
                reply['proxy'] = self.proxy
            return json.dumps(reply)
        return 'OK|' + COOKIE


class DataDomeTest(AbstractTest):

    def setUp(self):
        super().setUp()
        self.solver.api_client = DataDomeApiClient()

    def solve(self, **kwargs):
        params = {'captcha_url': CAPTCHA_URL, 'pageurl': PAGE_URL}
        params.update(kwargs)
        return self.solver.datadome(**params)

    def assert_sent(self, expected):
        expected.update({'key': 'API_KEY'})
        self.assertEqual(self.solver.api_client.incomings, expected)

    # -- what goes out ----------------------------------------------------

    def test_minimal_task(self):
        result = self.solve()

        self.assert_sent({
            'method': 'datadome',
            'captcha_url': CAPTCHA_URL,
            'pageurl': PAGE_URL,
        })
        self.assertEqual(result['captchaId'], '123')
        # Polled as JSON, so userAgent and proxy come back with the cookie.
        self.assertEqual(self.solver.api_client.polled.get('json'), 1)

    def test_positional_arguments_follow_2captcha(self):
        """`datadome(captcha_url, pageurl, userAgent, proxy)` is 2Captcha's
        order, so code written against it keeps working unchanged."""
        self.solver.datadome(CAPTCHA_URL, PAGE_URL, USER_AGENT,
                             {'type': 'HTTP', 'uri': 'login:password@1.2.3.4:8080'})

        self.assert_sent({
            'method': 'datadome',
            'captcha_url': CAPTCHA_URL,
            'pageurl': PAGE_URL,
            'useragent': USER_AGENT,
            'proxy': 'login:password@1.2.3.4:8080',
            'proxytype': 'HTTP',
        })

    def test_url_stands_in_for_pageurl(self):
        self.solver.datadome(CAPTCHA_URL, url=PAGE_URL)
        self.assertEqual(self.solver.api_client.incomings['pageurl'], PAGE_URL)

    def test_camel_case_captcha_url_is_accepted(self):
        self.solver.datadome(None, PAGE_URL, captchaUrl=CAPTCHA_URL)
        self.assertEqual(self.solver.api_client.incomings['captcha_url'], CAPTCHA_URL)

    def test_interstitial_device_check(self):
        self.solve(captcha_url=INTERSTITIAL_URL)
        self.assertEqual(self.solver.api_client.incomings['captcha_url'], INTERSTITIAL_URL)

    def test_html_escaped_iframe_src_is_accepted(self):
        """An iframe src copied out of the page source carries &amp;; the
        server decodes it, so it is not refused here either."""
        escaped = CAPTCHA_URL.replace('&', '&amp;')
        self.solve(captcha_url=escaped)
        self.assertEqual(self.solver.api_client.incomings['captcha_url'], escaped)

    def test_string_proxy_defaults_to_http(self):
        self.solve(proxy='1.2.3.4:8080')
        sent = self.solver.api_client.incomings
        self.assertEqual(sent['proxy'], '1.2.3.4:8080')
        self.assertEqual(sent['proxytype'], 'HTTP')

    def test_socks5h_proxy(self):
        self.solve(proxy={'type': 'SOCKS5H', 'uri': '1.2.3.4:1080'})
        self.assertEqual(self.solver.api_client.incomings['proxytype'], 'SOCKS5H')

    def test_uses_recaptcha_timeout_by_default(self):
        seen = {}
        original = self.solver.wait_result

        def spy(id_, timeout, polling_interval, json=0):
            seen['timeout'] = timeout
            return original(id_, timeout, polling_interval, json=json)

        self.solver.wait_result = spy
        self.solver.recaptcha_timeout = 321
        self.solve()
        self.assertEqual(seen['timeout'], 321)

    # -- what comes back --------------------------------------------------

    def test_result_carries_cookie_user_agent_and_list_proxy(self):
        result = self.solve()

        self.assertEqual(result['code'], COOKIE)
        self.assertEqual(result['cookie'], COOKIE_PAIR)
        self.assertEqual(result['userAgent'], USER_AGENT)
        self.assertEqual(result['proxy'], LIST_PROXY)

    def test_no_proxy_field_when_capskip_used_none(self):
        self.solver.api_client = DataDomeApiClient(proxy=None)
        result = self.solve()
        self.assertNotIn('proxy', result)
        self.assertEqual(result['cookie'], COOKIE_PAIR)

    def test_expansion_leaves_a_non_string_answer_alone(self):
        result = _apply_datadome_solution({'captchaId': '1', 'code': {'x': 1}})
        self.assertNotIn('cookie', result)
        self.assertEqual(result['code'], {'x': 1})

    def test_expansion_of_a_bare_cookie(self):
        result = _apply_datadome_solution({'captchaId': '1', 'code': 'datadome=abc'})
        self.assertEqual(result['cookie'], 'datadome=abc')

    # -- refused locally, as the server would refuse them -----------------

    def assert_refused(self, **kwargs):
        with self.assertRaises(ValidationException) as ctx:
            self.solve(**kwargs)
        self.assertFalse(hasattr(self.solver.api_client, 'incomings'))
        return str(ctx.exception)

    def test_missing_captcha_url(self):
        self.assert_refused(captcha_url=None)

    def test_missing_pageurl(self):
        self.assert_refused(pageurl=None)

    def test_captcha_url_off_datadome(self):
        self.assert_refused(captcha_url=CAPTCHA_URL.replace('captcha-delivery.com', 'evil.example'))

    def test_captcha_url_lookalike_host(self):
        self.assert_refused(captcha_url=CAPTCHA_URL.replace('geo.captcha-delivery.com', 'evilcaptcha-delivery.com'))

    def test_captcha_url_over_http(self):
        self.assert_refused(captcha_url=CAPTCHA_URL.replace('https://', 'http://'))

    def test_captcha_url_other_path(self):
        self.assert_refused(captcha_url=CAPTCHA_URL.replace('/captcha/', '/other/'))

    def test_captcha_url_without_challenge_ids(self):
        self.assert_refused(captcha_url='https://geo.captcha-delivery.com/captcha/?initialCid=A&hash=B')

    def test_banned_block_page(self):
        message = self.assert_refused(captcha_url=CAPTCHA_URL.replace('t=fe', 't=bv'))
        self.assertIn('t=bv', message)

    def test_pageurl_not_http(self):
        self.assert_refused(pageurl='ftp://www.example.com/')

    def test_pageurl_on_the_challenge_host(self):
        self.assert_refused(pageurl='https://geo.captcha-delivery.com/')

    def test_firefox_user_agent(self):
        self.assert_refused(userAgent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0')

    def test_mac_chrome_user_agent(self):
        self.assert_refused(userAgent=USER_AGENT.replace('Windows NT 10.0; Win64; x64', 'Macintosh; Intel Mac OS X 10_15_7'))

    def test_edge_user_agent(self):
        self.assert_refused(userAgent=USER_AGENT + ' Edg/156.0.0.0')

    def test_android_chrome_user_agent(self):
        self.assert_refused(userAgent='Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 '
                                      '(KHTML, like Gecko) Chrome/156.0.0.0 Mobile Safari/537.36')

    def test_socks4_proxy(self):
        self.assert_refused(proxy={'type': 'SOCKS4', 'uri': '1.2.3.4:1080'})

    def test_unknown_parameter(self):
        self.assert_refused(sitekey='nope')


if __name__ == '__main__':
    unittest.main()
