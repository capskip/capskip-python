import pytest

try:
    from .abstract_async import make_solver, send_return
except ImportError:
    from abstract_async import make_solver, send_return

SITEKEY = '0x4AAAAAAABUYP0XeMJF0xoy'
URL = 'https://mysite.com/page/with/turnstile'


@pytest.mark.asyncio
async def test_basic():
    solver = make_solver()

    params = {'sitekey': SITEKEY, 'url': URL}
    sends = {'method': 'turnstile', 'sitekey': SITEKEY, 'pageurl': URL}

    await send_return(solver, sends, solver.turnstile, **params)


@pytest.mark.asyncio
async def test_challenge_page():
    solver = make_solver()

    params = {
        'sitekey': SITEKEY,
        'url': URL,
        'action': 'managed',
        'data': 'cdata_value',
        'pagedata': 'chlpagedata_value',
    }
    sends = {
        'method': 'turnstile',
        'sitekey': SITEKEY,
        'pageurl': URL,
        'action': 'managed',
        'data': 'cdata_value',
        'pagedata': 'chlpagedata_value',
    }

    await send_return(solver, sends, solver.turnstile, **params)


@pytest.mark.asyncio
async def test_proxy():
    solver = make_solver()

    params = {
        'sitekey': SITEKEY,
        'url': URL,
        'proxy': {'type': 'HTTP', 'uri': '1.2.3.4:3128'},
    }
    sends = {
        'method': 'turnstile',
        'sitekey': SITEKEY,
        'pageurl': URL,
        'proxy': '1.2.3.4:3128',
        'proxytype': 'HTTP',
    }

    await send_return(solver, sends, solver.turnstile, **params)
