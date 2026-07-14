import unittest

try:
    from .abstract import AbstractTest
except ImportError:
    from abstract import AbstractTest


class RecaptchaTest(AbstractTest):

    def test_v2(self):
        params = {
            'sitekey': '6Le-wvkSVVABCPBMRTvw0Q4Muexq1bi0DJwx_mJ-',
            'url': 'https://mysite.com/page/with/recaptcha',
            'invisible': 1,
            'datas': 'Crb7VsRAQaBqoaQQtHQQ',
        }

        sends = {
            'method': 'userrecaptcha',
            'googlekey': '6Le-wvkSVVABCPBMRTvw0Q4Muexq1bi0DJwx_mJ-',
            'pageurl': 'https://mysite.com/page/with/recaptcha',
            'invisible': 1,
            'enterprise': 0,
            'data-s': 'Crb7VsRAQaBqoaQQtHQQ',
        }

        return self.send_return(sends, self.solver.recaptcha, **params)

    def test_v2_rejects_v3_action(self):
        with self.assertRaises(self.solver.exceptions):
            self.solver.recaptcha(
                sitekey='6Le-wvkS...',
                url='https://example.com',
                action='verify',
            )

    def test_v2_enterprise(self):
        params = {
            'sitekey': '6Le-wvkSVVABCPBMRTvw0Q4Muexq1bi0DJwx_mJ-',
            'url': 'https://mysite.com/page/with/recaptcha',
            'enterprise': 1,
        }

        sends = {
            'method': 'userrecaptcha',
            'googlekey': '6Le-wvkSVVABCPBMRTvw0Q4Muexq1bi0DJwx_mJ-',
            'pageurl': 'https://mysite.com/page/with/recaptcha',
            'enterprise': 1,
        }

        return self.send_return(sends, self.solver.recaptcha, **params)

    def test_v3(self):
        params = {
            'sitekey': '6Le-wvkSVVABCPBMRTvw0Q4Muexq1bi0DJwx_mJ-',
            'url': 'https://mysite.com/page/with/recaptcha',
            'action': 'verify',
            'version': 'v3',
            'score': 0.7,
        }

        sends = {
            'method': 'userrecaptcha',
            'googlekey': '6Le-wvkSVVABCPBMRTvw0Q4Muexq1bi0DJwx_mJ-',
            'pageurl': 'https://mysite.com/page/with/recaptcha',
            'enterprise': 0,
            'action': 'verify',
            'version': 'v3',
            'min_score': 0.7,
        }

        return self.send_return(sends, self.solver.recaptcha, **params)

    def test_proxy(self):
        params = {
            'sitekey': '6Le-wvkSVVABCPBMRTvw0Q4Muexq1bi0DJwx_mJ-',
            'url': 'https://mysite.com/page/with/recaptcha',
            'proxy': {'type': 'HTTPS', 'uri': 'login:password@1.2.3.4:3128'},
        }

        sends = {
            'method': 'userrecaptcha',
            'googlekey': '6Le-wvkSVVABCPBMRTvw0Q4Muexq1bi0DJwx_mJ-',
            'pageurl': 'https://mysite.com/page/with/recaptcha',
            'enterprise': 0,
            'proxy': 'login:password@1.2.3.4:3128',
            'proxytype': 'HTTPS',
        }

        return self.send_return(sends, self.solver.recaptcha, **params)


if __name__ == '__main__':
    unittest.main()
