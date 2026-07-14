import unittest

try:
    from .abstract import AbstractTest, code
except ImportError:
    from abstract import AbstractTest, code


class TurnstileTest(AbstractTest):

    def test_basic(self):
        params = {
            'sitekey': '0x4AAAAAAABUYP0XeMJF0xoy',
            'url': 'https://mysite.com/page/with/turnstile',
        }

        sends = {
            'method': 'turnstile',
            'sitekey': '0x4AAAAAAABUYP0XeMJF0xoy',
            'pageurl': 'https://mysite.com/page/with/turnstile',
        }

        return self.send_return(sends, self.solver.turnstile, **params)

    def test_challenge_page(self):
        params = {
            'sitekey': '0x4AAAAAAABUYP0XeMJF0xoy',
            'url': 'https://mysite.com/page/with/turnstile',
            'action': 'managed',
            'data': 'cdata_value',
            'pagedata': 'chlpagedata_value',
        }

        sends = {
            'method': 'turnstile',
            'sitekey': '0x4AAAAAAABUYP0XeMJF0xoy',
            'pageurl': 'https://mysite.com/page/with/turnstile',
            'action': 'managed',
            'data': 'cdata_value',
            'pagedata': 'chlpagedata_value',
        }

        return self.send_return(sends, self.solver.turnstile, **params)

    def test_proxy(self):
        params = {
            'sitekey': '0x4AAAAAAABUYP0XeMJF0xoy',
            'url': 'https://mysite.com/page/with/turnstile',
            'proxy': {'type': 'HTTP', 'uri': '1.2.3.4:3128'},
        }

        sends = {
            'method': 'turnstile',
            'sitekey': '0x4AAAAAAABUYP0XeMJF0xoy',
            'pageurl': 'https://mysite.com/page/with/turnstile',
            'proxy': '1.2.3.4:3128',
            'proxytype': 'HTTP',
        }

        return self.send_return(sends, self.solver.turnstile, **params)

    def test_returns_user_agent(self):
        result = self.solver.turnstile(
            sitekey='0x4AAAAAAABUYP0XeMJF0xoy',
            url='https://mysite.com/page/with/turnstile',
        )
        self.assertEqual(result['code'], code)
        self.assertEqual(result['userAgent'], 'TestAgent/1.0')


if __name__ == '__main__':
    unittest.main()
