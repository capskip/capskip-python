import pytest

try:
    from .abstract_async import make_solver, send_return
except ImportError:
    from abstract_async import make_solver, send_return

SITEKEY = '6Le-wvkSVVABCPBMRTvw0Q4Muexq1bi0DJwx_mJ-'
URL = 'https://mysite.com/page/with/recaptcha'


@pytest.mark.asyncio
async def test_v2():
    solver = make_solver()

    params = {
        'sitekey': SITEKEY,
        'url': URL,
        'invisible': 1,
        'datas': 'Crb7VsRAQaBqoaQQtHQQ',
    }
    sends = {
        'method': 'userrecaptcha',
        'googlekey': SITEKEY,
        'pageurl': URL,
        'invisible': 1,
        'enterprise': 0,
        'data-s': 'Crb7VsRAQaBqoaQQtHQQ',
    }

    await send_return(solver, sends, solver.recaptcha, **params)


@pytest.mark.asyncio
async def test_v3():
    solver = make_solver()

    params = {
        'sitekey': SITEKEY,
        'url': URL,
        'action': 'verify',
        'version': 'v3',
        'score': 0.7,
    }
    sends = {
        'method': 'userrecaptcha',
        'googlekey': SITEKEY,
        'pageurl': URL,
        'enterprise': 0,
        'action': 'verify',
        'version': 'v3',
        'min_score': 0.7,
    }

    await send_return(solver, sends, solver.recaptcha, **params)


@pytest.mark.asyncio
async def test_proxy():
    solver = make_solver()

    params = {
        'sitekey': SITEKEY,
        'url': URL,
        'proxy': {'type': 'HTTPS', 'uri': 'login:password@1.2.3.4:3128'},
    }
    sends = {
        'method': 'userrecaptcha',
        'googlekey': SITEKEY,
        'pageurl': URL,
        'enterprise': 0,
        'proxy': 'login:password@1.2.3.4:3128',
        'proxytype': 'HTTPS',
    }

    await send_return(solver, sends, solver.recaptcha, **params)
