import json

import pytest

try:
    from .abstract_async import make_solver
except ImportError:
    from abstract_async import make_solver

from capskip.exceptions import ValidationException

PAGE_URL = 'https://www.example.com/'
CAPTCHA_URL = (
    'https://geo.captcha-delivery.com/captcha/?initialCid=AHrlqAAAAAMA7KBvCr0n4cEAG330MA%3D%3D'
    '&hash=D013AA612AB2224D03B2318D0F5B19&cid=KzE6_pZBBTHdCdvZkauT9VAshi0wS7~v5_M_MacEtdw8'
    '&t=fe&referer=https%3A%2F%2Fwww.example.com%2F&s=45225&dm=cd'
)
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36'
)
COOKIE = 'datadome=Zm9vYmFyEXAMPLEcookie~value; Max-Age=31536000; Domain=.example.com; Path=/; Secure; SameSite=Lax'
LIST_PROXY = '203.0.113.10:8080'


class AsyncDataDomeApiClient():
    """Mock async client answering as CapSkip does for a DataDome task."""

    async def in_(self, files={}, **kwargs):
        self.incomings = kwargs
        self.incoming_files = files
        return 'OK|123'

    async def res(self, **kwargs):
        if kwargs.get('json') in (1, '1'):
            return json.dumps({'status': 1, 'request': COOKIE,
                               'userAgent': USER_AGENT, 'proxy': LIST_PROXY})
        return 'OK|' + COOKIE


def make_datadome_solver():
    solver = make_solver()
    solver.api_client = AsyncDataDomeApiClient()
    return solver


@pytest.mark.asyncio
async def test_solve():
    solver = make_datadome_solver()

    result = await solver.datadome(CAPTCHA_URL, PAGE_URL, USER_AGENT)

    assert solver.api_client.incomings == {
        'key': 'API_KEY',
        'method': 'datadome',
        'captcha_url': CAPTCHA_URL,
        'pageurl': PAGE_URL,
        'useragent': USER_AGENT,
    }
    assert result['captchaId'] == '123'
    assert result['code'] == COOKIE
    assert result['cookie'] == 'datadome=Zm9vYmFyEXAMPLEcookie~value'
    assert result['userAgent'] == USER_AGENT
    assert result['proxy'] == LIST_PROXY


@pytest.mark.asyncio
async def test_proxy_dict():
    solver = make_datadome_solver()

    await solver.datadome(CAPTCHA_URL, url=PAGE_URL,
                          proxy={'type': 'SOCKS5', 'uri': 'user:pass@1.2.3.4:1080'})

    assert solver.api_client.incomings['pageurl'] == PAGE_URL
    assert solver.api_client.incomings['proxy'] == 'user:pass@1.2.3.4:1080'
    assert solver.api_client.incomings['proxytype'] == 'SOCKS5'


@pytest.mark.asyncio
async def test_banned_block_page_is_refused_locally():
    solver = make_datadome_solver()

    with pytest.raises(ValidationException):
        await solver.datadome(CAPTCHA_URL.replace('t=fe', 't=bv'), PAGE_URL)
    assert not hasattr(solver.api_client, 'incomings')


@pytest.mark.asyncio
async def test_non_windows_chrome_user_agent_is_refused_locally():
    solver = make_datadome_solver()

    with pytest.raises(ValidationException):
        await solver.datadome(CAPTCHA_URL, PAGE_URL,
                              'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                              '(KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36')
    assert not hasattr(solver.api_client, 'incomings')
