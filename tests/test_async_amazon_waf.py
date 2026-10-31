import json

import pytest

try:
    from .abstract_async import make_solver
except ImportError:
    from abstract_async import make_solver

from capskip.exceptions import ValidationException

URL = 'https://www.example.com/'
SITEKEY = 'AQIDAHjcYuEXAMPLEghicBgQ/7bFaQZ+m5FKCMDnO+vTbNg96AHDh0IR5vgzHNceHYqZR+GOAAAAfjB8'
IV = 'CgAFRDIjfgAAA5yY'
CONTEXT = 'Rbp3r8fvbuhmrCqpUe8Mh1TLvs8OSKJZiSs2vCF4dt9rxVZI7xYJa2n5k/9r+XaXe7KUIu2I8nXTDHHkDvIOTDc2'
WIDGET_KEY = 'Xr9kEXAMPLE2bWQx1vTq8LmZ0aYc4dHs7nFp3gJt6uKw5eRi9AbCdEfGh=_0_1'
JSAPI_JS = 'https://5b7e0a19c3d8.us-east-1.captcha-sdk.awswaf.com/5b7e0a19c3d8/jsapi.js'

SOLUTION = {
    'captcha_voucher': 'eyJ2b3VjaGVyIjoiRVhBTVBMRSJ9.9QwZcEXAMPLEvoucherJk4LmN0pQ',
    'existing_token': '7d4c2a91-EXAMPLE-4f0b-9e6d-3a1b5c8e2f70:EQoAeXAMPLEtokenAAAA:Wm9wc2E=',
}


class AsyncAmazonWafApiClient():
    """Mock async client returning a realistic AWS WAF answer (an object)."""

    async def in_(self, files={}, **kwargs):
        self.incomings = kwargs
        self.incoming_files = files
        return 'OK|123'

    async def res(self, **kwargs):
        if kwargs.get('json') in (1, '1'):
            return json.dumps({'status': 1, 'request': SOLUTION})
        return 'OK|' + json.dumps(SOLUTION)


def make_waf_solver():
    solver = make_solver()
    solver.api_client = AsyncAmazonWafApiClient()
    return solver


@pytest.mark.asyncio
async def test_challenge_page():
    solver = make_waf_solver()

    result = await solver.amazon_waf(SITEKEY, IV, CONTEXT, URL)

    assert solver.api_client.incomings == {
        'key': 'API_KEY',
        'method': 'amazon_waf',
        'sitekey': SITEKEY,
        'iv': IV,
        'context': CONTEXT,
        'pageurl': URL,
    }
    assert result['captchaId'] == '123'
    assert result['captcha_voucher'] == SOLUTION['captcha_voucher']
    assert result['existing_token'] == SOLUTION['existing_token']


@pytest.mark.asyncio
async def test_widget_page():
    solver = make_waf_solver()

    await solver.amazon_waf(WIDGET_KEY, url=URL, jsapiScript=JSAPI_JS)

    assert solver.api_client.incomings == {
        'key': 'API_KEY',
        'method': 'amazon_waf',
        'sitekey': WIDGET_KEY,
        'pageurl': URL,
        'jsapiScript': JSAPI_JS,
    }


@pytest.mark.asyncio
async def test_lone_context_is_refused():
    solver = make_waf_solver()
    with pytest.raises(ValidationException):
        await solver.amazon_waf(SITEKEY, None, CONTEXT, URL)


@pytest.mark.asyncio
async def test_off_aws_script_is_refused():
    solver = make_waf_solver()
    with pytest.raises(ValidationException):
        await solver.amazon_waf(SITEKEY, IV, CONTEXT, URL,
                                challenge_script='https://example.com/a/challenge.js')


@pytest.mark.asyncio
async def test_missing_pageurl_is_refused():
    solver = make_waf_solver()
    with pytest.raises(ValidationException):
        await solver.amazon_waf(SITEKEY)
