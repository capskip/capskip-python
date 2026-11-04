"""End-to-end tests driving the real HTTP layer against a local mock server."""

import base64
import tempfile

import pytest

from capskip import (
    CapSkip, AsyncCapSkip, ApiClient, AsyncApiClient,
    ApiException, NetworkException, TimeoutException, ValidationException,
)

try:
    from .conftest import (
        ALTCHA_NUMBER, ALTCHA_TOKEN, AMAZON_WAF_SOLUTION, CAPTCHAFOX_TOKEN, CAPTCHAFOX_USER_AGENT,
        CAPY_SOLUTION, CODE, FRIENDLY_CAPTCHA_TOKEN, USER_AGENT, PNG,
        DATADOME_BROWSER_USER_AGENT, DATADOME_COOKIE, DATADOME_LIST_PROXY,
        HCAPTCHA_RESP_KEY, HCAPTCHA_TOKEN, HCAPTCHA_USER_AGENT,
    )
except ImportError:
    from conftest import (
        ALTCHA_NUMBER, ALTCHA_TOKEN, AMAZON_WAF_SOLUTION, CAPTCHAFOX_TOKEN, CAPTCHAFOX_USER_AGENT,
        CAPY_SOLUTION, CODE, FRIENDLY_CAPTCHA_TOKEN, USER_AGENT, PNG,
        DATADOME_BROWSER_USER_AGENT, DATADOME_COOKIE, DATADOME_LIST_PROXY,
        HCAPTCHA_RESP_KEY, HCAPTCHA_TOKEN, HCAPTCHA_USER_AGENT,
    )

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


def test_normal_json_submit(solver):
    # json=1 makes in.php return a JSON submit response; the SDK must parse it.
    assert solver.normal(B64, json=1)['code'] == CODE


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


CHALLENGE_URL = 'https://example.com/captcha/api/altcha/challenge'
CHALLENGE_DOC = {
    'algorithm': 'SHA-256',
    'challenge': '3dd28253be6cc0c54d95f7f98c517e68',
    'salt': '46d5b1c8871e5152d902ee3f?expires=1893456000',
    'signature': '4b1cf0e0be0f4e5247e50b0f9a449830',
    'maxnumber': 1000000,
}


def test_altcha_challenge_url(solver):
    r = solver.altcha(url=URL, challenge_url=CHALLENGE_URL)
    assert r['code'] == ALTCHA_TOKEN
    assert r['token'] == ALTCHA_TOKEN
    assert r['number'] == ALTCHA_NUMBER
    assert r['captchaId']


def test_altcha_challenge_json(solver):
    import json as _json
    r = solver.altcha(url=URL, challenge_json=_json.dumps(CHALLENGE_DOC))
    assert r['token'] == ALTCHA_TOKEN


def test_altcha_challenge_json_as_dict_survives_the_wire(solver):
    # A dict has to reach the server as JSON, not as Python's repr, or the
    # server answers ERROR_BAD_PARAMETERS.
    r = solver.altcha(url=URL, challenge_json=CHALLENGE_DOC)
    assert r['number'] == ALTCHA_NUMBER


def test_altcha_without_a_challenge_is_refused_locally(solver):
    with pytest.raises(ValidationException):
        solver.altcha(url=URL)


@pytest.mark.asyncio
async def test_async_altcha(async_solver):
    r = await async_solver.altcha(url=URL, challenge_url=CHALLENGE_URL)
    assert r['token'] == ALTCHA_TOKEN
    assert r['number'] == ALTCHA_NUMBER


# -- Capy -----------------------------------------------------------------

CAPY_KEY = 'PUZZLE_Abc1dEFghIJKLM2no34P56q7rStu8v'
FOX_SITEKEY = 'sk_xtNxpk6fCdFbxh1_xJeGflSdCE9tn99G'
FRIENDLY_SITEKEY = 'FCMGEMUD2M567T8G'


def test_capy(solver):
    r = solver.capy(CAPY_KEY, URL)
    assert r['captchakey'] == CAPY_SOLUTION['captchakey']
    assert r['challengekey'] == CAPY_SOLUTION['challengekey']
    assert r['answer'] == CAPY_SOLUTION['answer']
    assert r['captchaId']


def test_capy_answer_crosses_the_wire_unchanged(solver):
    # The answer is the drag path the widget would have recorded; the target
    # site verifies it against the challenge it issued, so any edit breaks it.
    r = solver.capy(CAPY_KEY, URL, api_server='https://jp.api.capy.me/')
    assert r['answer'] == CAPY_SOLUTION['answer']


def test_capy_avatar_is_refused_locally(solver):
    with pytest.raises(ValidationException):
        solver.capy(CAPY_KEY, URL, version='avatar')


@pytest.mark.asyncio
async def test_async_capy(async_solver):
    r = await async_solver.capy(CAPY_KEY, URL)
    assert r['answer'] == CAPY_SOLUTION['answer']
    assert r['challengekey'] == CAPY_SOLUTION['challengekey']


# -- CaptchaFox -----------------------------------------------------------

def test_captchafox(solver):
    r = solver.captchafox(FOX_SITEKEY, URL)
    assert r['code'] == CAPTCHAFOX_TOKEN
    assert r['token'] == CAPTCHAFOX_TOKEN
    assert r['captchaId']


def test_captchafox_reports_the_browsers_user_agent(solver):
    # Not the one sent: CapSkip solves in its own browser, and the token has to
    # be submitted under the UA that minted it.
    caller_ua = 'Mozilla/5.0 (the caller own UA)'
    r = solver.captchafox(FOX_SITEKEY, URL, useragent=caller_ua)
    assert r['userAgent'] == CAPTCHAFOX_USER_AGENT
    assert r['userAgent'] != caller_ua


def test_captchafox_without_a_sitekey_is_refused_locally(solver):
    with pytest.raises(ValidationException):
        solver.captchafox('', URL)


@pytest.mark.asyncio
async def test_async_captchafox(async_solver):
    r = await async_solver.captchafox(FOX_SITEKEY, URL)
    assert r['token'] == CAPTCHAFOX_TOKEN


# -- Friendly Captcha -----------------------------------------------------

def test_friendly_captcha(solver):
    r = solver.friendly_captcha(FRIENDLY_SITEKEY, URL, version='v1')
    assert r['code'] == FRIENDLY_CAPTCHA_TOKEN
    assert r['token'] == FRIENDLY_CAPTCHA_TOKEN
    assert r['captchaId']


def test_friendly_captcha_token_survives_the_wire_verbatim(solver):
    # The token carries base64 padding and slashes; form encoding must round-trip
    # them, or the target site rejects a token that looks fine.
    r = solver.friendly_captcha(FRIENDLY_SITEKEY, URL,
                                module_script='https://cdn.example.com/site.min.js')
    assert r['token'] == FRIENDLY_CAPTCHA_TOKEN
    assert '/' in r['token'] and '=' in r['token']


def test_friendly_captcha_bad_version_is_refused_locally(solver):
    with pytest.raises(ValidationException):
        solver.friendly_captcha(FRIENDLY_SITEKEY, URL, version='v3')


@pytest.mark.asyncio
async def test_async_friendly_captcha(async_solver):
    r = await async_solver.friendly_captcha(FRIENDLY_SITEKEY, URL, api_server='eu')
    assert r['token'] == FRIENDLY_CAPTCHA_TOKEN


# -- Amazon WAF -----------------------------------------------------------

WAF_KEY = 'AQIDAHjcYuEXAMPLEghicBgQ/7bFaQZ+m5FKCMDnO+vTbNg96AHDh0IR5vgzHNceHYqZR+GOAAAAfjB8'
WAF_IV = 'CgAFRDIjfgAAA5yY'
WAF_CONTEXT = 'Rbp3r8fvbuhmrCqpUe8Mh1TLvs8OSKJZiSs2vCF4dt9rxVZI7xYJa2n5k/9r+XaXe7KUIu2I8nXTDHHkDvIOTDc2'
WAF_CHALLENGE_JS = 'https://3f2a9c7d41b0.edge.sdk.awswaf.com/3f2a9c7d41b0/8e51d0c7a2f4/challenge.js'
WAF_JSAPI = 'https://5b7e0a19c3d8.us-east-1.captcha-sdk.awswaf.com/5b7e0a19c3d8/jsapi.js'


def test_amazon_waf_challenge_page(solver):
    r = solver.amazon_waf(WAF_KEY, WAF_IV, WAF_CONTEXT, URL,
                          challenge_script=WAF_CHALLENGE_JS)
    assert r['captcha_voucher'] == AMAZON_WAF_SOLUTION['captcha_voucher']
    assert r['existing_token'] == AMAZON_WAF_SOLUTION['existing_token']


def test_amazon_waf_widget_page(solver):
    r = solver.amazon_waf(sitekey=WAF_KEY + '_0_1', url=URL, jsapiScript=WAF_JSAPI)
    assert r['captcha_voucher'] == AMAZON_WAF_SOLUTION['captcha_voucher']
    assert r['existing_token'] == AMAZON_WAF_SOLUTION['existing_token']


def test_amazon_waf_keys_with_plus_slash_equals_cross_the_wire(solver):
    """The keys carry +, / and =, which a form body has to URL-encode; a key
    mangled on the way would be a different firewall configuration."""
    r = solver.amazon_waf(WAF_KEY + '==', WAF_IV, WAF_CONTEXT, URL)
    assert r['existing_token'] == AMAZON_WAF_SOLUTION['existing_token']


def test_amazon_waf_lone_iv_is_refused_locally(solver):
    with pytest.raises(ValidationException):
        solver.amazon_waf(WAF_KEY, WAF_IV, None, URL)


def test_amazon_waf_off_aws_script_is_refused_locally(solver):
    with pytest.raises(ValidationException):
        solver.amazon_waf(WAF_KEY, url=URL, jsapiScript='https://evil.example/jsapi.js')


@pytest.mark.asyncio
async def test_async_amazon_waf(async_solver):
    r = await async_solver.amazon_waf(WAF_KEY, WAF_IV, WAF_CONTEXT, URL)
    assert r['captcha_voucher'] == AMAZON_WAF_SOLUTION['captcha_voucher']
    assert r['existing_token'] == AMAZON_WAF_SOLUTION['existing_token']


# -- DataDome -------------------------------------------------------------

DD_PAGE = 'https://www.example.com/'
DD_CAPTCHA_URL = (
    'https://geo.captcha-delivery.com/captcha/?initialCid=AHrlqAAAAAMA7KBvCr0n4cEAG330MA%3D%3D'
    '&hash=D013AA612AB2224D03B2318D0F5B19&cid=KzE6_pZBBTHdCdvZkauT9VAshi0wS7~v5_M_MacEtdw8'
    '&t=fe&referer=https%3A%2F%2Fwww.example.com%2F&s=45225&e=549255a0289eaf17af60822309ab8db4&dm=cd'
)
DD_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/156.0.0.1 Safari/537.36'
)


def test_datadome_without_proxy_reports_the_list_proxy(solver):
    """No proxy sent: CapSkip solved through its own DataDome list, so the
    result names that proxy and the browser's User-Agent."""
    r = solver.datadome(DD_CAPTCHA_URL, DD_PAGE)
    assert r['code'] == DATADOME_COOKIE
    assert r['cookie'] == DATADOME_COOKIE.split(';')[0]
    assert r['userAgent'] == DATADOME_BROWSER_USER_AGENT
    assert r['proxy'] == DATADOME_LIST_PROXY


def test_datadome_with_own_proxy_and_user_agent(solver):
    """A proxy sent with the task: no `proxy` comes back, and the User-Agent is
    the one sent -- it crossed the wire intact, ~ ; ( ) and all."""
    r = solver.datadome(DD_CAPTCHA_URL, DD_PAGE, DD_USER_AGENT,
                        {'type': 'HTTP', 'uri': 'login:p%40ss@203.0.113.7:3128'})
    assert r['cookie'] == DATADOME_COOKIE.split(';')[0]
    assert r['userAgent'] == DD_USER_AGENT
    assert 'proxy' not in r


def test_datadome_banned_block_page_is_refused_locally(solver):
    with pytest.raises(ValidationException):
        solver.datadome(DD_CAPTCHA_URL.replace('t=fe', 't=bv'), DD_PAGE)


@pytest.mark.asyncio
async def test_async_datadome(async_solver):
    r = await async_solver.datadome(DD_CAPTCHA_URL, DD_PAGE)
    assert r['cookie'] == DATADOME_COOKIE.split(';')[0]
    assert r['userAgent'] == DATADOME_BROWSER_USER_AGENT
    assert r['proxy'] == DATADOME_LIST_PROXY


# -- hCaptcha -------------------------------------------------------------

HC_SITEKEY = 'a5f74b19-9e45-40e0-b45d-47ff91b7a6c2'
HC_PAGE = 'https://accounts.hcaptcha.com/demo'


def test_hcaptcha(solver):
    r = solver.hcaptcha(HC_SITEKEY, HC_PAGE)
    assert r['captchaId']
    assert r['code'] == HCAPTCHA_TOKEN
    assert r['token'] == HCAPTCHA_TOKEN
    assert r['respKey'] == HCAPTCHA_RESP_KEY
    assert r['userAgent'] == HCAPTCHA_USER_AGENT


def test_hcaptcha_with_every_option(solver):
    # invisible=True has to cross the wire as 1: the mock, like CapSkip,
    # refuses anything else. rqdata carries + and /, which must survive.
    r = solver.hcaptcha(HC_SITEKEY, HC_PAGE, invisible=True,
                        data='Wk2qT7bX+fV9rL0pZ3mN8cJ1hYsD6uE4gA5oR2iK/0=',
                        userAgent='Mozilla/5.0 (caller)',
                        proxy={'type': 'SOCKS5H', 'uri': 'login:p%40ss@203.0.113.7:1080'})
    assert r['token'] == HCAPTCHA_TOKEN
    assert r['respKey'] == HCAPTCHA_RESP_KEY


def test_hcaptcha_bad_pageurl_is_refused_locally(solver):
    with pytest.raises(ValidationException):
        solver.hcaptcha(HC_SITEKEY, 'accounts.hcaptcha.com/demo')


@pytest.mark.asyncio
async def test_async_hcaptcha(async_solver):
    r = await async_solver.hcaptcha(HC_SITEKEY, HC_PAGE, invisible=1)
    assert r['token'] == HCAPTCHA_TOKEN
    assert r['respKey'] == HCAPTCHA_RESP_KEY
    assert r['userAgent'] == HCAPTCHA_USER_AGENT
