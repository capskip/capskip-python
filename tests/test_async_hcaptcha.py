import json

import pytest

try:
    from .abstract_async import make_solver
except ImportError:
    from abstract_async import make_solver

from capskip.exceptions import ValidationException

URL = 'https://accounts.hcaptcha.com/demo'
SITEKEY = 'a5f74b19-9e45-40e0-b45d-47ff91b7a6c2'
TOKEN = 'P1_eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.hadwYXNza2V5xQZ2f3Kq8nV2'
RESP_KEY = 'E0_eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6IjA09wB1'
BROWSER_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36')


class AsyncHCaptchaApiClient():
    """Mock async client answering as CapSkip's res.php does for hCaptcha."""

    def __init__(self, resp_key=RESP_KEY):
        self.resp_key = resp_key

    async def in_(self, files={}, **kwargs):
        self.incomings = kwargs
        self.incoming_files = files
        return 'OK|123'

    async def res(self, **kwargs):
        if kwargs.get('json') in (1, '1'):
            return json.dumps({'status': 1, 'request': TOKEN,
                               'respKey': self.resp_key, 'useragent': BROWSER_UA})
        return 'OK|' + TOKEN


def make_hcaptcha_solver(resp_key=RESP_KEY):
    solver = make_solver()
    solver.api_client = AsyncHCaptchaApiClient(resp_key=resp_key)
    return solver


@pytest.mark.asyncio
async def test_basic():
    solver = make_hcaptcha_solver()

    result = await solver.hcaptcha(SITEKEY, URL)

    assert solver.api_client.incomings == {
        'key': 'API_KEY',
        'method': 'hcaptcha',
        'sitekey': SITEKEY,
        'pageurl': URL,
    }
    assert result['token'] == TOKEN
    assert result['code'] == TOKEN
    assert result['respKey'] == RESP_KEY
    assert result['userAgent'] == BROWSER_UA


@pytest.mark.asyncio
async def test_options_are_sent():
    solver = make_hcaptcha_solver()

    await solver.hcaptcha(SITEKEY, URL, invisible=True, data='rq',
                          userAgent='UA/1', proxy='1.2.3.4:8080')

    assert solver.api_client.incomings == {
        'key': 'API_KEY',
        'method': 'hcaptcha',
        'sitekey': SITEKEY,
        'pageurl': URL,
        'invisible': 1,
        'data': 'rq',
        'useragent': 'UA/1',
        'proxy': '1.2.3.4:8080',
        'proxytype': 'HTTP',
    }


@pytest.mark.asyncio
async def test_empty_resp_key():
    solver = make_hcaptcha_solver(resp_key='')

    result = await solver.hcaptcha(SITEKEY, URL)

    assert result['respKey'] == ''


@pytest.mark.asyncio
async def test_missing_sitekey_is_refused():
    solver = make_hcaptcha_solver()

    with pytest.raises(ValidationException):
        await solver.hcaptcha('', URL)


@pytest.mark.asyncio
async def test_bad_pageurl_is_refused():
    solver = make_hcaptcha_solver()

    with pytest.raises(ValidationException):
        await solver.hcaptcha(SITEKEY, 'not-a-url')


@pytest.mark.asyncio
async def test_unknown_parameter_is_refused():
    solver = make_hcaptcha_solver()

    with pytest.raises(ValidationException):
        await solver.hcaptcha(SITEKEY, URL, domain='js.hcaptcha.com')
