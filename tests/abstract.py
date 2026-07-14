import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from capskip import CapSkip

captcha_id = '123'
code = 'abcd'


class ApiClient():
    """Mock API client that records the params sent and returns canned responses."""

    def in_(self, files={}, **kwargs):
        self.incomings = kwargs
        self.incoming_files = files

        return 'OK|' + captcha_id

    def res(self, **kwargs):
        if kwargs.get('json') in (1, '1'):
            return (
                '{"status":1,"request":"' + code
                + '","useragent":"TestAgent/1.0"}'
            )
        return 'OK|' + code


class AbstractTest(unittest.TestCase):
    def setUp(self):
        self.solver = CapSkip('API_KEY', pollingInterval=1)
        self.solver.api_client = ApiClient()

    def send_return(self, for_send, method, **kwargs):
        file = kwargs.pop('file', {})
        file = kwargs.pop('files', file)

        result = method(file, **kwargs) if file else method(**kwargs)

        incomings = self.solver.api_client.incomings
        for_send.update({'key': 'API_KEY'})

        files = for_send.pop('files', {})
        self.assertEqual(incomings, for_send)

        incoming_files = self.solver.api_client.incoming_files
        incoming_files and self.assertEqual(incoming_files, files)

        self.assertIsInstance(result, dict)
        self.assertIn('captchaId', result)
        self.assertEqual(result['captchaId'], captcha_id)
        self.assertIn('code', result)
        self.assertEqual(result['code'], code)

    def invalid_file(self, method, **kwargs):
        self.assertRaises(self.solver.exceptions, method, 'lost_file.png',
                          **kwargs)


if __name__ == '__main__':
    unittest.main()
