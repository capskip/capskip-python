import unittest

try:
    from .abstract import AbstractTest
except ImportError:
    from abstract import AbstractTest


class NormalTest(AbstractTest):

    def test_base64(self):
        body = 'A' * 60

        params = {
            'file': body,
        }

        sends = {
            'method': 'base64',
            'body': body,
        }

        return self.send_return(sends, self.solver.normal, **params)

    def test_data_uri(self):
        body = 'A' * 60

        params = {
            'file': 'data:image/png;base64,' + body,
        }

        sends = {
            'method': 'base64',
            'body': body,
        }

        return self.send_return(sends, self.solver.normal, **params)

    def test_invalid_file(self):
        return self.invalid_file(self.solver.normal)

    def test_rejects_unsupported_params(self):
        with self.assertRaises(self.solver.exceptions):
            self.solver.normal('A' * 60, numeric=1)

    def test_rejects_proxy(self):
        with self.assertRaises(self.solver.exceptions):
            self.solver.normal(
                'A' * 60,
                proxy={'type': 'HTTP', 'uri': '1.2.3.4:3128'},
            )


if __name__ == '__main__':
    unittest.main()
