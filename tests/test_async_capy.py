import json

import pytest

try:
    from .abstract_async import make_solver
except ImportError:
    from abstract_async import make_solver

from capskip.exceptions import ValidationException

URL = 'https://mysite.com/login'
CAPTCHA_KEY = 'PUZZLE_Abc1dEFghIJKLM2no34P56q7rStu8v'

SOLUTION = {
    'captchakey': CAPTCHA_KEY,
    'challengekey': 'BalY2gJaI8uA2SGVOZhqBQ3V0CYSNNGP',
    'answer': '0xax8ex0xax84x0xkx7qx0x18x76x0x1ix6sx0x26x68x0x2gx5kx0x34x50x',
    'respKey': '',
}


class AsyncCapyApiClient():
    """Mock async client returning a realistic Capy answer (an object, not a token)."""

    async def in_(self, files={}, **kwargs):
        self.incomings = kwargs
        self.incoming_files = files
        return 'OK|123'

    async def res(self, **kwargs):
        if kwargs.get('json') in (1, '1'):
            return json.dumps({
                'status': 1,
                'request': SOLUTION,
                'solution': SOLUTION,
            })
        return 'OK|' + json.dumps(SOLUTION)


def make_capy_solver():
    solver = make_solver()
    solver.api_client = AsyncCapyApiClient()
    return solver


@pytest.mark.asyncio
async def test_basic():
    solver = make_capy_solver()

    result = await solver.capy(CAPTCHA_KEY, URL)

    assert solver.api_client.incomings == {
        'key': 'API_KEY',
        'method': 'capy',
        'captchakey': CAPTCHA_KEY,
        'pageurl': URL,
    }
    assert result['captchaId'] == '123'


@pytest.mark.asyncio
async def test_result_is_expanded_into_the_three_form_fields():
    solver = make_capy_solver()

    result = await solver.capy(CAPTCHA_KEY, URL)

    assert result['captchakey'] == SOLUTION['captchakey']
    assert result['challengekey'] == SOLUTION['challengekey']
    assert result['answer'] == SOLUTION['answer']
    assert result['respKey'] == ''


@pytest.mark.asyncio
async def test_optional_parameters_are_forwarded():
    solver = make_capy_solver()

    await solver.capy(CAPTCHA_KEY, URL,
                      api_server='https://jp.api.capy.me/', version='puzzle')

    sent = solver.api_client.incomings
    assert sent['api_server'] == 'https://jp.api.capy.me/'
    assert sent['version'] == 'puzzle'


@pytest.mark.asyncio
async def test_avatar_version_is_refused_locally():
    solver = make_capy_solver()

    with pytest.raises(ValidationException, match='puzzle'):
        await solver.capy(CAPTCHA_KEY, URL, version='avatar')


@pytest.mark.asyncio
async def test_missing_captchakey_is_refused():
    solver = make_capy_solver()

    with pytest.raises(ValidationException):
        await solver.capy('', URL)


@pytest.mark.asyncio
async def test_socks4_is_refused():
    solver = make_capy_solver()

    with pytest.raises(ValidationException):
        await solver.capy(CAPTCHA_KEY, URL,
                          proxy={'type': 'SOCKS4', 'uri': '1.2.3.4:1080'})


@pytest.mark.asyncio
async def test_solution_object_is_not_leaked_to_the_caller():
    solver = make_capy_solver()

    result = await solver.capy(CAPTCHA_KEY, URL)

    assert 'solution' not in result
