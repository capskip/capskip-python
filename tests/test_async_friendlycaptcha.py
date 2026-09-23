import json

import pytest

try:
    from .abstract_async import make_solver
except ImportError:
    from abstract_async import make_solver

from capskip.exceptions import ValidationException

URL = 'https://mysite.com/signup'
SITEKEY = 'FCMGEMUD2M567T8G'
V1_TOKEN = ('c62c4da36bbaf7f253873035832709ef.aqwpWwdbzRWKY/UQAQwwpgAAAAAAAAAAM7hBvJOzqjc=.'
            'AAAAAArcCQABAAAAxv8QAAIAAACKYRgA.AgAB')
V2_MODULE_SCRIPT = 'https://cdn.example.com/@friendlycaptcha/sdk@0.1.6/site.min.js'


class AsyncFriendlyCaptchaApiClient():
    """Mock async client returning a realistic Friendly Captcha answer."""

    def __init__(self, token=V1_TOKEN):
        self.token = token

    async def in_(self, files={}, **kwargs):
        self.incomings = kwargs
        self.incoming_files = files
        return 'OK|123'

    async def res(self, **kwargs):
        if kwargs.get('json') in (1, '1'):
            return json.dumps({
                'status': 1,
                'request': self.token,
                'solution': {'token': self.token},
            })
        return 'OK|' + self.token


def make_friendly_solver(token=V1_TOKEN):
    solver = make_solver()
    solver.api_client = AsyncFriendlyCaptchaApiClient(token=token)
    return solver


@pytest.mark.asyncio
async def test_basic():
    solver = make_friendly_solver()

    result = await solver.friendly_captcha(SITEKEY, URL)

    assert solver.api_client.incomings == {
        'key': 'API_KEY',
        'method': 'friendly_captcha',
        'sitekey': SITEKEY,
        'pageurl': URL,
    }
    assert result['token'] == V1_TOKEN
    assert result['code'] == V1_TOKEN


@pytest.mark.asyncio
async def test_version_and_script_are_forwarded():
    solver = make_friendly_solver()

    await solver.friendly_captcha(SITEKEY, URL, version='v2',
                                  module_script=V2_MODULE_SCRIPT)

    sent = solver.api_client.incomings
    assert sent['version'] == 'v2'
    assert sent['module_script'] == V2_MODULE_SCRIPT


@pytest.mark.asyncio
async def test_eu_tenant_is_forwarded():
    solver = make_friendly_solver()

    await solver.friendly_captcha(SITEKEY, URL, api_server='eu')

    assert solver.api_client.incomings['api_server'] == 'eu'


@pytest.mark.asyncio
async def test_a_large_v2_token_survives_intact():
    v2_token = 'AQQA.' + ('a' * 6000)
    solver = make_friendly_solver(token=v2_token)

    result = await solver.friendly_captcha(SITEKEY, URL, version='v2')

    assert result['token'] == v2_token


@pytest.mark.asyncio
async def test_unknown_version_is_refused_locally():
    solver = make_friendly_solver()

    with pytest.raises(ValidationException, match='v1'):
        await solver.friendly_captcha(SITEKEY, URL, version='v3')


@pytest.mark.asyncio
async def test_missing_sitekey_is_refused():
    solver = make_friendly_solver()

    with pytest.raises(ValidationException):
        await solver.friendly_captcha('', URL)


@pytest.mark.asyncio
async def test_socks4_is_refused():
    solver = make_friendly_solver()

    with pytest.raises(ValidationException):
        await solver.friendly_captcha(SITEKEY, URL,
                                      proxy={'type': 'SOCKS4', 'uri': '1.2.3.4:1080'})
