"""CapSkip API parameter validation (https://capskip.com/api-docs/)."""

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

_PARAM_ALIASES = {
    'url': 'pageurl',
    'score': 'min_score',
    'minScore': 'min_score',
    'datas': 'data-s',
    'data_s': 'data-s',
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


def prepare_submit_params(params: dict, captcha_type: str, version: str = 'v2') -> dict:
    params = apply_param_aliases(params)
    params = apply_proxy(params)

    if captcha_type == 'normal':
        validate_normal_submit(params)
    elif captcha_type == 'recaptcha':
        validate_recaptcha_submit(params, version)
    elif captcha_type == 'turnstile':
        validate_turnstile_submit(params)

    return params
