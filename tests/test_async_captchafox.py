import json

import pytest

try:
    from .abstract_async import make_solver
except ImportError:
    from abstract_async import make_solver

from capskip.exceptions import ValidationException

URL = 'https://mysite.com/page/with/captchafox'
SITEKEY = 'sk_xtNxpk6fCdFbxh1_xJeGflSdCE9tn99G'
TOKEN = '177f50c25b845601e5c779cdb51b040d523e8ab69efb4d5b343e28df07d05076'
BROWSER_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36')
CALLER_UA = 'Mozilla/5.0 (the caller\'s own UA)'


class AsyncCaptchaFoxApiClient():
    """Mock async client returning a realistic CaptchaFox answer."""

    def __init__(self, user_agent=BROWSER_UA):
        self.user_agent = user_agent

    async def in_(self, files={}, **kwargs):
        self.incomings = kwargs
        self.incoming_files = files
        return 'OK|123'

    async def res(self, **kwargs):
        if kwargs.get('json') in (1, '1'):
            payload = {'status': 1, 'request': TOKEN, 'solution': {'token': TOKEN}}
            if self.user_agent:
                payload['userAgent'] = self.user_agent
            return json.dumps(payload)
        return 'OK|' + TOKEN


def make_captchafox_solver(user_agent=BROWSER_UA):
    solver = make_solver()
    solver.api_client = AsyncCaptchaFoxApiClient(user_agent=user_agent)
    return solver


@pytest.mark.asyncio
async def test_basic():
    solver = make_captchafox_solver()

    result = await solver.captchafox(SITEKEY, URL)

    assert solver.api_client.incomings == {
        'key': 'API_KEY',
        'method': 'captchafox',
        'sitekey': SITEKEY,
        'pageurl': URL,
    }
    assert result['token'] == TOKEN
    assert result['code'] == TOKEN


@pytest.mark.asyncio
async def test_result_carries_the_user_agent_that_minted_the_token():
    solver = make_captchafox_solver()

    result = await solver.captchafox(SITEKEY, URL, useragent=CALLER_UA)

    assert result['userAgent'] == BROWSER_UA
    assert result['userAgent'] != CALLER_UA


@pytest.mark.asyncio
async def test_user_agent_is_absent_when_the_solve_reported_none():
    solver = make_captchafox_solver(user_agent=None)

    result = await solver.captchafox(SITEKEY, URL)

    assert 'userAgent' not in result


@pytest.mark.asyncio
async def test_mam_api_server_is_forwarded():
    solver = make_captchafox_solver()
    api_server = 'https://s.uicdn.com/mampkg/@mamdev/core.frontend.libs.captchafox/'

    await solver.captchafox(SITEKEY, URL, api_server=api_server)

    assert solver.api_client.incomings['api_server'] == api_server


@pytest.mark.asyncio
async def test_missing_sitekey_is_refused():
    solver = make_captchafox_solver()

    with pytest.raises(ValidationException):
        await solver.captchafox('', URL)


@pytest.mark.asyncio
async def test_socks4_is_refused():
    solver = make_captchafox_solver()

    with pytest.raises(ValidationException):
        await solver.captchafox(SITEKEY, URL,
                                proxy={'type': 'SOCKS4', 'uri': '1.2.3.4:1080'})
