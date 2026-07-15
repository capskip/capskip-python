import asyncio
import os
import time
from base64 import b64encode

import httpx

from .async_api import AsyncApiClient
from ._api_params import apply_param_aliases, apply_proxy, prepare_submit_params
from .exceptions import NetworkException, TimeoutException, ValidationException, SolverExceptions
from .solver import (
    INITIAL_POLLING_INTERVAL,
    _apply_poll_result,
    _next_poll_interval,
    _parse_poll_response,
    _parse_submit_response,
)


class AsyncCapSkip:
    """Async client for the CapSkip local captcha solver."""

    def __init__(self,
                 apiKey='capskip',
                 host='127.0.0.1',
                 port=8080,
                 defaultTimeout=120,
                 recaptchaTimeout=300,
                 pollingInterval=5):

        self.API_KEY = apiKey
        self.default_timeout = defaultTimeout
        self.recaptcha_timeout = recaptchaTimeout
        self.polling_interval = pollingInterval
        self.api_client = AsyncApiClient(host=host, port=port)
        self.exceptions = SolverExceptions

    async def normal(self, file, **kwargs):
        unsupported = set(kwargs) - {'json'}
        if unsupported:
            raise ValidationException(
                f"Unsupported parameters for image captcha: {sorted(unsupported)}. "
                f"Only json is supported besides the image input."
            )
        method = await self.get_method(file)
        return await self.solve(**method, **kwargs)

    async def recaptcha(self, sitekey, url, version='v2', enterprise=0, **kwargs):
        params = {
            'googlekey': sitekey,
            'url': url,
            'method': 'userrecaptcha',
            'enterprise': enterprise,
            **kwargs,
        }
        if str(version).lower() == 'v3':
            params['version'] = 'v3'
        return await self.solve(timeout=self.recaptcha_timeout, **params)

    async def turnstile(self, sitekey, url, **kwargs):
        return await self.solve(
            sitekey=sitekey,
            url=url,
            method='turnstile',
            poll_json=1,
            **kwargs,
        )

    async def solve(self, timeout=0, polling_interval=0, poll_json=0, **kwargs):
        poll_json = int(kwargs.pop('poll_json', poll_json) or 0)
        captcha_id = await self.send(**kwargs)
        result = {'captchaId': captcha_id}
        timeout = float(timeout or self.default_timeout)
        sleep = float(polling_interval or self.polling_interval)
        polled = await self.wait_result(captcha_id, timeout, sleep, json=poll_json)
        return _apply_poll_result(result, polled)

    async def wait_result(self, id_, timeout, polling_interval, json=0):
        deadline = time.time() + timeout
        interval = min(INITIAL_POLLING_INTERVAL, polling_interval)
        while time.time() < deadline:
            try:
                return await self.get_result(id_, json=json)
            except NetworkException:
                await asyncio.sleep(interval)
                interval = _next_poll_interval(interval, polling_interval)
        raise TimeoutException(f'timeout {timeout} exceeded')

    async def get_method(self, file):
        if not file:
            raise ValidationException('File required')
        if file.startswith('data:'):
            return {'method': 'base64', 'body': file.split(',', 1)[1]}
        if '.' not in file and len(file) > 50:
            return {'method': 'base64', 'body': file}
        if file.startswith('http'):
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(file)
                if resp.status_code != 200:
                    raise ValidationException(f'File could not be downloaded from url: {file}')
                return {'method': 'base64', 'body': b64encode(resp.content).decode('utf-8')}
        if not os.path.exists(file):
            raise ValidationException(f'File not found: {file}')
        return {'method': 'post', 'file': file}

    async def send(self, **kwargs):
        params = self._prepare_send_params({**kwargs, 'key': self.API_KEY})
        files = params.pop('files', {})
        response = await self.api_client.in_(files=files, **params)
        return _parse_submit_response(response)

    async def get_result(self, id_, json=0):
        query = {'key': self.API_KEY, 'action': 'get', 'id': id_}
        if json:
            query['json'] = 1
        response = await self.api_client.res(**query)
        return _parse_poll_response(response, json_mode=int(json or 0))

    def _prepare_send_params(self, params: dict) -> dict:
        method = params.get('method')
        if method in ('post', 'base64'):
            return prepare_submit_params(params, 'normal')
        if method == 'userrecaptcha':
            return prepare_submit_params(params, 'recaptcha', params.get('version', 'v2'))
        if method == 'turnstile':
            return prepare_submit_params(params, 'turnstile')
        return apply_proxy(apply_param_aliases(params))
