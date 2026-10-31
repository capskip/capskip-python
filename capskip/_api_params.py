"""CapSkip API parameter validation (https://capskip.com/api-docs/)."""

import json
import re
from urllib.parse import urlsplit

from .exceptions import ValidationException

NORMAL_SUBMIT = frozenset({'method', 'body', 'json', 'file'})

RECAPTCHA_V2_SUBMIT = frozenset({
    'method', 'googlekey', 'pageurl', 'enterprise', 'invisible', 'data-s', 'json',
    'proxy', 'proxytype',
})

RECAPTCHA_V3_SUBMIT = frozenset({
    'method', 'version', 'googlekey', 'pageurl', 'enterprise', 'action', 'min_score',
    'json', 'proxy', 'proxytype',
})

TURNSTILE_SUBMIT = frozenset({
    'method', 'sitekey', 'pageurl', 'action', 'data', 'pagedata', 'json',
    'proxy', 'proxytype',
})

GEETEST_SUBMIT = frozenset({
    'method', 'gt', 'challenge', 'pageurl', 'api_server', 'json',
    'proxy', 'proxytype',
})

ALTCHA_SUBMIT = frozenset({
    'method', 'pageurl', 'challenge_url', 'challenge_json', 'json',
    'proxy', 'proxytype',
})

CAPY_SUBMIT = frozenset({
    'method', 'captchakey', 'pageurl', 'api_server', 'version', 'useragent', 'json',
    'proxy', 'proxytype',
})

CAPTCHAFOX_SUBMIT = frozenset({
    'method', 'sitekey', 'pageurl', 'api_server', 'useragent', 'json',
    'proxy', 'proxytype',
})

FRIENDLY_CAPTCHA_SUBMIT = frozenset({
    'method', 'sitekey', 'pageurl', 'version', 'module_script', 'nomodule_script',
    'api_server', 'useragent', 'json', 'proxy', 'proxytype',
})

AMAZON_WAF_SUBMIT = frozenset({
    'method', 'sitekey', 'pageurl', 'iv', 'context', 'challenge_script',
    'captcha_script', 'jsapiScript', 'json', 'proxy', 'proxytype',
})

# The script parameters of an AWS WAF task. CapSkip POSTs the solution to the
# host these name, so it refuses any that is not a genuine AWS WAF one.
AMAZON_WAF_SCRIPTS = ('challenge_script', 'captcha_script', 'jsapiScript')

# The server's own test: one or more [A-Za-z0-9_-] path segments, then one of
# the three AWS WAF script files.
_AMAZON_WAF_SCRIPT_PATH = re.compile(
    r'^(/[A-Za-z0-9_-]+)+/(challenge|captcha|jsapi)\.js$'
)

# CapSkip solves the puzzle family only. `avatar` is a different challenge behind
# a different endpoint; the server refuses it at submit time rather than answering
# it with a puzzle answer, which would bill for a solve the target site rejects.
CAPY_VERSIONS = ('puzzle',)

# Both spellings the server accepts, and the bare digits it also takes.
FRIENDLY_CAPTCHA_VERSIONS = ('v1', 'v2', '1', '2')

# The only values CapSkip maps to a proxy scheme; it answers
# ERROR_BAD_PARAMETERS for anything else, SOCKS4 included. Matched
# case-insensitively, as the server does.
PROXY_TYPES = ('HTTP', 'HTTPS', 'SOCKS5', 'SOCKS5H')

_PARAM_ALIASES = {
    'url': 'pageurl',
    'score': 'min_score',
    'minScore': 'min_score',
    'datas': 'data-s',
    'data_s': 'data-s',
    'apiServer': 'api_server',
    'api_subdomain': 'api_server',
    'challengeUrl': 'challenge_url',
    'challengeURL': 'challenge_url',
    'challengeJson': 'challenge_json',
    'challengeJSON': 'challenge_json',
    # The server reads userAgent and useragent interchangeably on every method
    # that takes one, so the SDK settles on the lowercase spelling its parameter
    # tables document and accepts the camelCase one callers arrive with.
    'userAgent': 'useragent',
    'user_agent': 'useragent',
    'captchaKey': 'captchakey',
    'moduleScript': 'module_script',
    'nomoduleScript': 'nomodule_script',
    'noModuleScript': 'nomodule_script',
    # AWS WAF: the API documents challenge_script / captcha_script in snake case
    # and jsapiScript in camel case, as 2Captcha does. Accept the other spelling
    # of each, which is what createTask-style callers arrive with.
    'challengeScript': 'challenge_script',
    'captchaScript': 'captcha_script',
    'jsapi_script': 'jsapiScript',
}


def apply_param_aliases(params: dict) -> dict:
    out = dict(params)
    for alias, api_name in _PARAM_ALIASES.items():
        if alias in out:
            if api_name in out and out[alias] != out[api_name]:
                raise ValidationException(
                    f"Conflicting parameters: {alias!r} and {api_name!r}"
                )
            out[api_name] = out.pop(alias)
    return out


def apply_proxy(params: dict) -> dict:
    out = dict(params)
    proxy = out.pop('proxy', None)
    if not proxy:
        return out
    if isinstance(proxy, dict):
        if 'uri' not in proxy or 'type' not in proxy:
            raise ValidationException("proxy dict must contain 'type' and 'uri' keys")
        out['proxy'] = proxy['uri']
        out['proxytype'] = proxy['type']
    else:
        out['proxy'] = proxy
        if 'proxytype' not in out:
            out['proxytype'] = 'HTTP'
    return out


def _unknown_keys(params: dict, allowed: frozenset) -> set:
    return set(params.keys()) - allowed - {'key', 'file', 'files'}


def validate_normal_submit(params: dict) -> None:
    unknown = _unknown_keys(params, NORMAL_SUBMIT)
    if unknown:
        raise ValidationException(
            f"Unsupported parameters for image captcha: {sorted(unknown)}. "
            f"CapSkip only supports: method, file/body, json."
        )
    if 'proxy' in params or 'proxytype' in params:
        raise ValidationException(
            "Proxy is not supported for image captcha. "
            "Use proxy only with reCAPTCHA or Turnstile."
        )


def validate_recaptcha_submit(params: dict, version: str) -> None:
    version = (version or 'v2').lower()
    if version == 'v3':
        allowed = RECAPTCHA_V3_SUBMIT
        if params.get('invisible'):
            raise ValidationException("invisible is only supported for reCAPTCHA v2.")
    else:
        allowed = RECAPTCHA_V2_SUBMIT
        if params.get('version') == 'v3':
            raise ValidationException("Use version='v3' for reCAPTCHA v3.")
        for key in ('action', 'min_score'):
            if key in params:
                raise ValidationException(f"{key!r} is only supported for reCAPTCHA v3.")

    unknown = _unknown_keys(params, allowed)
    if unknown:
        raise ValidationException(
            f"Unsupported parameters for reCAPTCHA {version}: {sorted(unknown)}."
        )


def validate_turnstile_submit(params: dict) -> None:
    unknown = _unknown_keys(params, TURNSTILE_SUBMIT)
    if unknown:
        raise ValidationException(
            f"Unsupported parameters for Turnstile: {sorted(unknown)}."
        )


def validate_geetest_submit(params: dict) -> None:
    # All three are documented as required. gt is static per site, challenge is
    # single-use and expires in about a minute; without them CapSkip answers
    # ERROR_BAD_PARAMETERS, and without pageurl ERROR_PAGEURL. Fail locally so a
    # missing value does not cost a round-trip.
    for key in ('gt', 'challenge', 'pageurl'):
        if not params.get(key):
            raise ValidationException(f"{key!r} is required for GeeTest v3.")

    unknown = _unknown_keys(params, GEETEST_SUBMIT)
    if unknown:
        raise ValidationException(
            f"Unsupported parameters for GeeTest: {sorted(unknown)}."
        )


def normalize_altcha_submit(params: dict) -> dict:
    """Drop unset challenge params and serialize an inline challenge document.

    `altcha(url, challenge_url=a, challenge_json=b)` is normally called with one
    of the two left as None, and the form body can only carry a string — so a
    document passed as a dict is serialized rather than stringified into Python's
    repr. Mirrors the server, which reads a JSON-body `null` as "not sent".
    """
    out = {k: v for k, v in params.items() if v is not None}

    challenge = out.get('challenge_json')
    if isinstance(challenge, (dict, list)):
        out['challenge_json'] = json.dumps(challenge)

    return out


def validate_altcha_submit(params: dict) -> None:
    if not params.get('pageurl'):
        raise ValidationException("'pageurl' is required for ALTCHA.")

    # CapSkip answers ERROR_BAD_PARAMETERS when neither is sent. Sending both is
    # deliberately allowed -- the inline document simply wins, because fetching
    # would only re-obtain what the caller already supplied.
    if not params.get('challenge_url') and not params.get('challenge_json'):
        raise ValidationException(
            "ALTCHA needs a challenge: pass 'challenge_url' for CapSkip to fetch "
            "it, or 'challenge_json' with the challenge document itself."
        )

    unknown = _unknown_keys(params, ALTCHA_SUBMIT)
    if unknown:
        raise ValidationException(
            f"Unsupported parameters for ALTCHA: {sorted(unknown)}."
        )


def drop_unset(params: dict) -> dict:
    """Drop parameters left as None so an omitted optional is not sent as 'None'.

    The form body can only carry strings, so a default of None would otherwise
    reach the server stringified. Mirrors the server, which reads a JSON-body
    `null` as "not sent".
    """
    return {k: v for k, v in params.items() if v is not None}


def validate_capy_submit(params: dict) -> None:
    # Both are documented as required; without captchakey the server answers
    # ERROR_BAD_PARAMETERS and without pageurl ERROR_PAGEURL. Fail locally so a
    # missing value does not cost a round-trip.
    for key in ('captchakey', 'pageurl'):
        if not params.get(key):
            raise ValidationException(f"{key!r} is required for Capy.")

    version = params.get('version')
    if version not in (None, '') and str(version).lower() not in CAPY_VERSIONS:
        raise ValidationException(
            f"Unsupported Capy version {version!r}. CapSkip solves the puzzle "
            f"family only -- 'avatar' is a different challenge behind a different "
            f"endpoint, and the server refuses it rather than returning a puzzle "
            f"answer the target site would reject."
        )

    unknown = _unknown_keys(params, CAPY_SUBMIT)
    if unknown:
        raise ValidationException(
            f"Unsupported parameters for Capy: {sorted(unknown)}."
        )


def validate_captchafox_submit(params: dict) -> None:
    for key in ('sitekey', 'pageurl'):
        if not params.get(key):
            raise ValidationException(f"{key!r} is required for CaptchaFox.")

    unknown = _unknown_keys(params, CAPTCHAFOX_SUBMIT)
    if unknown:
        raise ValidationException(
            f"Unsupported parameters for CaptchaFox: {sorted(unknown)}."
        )


def validate_friendly_captcha_submit(params: dict) -> None:
    for key in ('sitekey', 'pageurl'):
        if not params.get(key):
            raise ValidationException(f"{key!r} is required for Friendly Captcha.")

    version = params.get('version')
    if version not in (None, '') and str(version).lower() not in FRIENDLY_CAPTCHA_VERSIONS:
        raise ValidationException(
            f"Unsupported Friendly Captcha version {version!r}. Use 'v1' or 'v2' "
            f"(a bare 1 or 2 is accepted too). The two are different protocols "
            f"sharing one sitekey namespace, so solving the wrong one returns a "
            f"well-formed token the target site rejects."
        )

    unknown = _unknown_keys(params, FRIENDLY_CAPTCHA_SUBMIT)
    if unknown:
        raise ValidationException(
            f"Unsupported parameters for Friendly Captcha: {sorted(unknown)}."
        )


def is_amazon_waf_script_url(url) -> bool:
    """True for a script URL CapSkip will accept on an AWS WAF task.

    Mirrors the server: https, a host under .awswaf.com, no credentials or
    explicit port, and a path ending in challenge.js, captcha.js or jsapi.js.
    The server only applies the check once the task is queued, so failing here
    saves a submit that could never solve.
    """
    try:
        parts = urlsplit(str(url).strip())
        port = parts.port
    except ValueError:
        return False
    host = (parts.hostname or '').lower()
    return (
        parts.scheme.lower() == 'https'
        and host.endswith('.awswaf.com')
        and parts.username is None
        and parts.password is None
        and port in (None, 443)
        and bool(_AMAZON_WAF_SCRIPT_PATH.match(parts.path))
    )


def validate_amazon_waf_submit(params: dict) -> None:
    # Without sitekey the server answers ERROR_BAD_PARAMETERS and without
    # pageurl ERROR_PAGEURL. Fail locally so a missing value costs no round-trip.
    for key in ('sitekey', 'pageurl'):
        if not params.get(key):
            raise ValidationException(f"{key!r} is required for Amazon WAF.")

    pageurl = str(params['pageurl']).strip()
    if urlsplit(pageurl).scheme.lower() not in ('http', 'https') or '://' not in pageurl:
        raise ValidationException(
            f"'pageurl' must be a full http or https URL for Amazon WAF, got {pageurl!r}."
        )

    # iv and context come off the same challenge page and only work as a pair;
    # the server refuses one without the other with ERROR_BAD_PARAMETERS.
    if bool(params.get('iv')) != bool(params.get('context')):
        raise ValidationException(
            "Amazon WAF 'iv' and 'context' go together: send both (a challenge "
            "page) or neither (a widget page, or let CapSkip read them from pageurl)."
        )

    for key in AMAZON_WAF_SCRIPTS:
        value = params.get(key)
        if value and not is_amazon_waf_script_url(value):
            raise ValidationException(
                f"{key!r} must be the https URL of an AWS WAF script on an "
                f"awswaf.com host (challenge.js, captcha.js or jsapi.js), got {value!r}. "
                f"CapSkip refuses any other script, because it is not an AWS WAF integration."
            )

    unknown = _unknown_keys(params, AMAZON_WAF_SUBMIT)
    if unknown:
        raise ValidationException(
            f"Unsupported parameters for Amazon WAF: {sorted(unknown)}."
        )


def validate_proxy_type(params: dict) -> None:
    proxytype = params.get('proxytype')
    if proxytype in (None, ''):
        return
    if str(proxytype).upper() not in PROXY_TYPES:
        raise ValidationException(
            f"Unsupported proxytype {proxytype!r}. "
            f"CapSkip accepts: {', '.join(PROXY_TYPES)}."
        )


def prepare_submit_params(params: dict, captcha_type: str, version: str = 'v2') -> dict:
    params = apply_param_aliases(params)
    params = apply_proxy(params)

    if captcha_type == 'normal':
        validate_normal_submit(params)
    elif captcha_type == 'recaptcha':
        validate_recaptcha_submit(params, version)
    elif captcha_type == 'turnstile':
        validate_turnstile_submit(params)
    elif captcha_type == 'geetest':
        validate_geetest_submit(params)
    elif captcha_type == 'altcha':
        params = normalize_altcha_submit(params)
        validate_altcha_submit(params)
    elif captcha_type == 'capy':
        params = drop_unset(params)
        validate_capy_submit(params)
    elif captcha_type == 'captchafox':
        params = drop_unset(params)
        validate_captchafox_submit(params)
    elif captcha_type == 'friendly_captcha':
        params = drop_unset(params)
        validate_friendly_captcha_submit(params)
    elif captcha_type == 'amazon_waf':
        # An optional left as '' means "not sent" to the server, exactly like
        # None, so it is dropped rather than tripping the iv/context pairing.
        params = {k: v for k, v in drop_unset(params).items() if v != ''}
        validate_amazon_waf_submit(params)

    # Skipped for 'normal', which rejects proxy outright with a clearer message.
    if captcha_type != 'normal':
        validate_proxy_type(params)

    return params
