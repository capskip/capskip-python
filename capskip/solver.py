import json
import os
import time
from base64 import b64encode

import requests

from .api import ApiClient
from ._api_params import apply_param_aliases, apply_proxy, prepare_submit_params
from .exceptions import ApiException, NetworkException, TimeoutException, ValidationException, SolverExceptions

# First poll fires this soon after submitting, then the interval backs off
# (doubling) up to the configured pollingInterval ceiling. Keeps latency low for
# fast local solves (e.g. image captchas) without hammering on slow ones.
INITIAL_POLLING_INTERVAL = 0.25


def _next_poll_interval(interval: float, ceiling: float) -> float:
    return min(interval * 2, ceiling)


def _parse_poll_response(response: str, json_mode: int = 0):
    text = (response or '').strip()

    # CapSkip returns an empty body whenever no result is available yet: briefly
    # right after submit (before it starts reporting CAPCHA_NOT_READY), for an
    # unknown id, and after a solved token has already been read once. Treat it
    # like CAPCHA_NOT_READY so the caller keeps polling instead of failing.
    if not text:
        raise NetworkException

    if json_mode:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ApiException(f'invalid JSON response: {response}') from exc

        if data.get('status') == 0 and data.get('request') == 'CAPCHA_NOT_READY':
            raise NetworkException

        if data.get('status') != 1:
            raise ApiException(f'cannot recognize response {data}')

        return data

    if text == 'CAPCHA_NOT_READY':
        raise NetworkException

    if not text.startswith('OK|'):
        raise ApiException(f'cannot recognize response {response}')

    return text[3:]


def _apply_poll_result(result: dict, polled) -> dict:
    if isinstance(polled, dict):
        result['code'] = polled.get('request', '')
        user_agent = polled.get('useragent') or polled.get('userAgent')
        if user_agent:
            result['userAgent'] = user_agent
    else:
        result['code'] = polled
    return result


def _parse_submit_response(response: str) -> str:
    # CapSkip's in.php returns OK|<id> by default, or {"status":1,"request":"<id>"}
    # when the submit carried json=1. Accept both so submitting with json=1 works.
    text = (response or '').strip()

    if text.startswith('OK|'):
        return text[3:]

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        data = None

    if isinstance(data, dict) and data.get('status') == 1 and 'request' in data:
        return str(data['request'])

    raise ApiException(f'cannot recognize response {response}')


class CapSkip:
    """Client for the CapSkip local captcha solver (image, reCAPTCHA, Turnstile)."""

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
        self.api_client = ApiClient(host=host, port=port)
        self.exceptions = SolverExceptions

    def normal(self, file, **kwargs):
        unsupported = set(kwargs) - {'json'}
        if unsupported:
            raise ValidationException(
                f"Unsupported parameters for image captcha: {sorted(unsupported)}. "
                f"Only json is supported besides the image input."
            )
        return self.solve(**self.get_method(file), **kwargs)

    def recaptcha(self, sitekey, url, version='v2', enterprise=0, **kwargs):
        params = {
            'googlekey': sitekey,
            'url': url,
            'method': 'userrecaptcha',
            'enterprise': enterprise,
            **kwargs,
        }
        if str(version).lower() == 'v3':
            params['version'] = 'v3'
        return self.solve(timeout=self.recaptcha_timeout, **params)

    def turnstile(self, sitekey, url, **kwargs):
        return self.solve(
            sitekey=sitekey,
            url=url,
            method='turnstile',
            poll_json=1,
            **kwargs,
        )

    def solve(self, timeout=0, polling_interval=0, poll_json=0, **kwargs):
        poll_json = int(kwargs.pop('poll_json', poll_json) or 0)
        captcha_id = self.send(**kwargs)
        result = {'captchaId': captcha_id}
        timeout = float(timeout or self.default_timeout)
        sleep = float(polling_interval or self.polling_interval)
        polled = self.wait_result(captcha_id, timeout, sleep, json=poll_json)
        return _apply_poll_result(result, polled)

    def wait_result(self, id_, timeout, polling_interval, json=0):
        deadline = time.time() + timeout
        interval = min(INITIAL_POLLING_INTERVAL, polling_interval)
        while time.time() < deadline:
            try:
                return self.get_result(id_, json=json)
            except NetworkException:
                time.sleep(interval)
                interval = _next_poll_interval(interval, polling_interval)
        raise TimeoutException(f'timeout {timeout} exceeded')

    def get_method(self, file):
        if not file:
            raise ValidationException('File required')
        if file.startswith('data:'):
            return {'method': 'base64', 'body': file.split(',', 1)[1]}
        if '.' not in file and len(file) > 50:
            return {'method': 'base64', 'body': file}
        if file.startswith('http'):
            resp = requests.get(file)
            if resp.status_code != 200:
                raise ValidationException(f'File could not be downloaded from url: {file}')
            return {'method': 'base64', 'body': b64encode(resp.content).decode('utf-8')}
        if not os.path.exists(file):
            raise ValidationException(f'File not found: {file}')
        return {'method': 'post', 'file': file}

    def send(self, **kwargs):
        params = self._prepare_send_params({**kwargs, 'key': self.API_KEY})
        files = params.pop('files', {})
        response = self.api_client.in_(files=files, **params)
        return _parse_submit_response(response)

    def get_result(self, id_, json=0):
        query = {'key': self.API_KEY, 'action': 'get', 'id': id_}
        if json:
            query['json'] = 1
        return _parse_poll_response(self.api_client.res(**query), json_mode=int(json or 0))

    def _prepare_send_params(self, params: dict) -> dict:
        method = params.get('method')
        if method in ('post', 'base64'):
            return prepare_submit_params(params, 'normal')
        if method == 'userrecaptcha':
            return prepare_submit_params(params, 'recaptcha', params.get('version', 'v2'))
        if method == 'turnstile':
            return prepare_submit_params(params, 'turnstile')
        return apply_proxy(apply_param_aliases(params))
