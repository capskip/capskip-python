import json

import pytest

try:
    from .abstract_async import make_solver
except ImportError:
    from abstract_async import make_solver

from capskip.exceptions import ValidationException

URL = 'https://2captcha.com/demo/mtcaptcha'
SITEKEY = 'MTPublic-KzqLY1cKH'
TOKEN = ('v1(0f3c9e2a,7b1d4c88,MTPublic-KzqLY1cKH,5e0c2a9f61d84b37a0c1e9b2d6f4a873,'
         'Qm9ndXNUb2tlbkZvclRlc3RzT25seV9fTm90QVJlYWxNVENhcHRjaGFUb2tlbi1BYkNkRWZHaA**)')


class AsyncMtCaptchaApiClient():
    """Mock async client answering as CapSkip's res.php does for MTCaptcha."""

    async def in_(self, files={}, **kwargs):
        self.incomings = kwargs
        self.incoming_files = files
        return 'OK|123'

    async def res(self, **kwargs):
        if kwargs.get('json') in (1, '1'):
            return json.dumps({'status': 1, 'request': TOKEN})
        return 'OK|' + TOKEN


def make_mtcaptcha_solver():
    solver = make_solver()
    solver.api_client = AsyncMtCaptchaApiClient()
    return solver


@pytest.mark.asyncio
async def test_basic():
    solver = make_mtcaptcha_solver()

    result = await solver.mtcaptcha(SITEKEY, URL)

    assert solver.api_client.incomings == {
        'method': 'mt_captcha', 'sitekey': SITEKEY, 'pageurl': URL, 'key': 'API_KEY',
    }
    assert result['captchaId'] == '123'
    assert result['code'] == TOKEN
    assert result['token'] == TOKEN


@pytest.mark.asyncio
async def test_every_option():
    solver = make_mtcaptcha_solver()

    await solver.mtcaptcha('sk=' + SITEKEY, URL, action='login', userAgent='UA',
                           proxy={'type': 'SOCKS5', 'uri': '203.0.113.7:1080'})

    assert solver.api_client.incomings == {
        'method': 'mt_captcha', 'sitekey': SITEKEY, 'pageurl': URL, 'action': 'login',
        'useragent': 'UA', 'proxy': '203.0.113.7:1080', 'proxytype': 'SOCKS5',
        'key': 'API_KEY',
    }


@pytest.mark.asyncio
@pytest.mark.parametrize('sitekey,url', [
    ('', URL),
    ('KzqLY1cKH', URL),
    (SITEKEY, ''),
    (SITEKEY, 'example.com/login'),
])
async def test_refused_locally(sitekey, url):
    solver = make_mtcaptcha_solver()

    with pytest.raises(ValidationException):
        await solver.mtcaptcha(sitekey, url)
    assert not hasattr(solver.api_client, 'incomings')
