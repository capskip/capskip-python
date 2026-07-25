# CapSkip API Reference

Complete reference aligned with the [official CapSkip API](https://capskip.com/api-docs/).

CapSkip exposes a standard captcha-solver HTTP API on your local machine:

```
POST http://<host>:<port>/in.php   → submit captcha
GET  http://<host>:<port>/res.php  → poll result
```

The SDK only supports the captcha types documented by CapSkip.

---

## Supported captcha types

| Type | SDK method | `method` (POST) |
|---|---|---|
| Image captcha | `normal()` | `post` or `base64` |
| reCAPTCHA v2 | `recaptcha(..., version='v2')` | `userrecaptcha` |
| reCAPTCHA v3 | `recaptcha(..., version='v3')` | `userrecaptcha` + `version=v3` |
| Cloudflare Turnstile | `turnstile()` | `turnstile` |
| GeeTest v3 (slide) | `geetest()` | `geetest` |

**Proxy** is supported for reCAPTCHA, Turnstile, and GeeTest — not for image captcha.

---

## CapSkip (synchronous)

```python
from capskip import CapSkip

solver = CapSkip(
    apiKey="capskip",
    host="127.0.0.1",
    port=8080,
    defaultTimeout=120,
    recaptchaTimeout=300,
    pollingInterval=5,       # max seconds between polls; starts at 0.25s and backs off to this
)
```

---

## 1. Image captcha — `normal(file, json=0)`

### POST `/in.php`

| Parameter | Type | Required | Description |
|---|---|---|---|
| `key` | string | Yes | CapSkip API key |
| `method` | string | Yes | `post` (multipart file) or `base64` |
| `file` | file | Yes* | Image file when `method=post` |
| `body` | string | Yes* | Base64 image when `method=base64` |
| `json` | int | No | `0` plain text (default), `1` JSON |

### GET `/res.php`

| Parameter | Type | Required | Description |
|---|---|---|---|
| `key` | string | Yes | CapSkip API key |
| `action` | string | Yes | `get` |
| `id` | int | Yes | Captcha ID from `in.php` |
| `json` | int | No | `0` plain text (default), `1` JSON |

### SDK usage

```python
result = solver.normal("captcha.png")
result = solver.normal("https://example.com/captcha.jpg")
result = solver.normal("data:image/png;base64,iVBORw0KGgo...", json=1)
print(result["code"])
```

Only `json` is accepted as an extra parameter. Proxy is **not** supported.

---

## 2. reCAPTCHA v2 — `recaptcha(sitekey, url, version='v2', ...)`

### POST `/in.php`

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `key` | string | Yes | — | CapSkip API key |
| `method` | string | Yes | — | `userrecaptcha` |
| `googlekey` | string | Yes | — | Site key (`data-sitekey` / `k`) |
| `pageurl` | string | Yes | — | Full page URL |
| `enterprise` | int | No | `0` | `1` = Enterprise v2 |
| `invisible` | int | No | `0` | `1` = Invisible reCAPTCHA |
| `data-s` | string | No | — | Google Search / services `data-s` value |
| `json` | int | No | `0` | `1` = JSON response |
| `proxy` | string | No | — | `IP:PORT` or `login:pass@IP:PORT` |
| `proxytype` | string | No | `HTTP` | `HTTP`, `HTTPS`, `SOCKS5`, `SOCKS5H` |

Do **not** send `version`, `action`, or `min_score` for v2.

### GET `/res.php`

Same as image captcha poll parameters.

### SDK usage

```python
# Standard v2
result = solver.recaptcha(sitekey="...", url="https://example.com")

# Invisible v2
result = solver.recaptcha(sitekey="...", url="...", invisible=1)

# Enterprise v2
result = solver.recaptcha(sitekey="...", url="...", enterprise=1)

# Enterprise v2 with data-s (SDK alias: datas=...)
result = solver.recaptcha(sitekey="...", url="...", enterprise=1, datas="...")

# With proxy
result = solver.recaptcha(
    sitekey="...",
    url="...",
    proxy={"type": "HTTPS", "uri": "user:pass@1.2.3.4:3128"},
)
```

---

## 3. reCAPTCHA v3 — `recaptcha(..., version='v3', ...)`

### POST `/in.php`

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `key` | string | Yes | — | CapSkip API key |
| `method` | string | Yes | — | `userrecaptcha` |
| `version` | string | Yes | — | `v3` |
| `googlekey` | string | Yes | — | Site key |
| `pageurl` | string | Yes | — | Full page URL |
| `enterprise` | int | No | `0` | `1` = Enterprise v3 |
| `action` | string | No | `verify` | Action from `grecaptcha.execute()` |
| `min_score` | float | No | `0.4` | Minimum acceptable score |
| `json` | int | No | `0` | `1` = JSON response |
| `proxy` | string | No | — | Proxy address |
| `proxytype` | string | No | `HTTP` | Proxy type |

Do **not** send `invisible` for v3.

### SDK usage

```python
result = solver.recaptcha(
    sitekey="...",
    url="https://example.com",
    version="v3",
    action="submit",
    min_score=0.7,          # or SDK alias: score=0.7
    enterprise=0,
)
```

---

## 4. Cloudflare Turnstile — `turnstile(sitekey, url, ...)`

### POST `/in.php`

| Parameter | Type | Required | Description |
|---|---|---|---|
| `key` | string | Yes | CapSkip API key |
| `method` | string | Yes | `turnstile` |
| `sitekey` | string | Yes | Turnstile sitekey |
| `pageurl` | string | Yes | Full page URL |
| `action` | string | No | From `data-action` or `turnstile.render()` |
| `data` | string | No | `cData` / `data-cdata` |
| `pagedata` | string | No | `chlPageData` (challenge pages) |
| `json` | int | No | `0` plain text, `1` JSON |
| `proxy` | string | No | Proxy address |
| `proxytype` | string | No | Proxy type |

### GET `/res.php`

| Parameter | Type | Required | Description |
|---|---|---|---|
| `key` | string | Yes | CapSkip API key |
| `action` | string | Yes | `get` |
| `id` | int | Yes | Captcha ID |
| `json` | int | **Yes** | Must be `1` to receive User-Agent |

The SDK **automatically** polls Turnstile results with `json=1` and includes `userAgent` in the result when CapSkip returns it.

### SDK usage

```python
# Standalone widget
result = solver.turnstile(sitekey="0x4AAAAAAA...", url="https://example.com")
print(result["code"])
print(result.get("userAgent"))  # present when CapSkip returns it

# Challenge page
result = solver.turnstile(
    sitekey="0x4AAAAAAA...",
    url="https://example.com",
    action="managed",
    data="cData_value",
    pagedata="chlPageData_value",
)
# Use result["userAgent"] when submitting the token
```

---

## 5. GeeTest v3 — `geetest(gt, challenge, url, ...)`

### POST `/in.php`

| Parameter | Type | Required | Description |
|---|---|---|---|
| `key` | string | Yes | CapSkip API key |
| `method` | string | Yes | `geetest` |
| `gt` | string | Yes | Static per-site GeeTest id |
| `challenge` | string | Yes | Single-use challenge token |
| `pageurl` | string | Yes | Full page URL |
| `api_server` | string | No | GeeTest API server domain, e.g. `api-na.geetest.com` |
| `json` | int | No | `0` plain text, `1` JSON |
| `proxy` | string | No | Proxy address |
| `proxytype` | string | No | Proxy type |

### Getting `gt` and `challenge`

Both come from the target site, which fetches them from an endpoint returning
`{"gt": "...", "challenge": "..."}` (often `.../register.php` or a `gettype`/`get.php`
request). Find it in DevTools → Network, or read them out of the
`initGeetest({ gt, challenge })` call in the page scripts.

> **`challenge` is single-use and expires in about a minute.** Fetch a fresh pair
> immediately before each solve. If a solve comes back with a bad-challenge error,
> request a new pair and retry — reusing one never succeeds.

### SDK usage

```python
result = solver.geetest(
    gt="81388ea1fc187e0c335c0a8907ff2625",
    challenge="7cf6a8b1a2c34d5e6f7089abcdef0123",
    url="https://example.com/login",
)

result["challenge"]   # geetest_challenge
result["validate"]    # geetest_validate
result["seccode"]     # geetest_seccode
result["code"]        # the same answer as a raw JSON string
```

Post the three fields back exactly as the site's own front-end would:

```python
requests.post(LOGIN_URL, data={
    "geetest_challenge": result["challenge"],
    "geetest_validate": result["validate"],
    "geetest_seccode": result["seccode"],
})
```

GeeTest is a real browser solve, so it uses the longer `recaptchaTimeout` budget
rather than `defaultTimeout`.

---

## Return value

Every solve method returns:

```python
{
    "captchaId": "12345",
    "code": "TOKEN_OR_TEXT",
    "userAgent": "..."   # Turnstile only, when json=1 poll includes it
}
```

GeeTest additionally expands its answer into `challenge`, `validate`, and
`seccode` (`code` keeps the raw JSON string):

```python
{
    "captchaId": "12345",
    "code": '{"geetest_challenge":"...","geetest_validate":"...","geetest_seccode":"..."}',
    "challenge": "...",
    "validate": "...",
    "seccode": "...",
}
```

---

## SDK parameter aliases

Convenience aliases mapped before sending to CapSkip:

| SDK alias | CapSkip API param |
|---|---|
| `url` | `pageurl` |
| `score` | `min_score` |
| `minScore` | `min_score` |
| `datas` | `data-s` |
| `data_s` | `data-s` |
| `apiServer` | `api_server` |
| `api_subdomain` | `api_server` |
| `proxy` dict | `proxy` + `proxytype` strings |

```python
proxy = {"type": "HTTPS", "uri": "login:password@1.2.3.4:3128"}
```

Unsupported parameters (e.g. `numeric` on image captcha, `action` on v2) raise `ValidationException`.

---

## Manual workflow

### `send(**kwargs)`

Submit without polling. Returns captcha ID string.

```python
captcha_id = solver.send(
    method="userrecaptcha",
    googlekey="...",
    pageurl="https://example.com",
)
```

### `get_result(id_, json=0)`

Poll once. Raises `NetworkException` while `CAPCHA_NOT_READY`.

```python
from capskip import NetworkException

code = solver.get_result(captcha_id)              # plain text
data = solver.get_result(captcha_id, json=1)      # dict when json=1
```

---

## AsyncCapSkip

Same API as `CapSkip`, all methods are async:

```python
from capskip import AsyncCapSkip

solver = AsyncCapSkip()
result = await solver.turnstile(sitekey="...", url="...")
```

---

## Exceptions

| Exception | When |
|---|---|
| `ValidationException` | Invalid/unsupported parameters |
| `NetworkException` | Connection error, or captcha not ready |
| `ApiException` | CapSkip API error response |
| `TimeoutException` | Polling timeout exceeded |

---

## Low-level HTTP (ApiClient)

```python
from capskip import ApiClient

client = ApiClient(host="127.0.0.1", port=8080)
client.in_(method="turnstile", key="capskip", sitekey="...", pageurl="...")
client.res(key="capskip", action="get", id="12345", json=1)
```
