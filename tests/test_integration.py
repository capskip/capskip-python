"""End-to-end tests driving the real HTTP layer against a local mock server."""

import base64
import tempfile

import pytest

from capskip import (
    CapSkip, AsyncCapSkip, ApiClient, AsyncApiClient,
    ApiException, NetworkException, TimeoutException, ValidationException,
)

try:
    from .conftest import CODE, USER_AGENT, PNG
except ImportError:
    from conftest import CODE, USER_AGENT, PNG

SITEKEY = '6Le-wvkSVVABCPBMRTvw0Q4Muexq1bi0DJwx_mJ-'
TS_SITEKEY = '0x4AAAAAAABUYP0XeMJF0xoy'
URL = 'https://example.com'
B64 = base64.b64encode(PNG).decode()


@pytest.fixture
def solver(capskip_server):
    host, port = capskip_server
    return CapSkip(apiKey='capskip', host=host, port=port, pollingInterval=1)


@pytest.fixture
def async_solver(capskip_server):
    host, port = capskip_server
    return AsyncCapSkip(apiKey='capskip', host=host, port=port, pollingInterval=1)


@pytest.fixture
def image_file():
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as fh:
        fh.write(PNG)
        path = fh.name
    yield path
    import os
    os.unlink(path)


def test_normal_file(solver, image_file):
    r = solver.normal(image_file)
    assert r['code'] == CODE
    assert r['captchaId']


def test_normal_base64(solver):
    assert solver.normal(B64)['code'] == CODE


def test_normal_data_uri(solver):
    assert solver.normal('data:image/png;base64,' + B64)['code'] == CODE


def test_normal_url_download(solver, capskip_server):
    host, port = capskip_server
    assert solver.normal(f'http://{host}:{port}/image.png')['code'] == CODE


def test_recaptcha_v2(solver):
    assert solver.recaptcha(sitekey=SITEKEY, url=URL)['code'] == CODE


def test_recaptcha_v2_invisible(solver):
    assert solver.recaptcha(sitekey=SITEKEY, url=URL, invisible=1)['code'] == CODE


def test_recaptcha_v2_enterprise(solver):
    assert solver.recaptcha(sitekey=SITEKEY, url=URL, enterprise=1)['code'] == CODE


def test_recaptcha_v3(solver):
    r = solver.recaptcha(sitekey=SITEKEY, url=URL, version='v3', action='submit', score=0.7)
    assert r['code'] == CODE


def test_recaptcha_proxy(solver):
    r = solver.recaptcha(sitekey=SITEKEY, url=URL,
                         proxy={'type': 'HTTPS', 'uri': 'user:pass@1.2.3.4:3128'})
    assert r['code'] == CODE


def test_turnstile(solver):
    r = solver.turnstile(sitekey=TS_SITEKEY, url=URL)
    assert r['code'] == CODE
    assert r['userAgent'] == USER_AGENT


def test_turnstile_challenge_page(solver):
    r = solver.turnstile(sitekey=TS_SITEKEY, url=URL, action='managed',
                         data='cdata', pagedata='chlpd')
    assert r['code'] == CODE
    assert r['userAgent'] == USER_AGENT


def test_polling_retries_then_solves(solver):
    assert solver.recaptcha(sitekey=SITEKEY, url=URL + '/slow')['code'] == CODE


def test_polling_through_empty_responses(solver):
    # Regression: CapSkip returns an empty body before a result is ready; the
    # SDK must keep polling instead of raising "cannot recognize response".
    assert solver.recaptcha(sitekey=SITEKEY, url=URL + '/empty')['code'] == CODE


def test_manual_send_and_get_result(solver):
    cid = solver.send(method='userrecaptcha', googlekey=SITEKEY, pageurl=URL)
    assert cid
    assert solver.get_result(cid) == CODE


def test_timeout(capskip_server):
    host, port = capskip_server
    s = CapSkip(host=host, port=port, recaptchaTimeout=2, pollingInterval=1)
    with pytest.raises(TimeoutException):
        s.recaptcha(sitekey=SITEKEY, url=URL + '/never')


def test_bad_api_key(capskip_server):
    host, port = capskip_server
    s = CapSkip(apiKey='badkey', host=host, port=port)
    with pytest.raises(ApiException):
        s.recaptcha(sitekey=SITEKEY, url=URL)


def test_connection_refused():
    s = CapSkip(host='127.0.0.1', port=1, defaultTimeout=2, pollingInterval=1)
    with pytest.raises(NetworkException):
        s.send(method='userrecaptcha', googlekey=SITEKEY, pageurl=URL)


def test_low_level_api_client(capskip_server):
    host, port = capskip_server
    c = ApiClient(host=host, port=port)
    resp = c.in_(method='turnstile', key='capskip', sitekey=TS_SITEKEY, pageurl=URL)
    assert resp.startswith('OK|')
    assert CODE in c.res(key='capskip', action='get', id=resp[3:], json=1)


@pytest.mark.asyncio
async def test_async_normal_file(async_solver, image_file):
    assert (await async_solver.normal(image_file))['code'] == CODE


@pytest.mark.asyncio
async def test_async_normal_url(async_solver, capskip_server):
    host, port = capskip_server
    assert (await async_solver.normal(f'http://{host}:{port}/image.png'))['code'] == CODE


@pytest.mark.asyncio
async def test_async_recaptcha(async_solver):
    assert (await async_solver.recaptcha(sitekey=SITEKEY, url=URL))['code'] == CODE


@pytest.mark.asyncio
async def test_async_turnstile(async_solver):
    r = await async_solver.turnstile(sitekey=TS_SITEKEY, url=URL)
    assert r['code'] == CODE
    assert r['userAgent'] == USER_AGENT


@pytest.mark.asyncio
async def test_async_concurrent(async_solver):
    import asyncio
    results = await asyncio.gather(
        async_solver.recaptcha(sitekey=SITEKEY, url=URL),
        async_solver.turnstile(sitekey=TS_SITEKEY, url=URL),
    )
    assert all(r['code'] == CODE for r in results)


@pytest.mark.asyncio
async def test_async_polling_through_empty_responses(async_solver):
    assert (await async_solver.recaptcha(sitekey=SITEKEY, url=URL + '/empty'))['code'] == CODE


@pytest.mark.asyncio
async def test_async_timeout(capskip_server):
    host, port = capskip_server
    s = AsyncCapSkip(host=host, port=port, recaptchaTimeout=2, pollingInterval=1)
    with pytest.raises(TimeoutException):
        await s.recaptcha(sitekey=SITEKEY, url=URL + '/never')


@pytest.mark.asyncio
async def test_async_low_level_client(capskip_server):
    host, port = capskip_server
    c = AsyncApiClient(host=host, port=port)
    resp = await c.in_(method='turnstile', key='capskip', sitekey=TS_SITEKEY, pageurl=URL)
    assert resp.startswith('OK|')
