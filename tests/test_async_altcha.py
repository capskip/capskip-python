import base64
import json

import pytest

try:
    from .abstract_async import make_solver
except ImportError:
    from abstract_async import make_solver

from capskip.exceptions import ValidationException

URL = 'https://mysite.com/signup'
CHALLENGE_URL = 'https://mysite.com/captcha/api/altcha/challenge'
CHALLENGE_DOC = {
    'algorithm': 'SHA-256',
    'challenge': '3dd28253be6cc0c54d95f7f98c517e68',
    'salt': '46d5b1c8871e5152d902ee3f?expires=1893456000',
    'signature': '4b1cf0e0be0f4e5247e50b0f9a449830',
    'maxnumber': 1000000,
}
CHALLENGE_JSON = json.dumps(CHALLENGE_DOC)

SOLVED = dict(CHALLENGE_DOC, number=9661)
TOKEN = base64.b64encode(json.dumps(SOLVED).encode()).decode()


class AsyncAltchaApiClient():
    """Mock async client returning a realistic ALTCHA answer."""

    async def in_(self, files={}, **kwargs):
        self.incomings = kwargs
        self.incoming_files = files
        return 'OK|123'

    async def res(self, **kwargs):
        if kwargs.get('json') in (1, '1'):
            return json.dumps({
                'status': 1,
                'request': TOKEN,
                'solution': {'token': TOKEN, 'number': 9661},
            })
        return 'OK|' + TOKEN


def make_altcha_solver():
    solver = make_solver()
    solver.api_client = AsyncAltchaApiClient()
    return solver


@pytest.mark.asyncio
async def test_basic():
    solver = make_altcha_solver()

    result = await solver.altcha(url=URL, challenge_url=CHALLENGE_URL)

    assert solver.api_client.incomings == {
        'key': 'API_KEY',
        'method': 'altcha',
        'pageurl': URL,
        'challenge_url': CHALLENGE_URL,
    }
    assert result['captchaId'] == '123'


@pytest.mark.asyncio
async def test_challenge_json_accepts_a_dict():
    solver = make_altcha_solver()

    await solver.altcha(url=URL, challenge_json=CHALLENGE_DOC)

    sent = solver.api_client.incomings['challenge_json']
    assert json.loads(sent) == CHALLENGE_DOC


@pytest.mark.asyncio
async def test_expands_token_and_number():
    solver = make_altcha_solver()

    result = await solver.altcha(url=URL, challenge_url=CHALLENGE_URL)

    assert result['code'] == TOKEN
    assert result['token'] == TOKEN
    assert result['number'] == 9661


@pytest.mark.asyncio
async def test_proxy():
    solver = make_altcha_solver()

    await solver.altcha(
        url=URL,
        challenge_url=CHALLENGE_URL,
        proxy={'type': 'SOCKS5', 'uri': 'user:pass@1.2.3.4:1080'},
    )

    assert solver.api_client.incomings['proxy'] == 'user:pass@1.2.3.4:1080'
    assert solver.api_client.incomings['proxytype'] == 'SOCKS5'


@pytest.mark.asyncio
async def test_missing_both_challenge_params_raises():
    solver = make_altcha_solver()

    with pytest.raises(ValidationException):
        await solver.altcha(url=URL)


@pytest.mark.asyncio
async def test_missing_url_raises():
    solver = make_altcha_solver()

    with pytest.raises(ValidationException):
        await solver.altcha(url='', challenge_url=CHALLENGE_URL)


@pytest.mark.asyncio
async def test_unsupported_parameter_raises():
    solver = make_altcha_solver()

    with pytest.raises(ValidationException):
        await solver.altcha(
            url=URL, challenge_url=CHALLENGE_URL, sitekey='not-an-altcha-param'
        )


@pytest.mark.asyncio
async def test_socks4_is_rejected():
    solver = make_altcha_solver()

    with pytest.raises(ValidationException):
        await solver.altcha(
            url=URL,
            challenge_url=CHALLENGE_URL,
            proxy={'type': 'SOCKS4', 'uri': '1.2.3.4:3128'},
        )
