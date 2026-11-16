import json

import pytest

try:
    from .abstract_async import make_solver
except ImportError:
    from abstract_async import make_solver

from capskip.exceptions import ValidationException

URL = 'https://smartcaptcha.yandexcloud.net/demo'
SITEKEY = 'ysc1_DAo8nFPdNCMHkAwYxIUJFxW5IIJd99BBfeeeee'
TOKEN = ('dD0xNzk0NDE5NTg3O2k9MjAzLjAuMTEzLjI1O0Q9QjQ1RjJBN0MxRTkwRDM2ODU0QzA1M0M3QTFF'
         'MkIzQzRENUU2RjcwODE5MkEzQjRDNUQ2RTdGODA5MUEyQjNDNEQ1RTZGNzA4MTt1PTE3OTQ0MTk1'
         'ODcxMjM0NTY3ODk7aD01ZjBjMmE5ZTYxZDg0YjM3YTBjMWU5YjJkNmY0YTg3Mw==')


class AsyncYandexApiClient():
    """Mock async client answering as CapSkip's res.php does for SmartCaptcha."""

    async def in_(self, files={}, **kwargs):
        self.incomings = kwargs
        self.incoming_files = files
        return 'OK|123'

    async def res(self, **kwargs):
        if kwargs.get('json') in (1, '1'):
            return json.dumps({'status': 1, 'request': TOKEN})
        return 'OK|' + TOKEN


def make_yandex_solver():
    solver = make_solver()
    solver.api_client = AsyncYandexApiClient()
    return solver


@pytest.mark.asyncio
async def test_basic():
    solver = make_yandex_solver()

    result = await solver.yandex_smart(SITEKEY, URL)

    assert solver.api_client.incomings == {
        'method': 'yandex', 'sitekey': SITEKEY, 'pageurl': URL, 'key': 'API_KEY',
    }
    assert result['captchaId'] == '123'
    assert result['code'] == TOKEN
    assert result['token'] == TOKEN


@pytest.mark.asyncio
async def test_every_option():
    solver = make_yandex_solver()

    await solver.yandex_smart(SITEKEY, URL, userAgent='UA',
                              proxy={'type': 'HTTP', 'uri': '203.0.113.7:3128'})

    assert solver.api_client.incomings == {
        'method': 'yandex', 'sitekey': SITEKEY, 'pageurl': URL, 'useragent': 'UA',
        'proxy': '203.0.113.7:3128', 'proxytype': 'HTTP', 'key': 'API_KEY',
    }


@pytest.mark.asyncio
async def test_recaptcha_timeout_is_used():
    solver = make_yandex_solver()
    seen = {}
    original = solver.wait_result

    async def wait_result(id_, timeout, polling_interval, json=0):
        seen['timeout'] = timeout
        return await original(id_, timeout, polling_interval, json=json)

    solver.wait_result = wait_result
    await solver.yandex_smart(SITEKEY, URL)

    assert seen['timeout'] == solver.recaptcha_timeout


@pytest.mark.asyncio
@pytest.mark.parametrize('sitekey,url', [
    ('', URL),
    ('too-short', URL),
    (SITEKEY, ''),
    (SITEKEY, 'example.com/login'),
])
async def test_refused_locally(sitekey, url):
    solver = make_yandex_solver()

    with pytest.raises(ValidationException):
        await solver.yandex_smart(sitekey, url)
    assert not hasattr(solver.api_client, 'incomings')
