import json
import os
import time
from base64 import b64decode, b64encode

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
        # ALTCHA's createTask-shaped `solution` object. Carried through so
        # _apply_altcha_solution can read the counter the server already worked
        # out, which is the only reliable source for a proof-of-work v2 answer;
        # that method pops it, so it never reaches the caller.
        solution = polled.get('solution')
        if isinstance(solution, dict):
            result['solution'] = solution
    else:
        result['code'] = polled
    return result


# GeeTest answers come back as a JSON string in `request`, keyed with the
# geetest_ prefix that the target site's own form fields use.
_GEETEST_FIELDS = (
    ('challenge', 'geetest_challenge'),
    ('validate', 'geetest_validate'),
    ('seccode', 'geetest_seccode'),
)


def _apply_geetest_solution(result: dict) -> dict:
    """Expand the GeeTest answer into `challenge` / `validate` / `seccode`.

    `code` keeps the raw JSON string so callers that forward it verbatim (or that
    were written against another solver's API) keep working. If it does not parse,
    the result is returned untouched rather than masking the server's reply.
    """
    try:
        payload = json.loads(result.get('code') or '')
    except (json.JSONDecodeError, TypeError):
        return result

    if not isinstance(payload, dict):
        return result

    for short, prefixed in _GEETEST_FIELDS:
        value = payload.get(prefixed, payload.get(short))
        if value is not None:
            result[short] = value

    return result


# ALTCHA answers come back as a base64 payload: the challenge document with the
# winning counter added. That payload is what the site's own `altcha` form field
# carries, so it is posted back verbatim.
def _token_counter(code: str):
    """Dig the winning counter out of a token, whichever scheme produced it.

    The two ALTCHA generations nest it differently: a legacy payload is the
    challenge document with a top-level `number` added, while a proof-of-work v2
    payload is `{"challenge": {...}, "solution": {"counter": N, ...}}` and has no
    `number` at all. Returns None if the payload does not decode.
    """
    try:
        payload = json.loads(b64decode(code, validate=True))
    except (ValueError, TypeError):
        return None

    if not isinstance(payload, dict):
        return None

    if 'number' in payload:
        return payload['number']

    solution = payload.get('solution')
    if isinstance(solution, dict):
        return solution.get('counter')

    return None


def _apply_altcha_solution(result: dict) -> dict:
    """Expose the answer as `token`, and the winning counter as `number`.

    `code` keeps the raw answer so callers that forward it verbatim (or that were
    written against another solver's API) keep working; `token` is the same
    string, named for the form field it goes into.

    The counter comes from the server's own `solution` object when the poll
    carried one, because that is the single field both ALTCHA generations report
    the same way. Only if it is absent -- a plain-text poll -- is it dug out of
    the token, which is shaped differently per scheme. If neither yields one, the
    result keeps its token and simply has no `number`, rather than masking the
    server's reply.
    """
    code = result.get('code') or ''
    result['token'] = code

    solution = result.pop('solution', None)
    number = solution.get('number') if isinstance(solution, dict) else None
    if number is None:
        number = _token_counter(code)

    if number is not None:
        result['number'] = number

    return result


# A Capy solution is not a token. It is three values that together go into the
# target form, under the capy_ prefixed names the widget would have filled in.
_CAPY_FIELDS = ('captchakey', 'challengekey', 'answer', 'respKey')


def _apply_capy_solution(result: dict) -> dict:
    """Expand the Capy answer into `captchakey` / `challengekey` / `answer`.

    `code` keeps the raw answer -- a dict when polled with json=1, where the
    server puts the object straight into `request`, or the JSON string it sends
    after `OK|` in plain-text mode -- so callers that forward it verbatim (or
    that were written against another solver's API) keep working.

    If the answer does not parse, the result is returned untouched rather than
    masking the server's reply.
    """
    payload = result.pop('solution', None)

    if not isinstance(payload, dict):
        code = result.get('code')
        if isinstance(code, dict):
            payload = code
        else:
            try:
                payload = json.loads(code or '')
            except (json.JSONDecodeError, TypeError):
                return result

    if not isinstance(payload, dict):
        return result

    for field in _CAPY_FIELDS:
        if field in payload:
            result[field] = payload[field]

    return result


def _apply_token_solution(result: dict) -> dict:
    """Expose a single-token answer as `token`, named for the form field it fills.

    `code` keeps the raw answer so callers that forward it verbatim keep working;
    `token` is the same string. The server's createTask-shaped `solution` object
    carries that same string, so it is consumed here rather than handed back as a
    second copy -- but it is read first when `request` came through empty, so a
    client is never left without the token the poll actually carried.
    """
    solution = result.pop('solution', None)
    code = result.get('code')

    if not code and isinstance(solution, dict):
        code = solution.get('token') or ''
        result['code'] = code

    result['token'] = code or ''
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

    def geetest(self, gt, challenge, url, **kwargs):
        """Solve a GeeTest v3 slider.

        `gt` is static per site; `challenge` is single-use and expires in about a
        minute, so fetch a fresh pair immediately before calling this. Pass
        `api_server` when the site uses a non-default GeeTest API server domain.

        The result carries the raw answer as `code` (a JSON string) plus the
        parsed `challenge`, `validate`, and `seccode` fields to post back to the
        target site.
        """
        params = {
            'gt': gt,
            'challenge': challenge,
            'url': url,
            'method': 'geetest',
            'poll_json': 1,
            **kwargs,
        }
        # Like reCAPTCHA, this is a real browser solve (load, slide, verify) and
        # can retry internally, so it gets the longer of the two timeouts unless
        # the caller asked for a specific one.
        params.setdefault('timeout', self.recaptcha_timeout)
        return _apply_geetest_solution(self.solve(**params))

    def altcha(self, url, **kwargs):
        """Solve an ALTCHA proof-of-work challenge.

        Pass `challenge_url` for CapSkip to fetch the challenge itself, or
        `challenge_json` with the document you already have (a JSON string, or a
        dict which is serialized for you). Sending both is allowed -- the inline
        document wins. A proxy applies only to the `challenge_url` fetch.

        Challenges expire fast -- some sites inside two minutes -- and an expired
        one is refused with a bare "verification failed" that looks exactly like
        a wrong answer. Fetch the challenge immediately before calling, and post
        the token promptly.

        The result carries the raw answer as `code`, the same string as `token`
        (what the site's `altcha` form field expects, verbatim), and the counter
        that solved it as `number`.
        """
        params = {
            'url': url,
            'method': 'altcha',
            'poll_json': 1,
            # An unset challenge param is dropped rather than sent as None, so
            # `altcha(url, challenge_url=a, challenge_json=b)` works with either
            # one left out.
            **{k: v for k, v in kwargs.items() if v is not None},
        }
        # Unlike GeeTest and reCAPTCHA this is CPU proof-of-work measured in
        # milliseconds, not a browser solve, so it keeps the default timeout.
        return _apply_altcha_solution(self.solve(**params))

    def capy(self, sitekey, url, **kwargs):
        """Solve a Capy Puzzle captcha.

        `sitekey` is the site's public Capy key, conventionally prefixed
        `PUZZLE_`; it is sent as the `captchakey` the API documents. Pass
        `api_server` when the widget script points somewhere other than
        `https://jp.api.capy.me`.

        The result is not a token. It carries `captchakey`, `challengekey` and
        `answer`, which go into the target form's `capy_captchakey`,
        `capy_challengekey` and `capy_answer` fields, plus the raw answer as
        `code`. Submit `answer` verbatim -- it is the drag path the widget would
        have recorded, so trimming or re-encoding it invalidates the solve.

        The challenge key is single-use and short-lived, so submit promptly
        rather than caching the three values for a later request.
        """
        params = {
            'captchakey': sitekey,
            'url': url,
            'method': 'capy',
            'poll_json': 1,
            # An unset optional is dropped rather than sent as None, so
            # `capy(key, url, api_server=None)` behaves as if it were omitted.
            **{k: v for k, v in kwargs.items() if v is not None},
        }
        # A Capy solve is one HTTP fetch plus pixel math, not a browser session,
        # so it keeps the default timeout. It is held back to roughly two seconds
        # before the answer is released -- Capy refuses answers that arrive faster
        # than a human could have produced them -- which the default absorbs.
        return _apply_capy_solution(self.solve(**params))

    def captchafox(self, sitekey, url, **kwargs):
        """Solve a CaptchaFox challenge.

        `sitekey` is the public key the widget renders with, conventionally
        prefixed `sk_`, and `url` has to be the page the widget actually runs on:
        CaptchaFox checks it against the domains the key is registered for and
        refuses a mismatch permanently rather than intermittently.

        Pass `api_server` only when the target page does not load the default
        widget. A page loading the MAM package expects a `MAM_` prefixed token,
        and sending the wrong source still succeeds -- it just returns a token in
        a format the site will not accept, which reads as a silent verification
        failure rather than an error.

        The result carries the token as both `code` and `token`, for the form's
        `cf-captcha-response` field, and `userAgent` when the solve reported one.
        That User-Agent is the browser's own, not any you sent, so submit the
        token under it.
        """
        params = {
            'sitekey': sitekey,
            'url': url,
            'method': 'captchafox',
            'poll_json': 1,
            **{k: v for k, v in kwargs.items() if v is not None},
        }
        # A real browser session, like reCAPTCHA and GeeTest, and longer again
        # when an interactive challenge is drawn -- so it gets the longer of the
        # two timeouts unless the caller asked for a specific one.
        params.setdefault('timeout', self.recaptcha_timeout)
        return _apply_token_solution(self.solve(**params))

    def friendly_captcha(self, sitekey, url, **kwargs):
        """Solve a Friendly Captcha proof-of-work challenge.

        Two different protocols ship under this name and a sitekey does not tell
        you which one a site uses, so say which: pass `version='v1'` or
        `version='v2'`, or pass `module_script` with the src of the widget's
        `type="module"` script tag and let CapSkip read the version off the build
        the site actually loads. With neither, v1 is assumed. Solving the wrong
        version returns a well-formed token the target site rejects, with nothing
        to indicate the version was the problem.

        Pass `api_server='eu'` for a sitekey on the EU data-residency tenant;
        both tenants mint a token for the same sitekey, so the wrong one is only
        caught by the site's own verification.

        The result carries the token as both `code` and `token`. It goes into
        `frc-captcha-solution` on v1 and `frc-captcha-response` on v2 -- the
        field names differ, which is what catches an integration moved from one
        to the other. A v2 token is roughly six kilobytes, so size whatever
        carries it accordingly.
        """
        params = {
            'sitekey': sitekey,
            'url': url,
            'method': 'friendly_captcha',
            'poll_json': 1,
            **{k: v for k, v in kwargs.items() if v is not None},
        }
        # Proof-of-work, but not the millisecond kind ALTCHA does: the service
        # sets the difficulty per request and raises it for addresses it has seen
        # a lot of, and v2 always solves in a browser. Both make solve time
        # variable enough to want the longer timeout.
        params.setdefault('timeout', self.recaptcha_timeout)
        return _apply_token_solution(self.solve(**params))

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
        if method == 'geetest':
            return prepare_submit_params(params, 'geetest')
        if method == 'altcha':
            return prepare_submit_params(params, 'altcha')
        if method == 'capy':
            return prepare_submit_params(params, 'capy')
        if method == 'captchafox':
            return prepare_submit_params(params, 'captchafox')
        if method == 'friendly_captcha':
            return prepare_submit_params(params, 'friendly_captcha')
        return apply_proxy(apply_param_aliases(params))
