import json

import pytest

try:
    from .abstract_async import make_solver
except ImportError:
    from abstract_async import make_solver

from capskip.exceptions import ValidationException

GT = '81388ea1fc187e0c335c0a8907ff2625'
CHALLENGE = '7cf6a8b1a2c34d5e6f7089abcdef0123'
URL = 'https://mysite.com/page/with/geetest'

SOLUTION = {
    'geetest_challenge': CHALLENGE,
    'geetest_validate': '9b1f4a2c8e7d6b5a4938271605f4e3d2',
    'geetest_seccode': '9b1f4a2c8e7d6b5a4938271605f4e3d2|jordan',
}


class AsyncGeeTestApiClient():
    """Mock async client returning a realistic GeeTest v3 answer."""

    async def in_(self, files={}, **kwargs):
        self.incomings = kwargs
        self.incoming_files = files
        return 'OK|123'

    async def res(self, **kwargs):
        payload = json.dumps(SOLUTION)
        if kwargs.get('json') in (1, '1'):
            return json.dumps({'status': 1, 'request': payload})
        return 'OK|' + payload


def make_geetest_solver():
    solver = make_solver()
    solver.api_client = AsyncGeeTestApiClient()
    return solver


@pytest.mark.asyncio
async def test_basic():
    solver = make_geetest_solver()

    result = await solver.geetest(gt=GT, challenge=CHALLENGE, url=URL)

    assert solver.api_client.incomings == {
        'key': 'API_KEY',
        'method': 'geetest',
        'gt': GT,
        'challenge': CHALLENGE,
        'pageurl': URL,
    }
    assert result['captchaId'] == '123'


@pytest.mark.asyncio
async def test_api_server():
    solver = make_geetest_solver()

    await solver.geetest(
        gt=GT, challenge=CHALLENGE, url=URL, api_server='api-na.geetest.com'
    )

    assert solver.api_client.incomings['api_server'] == 'api-na.geetest.com'


@pytest.mark.asyncio
async def test_proxy():
    solver = make_geetest_solver()

    await solver.geetest(
        gt=GT, challenge=CHALLENGE, url=URL,
        proxy={'type': 'HTTP', 'uri': '1.2.3.4:3128'},
    )

    assert solver.api_client.incomings['proxy'] == '1.2.3.4:3128'
    assert solver.api_client.incomings['proxytype'] == 'HTTP'


@pytest.mark.asyncio
async def test_expands_solution_fields():
    solver = make_geetest_solver()

    result = await solver.geetest(gt=GT, challenge=CHALLENGE, url=URL)

    assert json.loads(result['code']) == SOLUTION
    assert result['challenge'] == SOLUTION['geetest_challenge']
    assert result['validate'] == SOLUTION['geetest_validate']
    assert result['seccode'] == SOLUTION['geetest_seccode']


@pytest.mark.asyncio
async def test_missing_challenge_raises():
    solver = make_geetest_solver()

    with pytest.raises(ValidationException):
        await solver.geetest(gt=GT, challenge='', url=URL)


@pytest.mark.asyncio
async def test_unsupported_parameter_raises():
    solver = make_geetest_solver()

    with pytest.raises(ValidationException):
        await solver.geetest(
            gt=GT, challenge=CHALLENGE, url=URL, sitekey='not-a-geetest-param'
        )
