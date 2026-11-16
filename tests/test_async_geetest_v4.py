import json

import pytest

try:
    from .abstract_async import make_solver
except ImportError:
    from abstract_async import make_solver

from capskip.exceptions import ValidationException

URL = 'https://gt4.geetest.com/'
CAPTCHA_ID = '54088bb07d2df3c46b79f80300b0abbe'
SOLUTION = {
    'captcha_id': CAPTCHA_ID,
    'lot_number': '7c1a4f0e9b2d48a6b3e5f7d9c1a3b5e7',
    'pass_token': '2f6c0e4a8b1d5f9e3c7a0b4d8e2f6a1c5b9d3e7f0a4c8b2e6d1f5a9c3e7b0d4f8',
    'gen_time': '1793001600',
    'captcha_output': 'V2xH3kQp-Rz9a_TM-rSt-9GZ_6s_5-dyAo3ZzQxZ3nhs8agozV1dXHM52rdKikcSbx6m9Z==',
}
CODE = json.dumps(SOLUTION, separators=(',', ':'))


class AsyncGeeTestV4ApiClient():
    """Mock async client answering as CapSkip's res.php does for GeeTest v4."""

    async def in_(self, files={}, **kwargs):
        self.incomings = kwargs
        self.incoming_files = files
        return 'OK|123'

    async def res(self, **kwargs):
        if kwargs.get('json') in (1, '1'):
            return json.dumps({'status': 1, 'request': CODE}).replace('\\"', '\\u0022')
        return 'OK|' + CODE


def make_geetest_v4_solver():
    solver = make_solver()
    solver.api_client = AsyncGeeTestV4ApiClient()
    return solver


@pytest.mark.asyncio
async def test_basic():
    solver = make_geetest_v4_solver()

    result = await solver.geetest_v4(CAPTCHA_ID, URL)

    assert solver.api_client.incomings == {
        'method': 'geetest_v4', 'captcha_id': CAPTCHA_ID, 'pageurl': URL, 'key': 'API_KEY',
    }
    assert result['captchaId'] == '123'
    assert result['code'] == CODE
    for field, value in SOLUTION.items():
        assert result[field] == value


@pytest.mark.asyncio
async def test_every_option():
    solver = make_geetest_v4_solver()

    await solver.geetest_v4(CAPTCHA_ID, URL, riskType='nine',
                            proxy={'type': 'SOCKS5H', 'uri': '203.0.113.7:1080'})

    assert solver.api_client.incomings == {
        'method': 'geetest_v4', 'captcha_id': CAPTCHA_ID, 'pageurl': URL,
        'risk_type': 'nine', 'proxy': '203.0.113.7:1080', 'proxytype': 'SOCKS5H',
        'key': 'API_KEY',
    }


@pytest.mark.asyncio
async def test_recaptcha_timeout_is_used():
    solver = make_geetest_v4_solver()
    seen = {}
    original = solver.wait_result

    async def wait_result(id_, timeout, polling_interval, json=0):
        seen['timeout'] = timeout
        return await original(id_, timeout, polling_interval, json=json)

    solver.wait_result = wait_result
    await solver.geetest_v4(CAPTCHA_ID, URL)

    assert seen['timeout'] == solver.recaptcha_timeout


@pytest.mark.asyncio
@pytest.mark.parametrize('captcha_id,url,extra', [
    ('', URL, {}),
    (CAPTCHA_ID, '', {}),
    (CAPTCHA_ID, 'gt4.geetest.com/', {}),
    (CAPTCHA_ID, URL, {'gt': '81388ea1fc187e0c335c0a8907ff2625'}),
    (CAPTCHA_ID, URL, {'proxy': {'type': 'SOCKS4', 'uri': '203.0.113.7:1080'}}),
])
async def test_refused_locally(captcha_id, url, extra):
    solver = make_geetest_v4_solver()

    with pytest.raises(ValidationException):
        await solver.geetest_v4(captcha_id, url, **extra)
    assert not hasattr(solver.api_client, 'incomings')
