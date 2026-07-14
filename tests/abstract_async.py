import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from capskip import AsyncCapSkip

captcha_id = '123'
code = 'abcd'


class AsyncApiClient():
    """Mock async API client recording sent params and returning canned responses."""

    async def in_(self, files={}, **kwargs):
        self.incomings = kwargs
        self.incoming_files = files

        return 'OK|' + captcha_id

    async def res(self, **kwargs):
        if kwargs.get('json') in (1, '1'):
            return (
                '{"status":1,"request":"' + code
                + '","useragent":"TestAgent/1.0"}'
            )
        return 'OK|' + code


def make_solver():
    solver = AsyncCapSkip('API_KEY', pollingInterval=1)
    solver.api_client = AsyncApiClient()
    return solver


async def send_return(solver, for_send, method, **kwargs):
    file = kwargs.pop('file', {})

    result = await (method(file, **kwargs) if file else method(**kwargs))

    incomings = solver.api_client.incomings
    for_send.update({'key': 'API_KEY'})

    assert incomings == for_send
    assert isinstance(result, dict)
    assert result['captchaId'] == captcha_id
    assert result['code'] == code
