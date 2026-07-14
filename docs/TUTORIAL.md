# CapSkip Python SDK — Complete Tutorial

This tutorial takes you from zero to solving every captcha type CapSkip supports,
using both the synchronous and asynchronous clients. Work through it top to bottom,
or jump to the section you need.

**Contents**

1. [How it works](#1-how-it-works)
2. [Install and configure](#2-install-and-configure)
3. [Your first solve](#3-your-first-solve)
4. [Image captcha](#4-image-captcha)
5. [reCAPTCHA v2](#5-recaptcha-v2)
6. [reCAPTCHA v3](#6-recaptcha-v3)
7. [Cloudflare Turnstile](#7-cloudflare-turnstile)
8. [Using a proxy](#8-using-a-proxy)
9. [Async and concurrency](#9-async-and-concurrency)
10. [The manual workflow](#10-the-manual-workflow)
11. [Return values](#11-return-values)
12. [Error handling](#12-error-handling)
13. [End-to-end: solve and submit](#13-end-to-end-solve-and-submit)
14. [Parameter reference](#14-parameter-reference)
15. [Best practices](#15-best-practices)

---

## 1. How it works

CapSkip is a **local** application that solves captchas on your own machine and
exposes a standard captcha-solver HTTP API (documented in the [CapSkip API docs](https://capskip.com/api-docs/)):

```
POST http://<host>:<port>/in.php   → submit a captcha, returns  OK|<id>
GET  http://<host>:<port>/res.php  → poll for the answer, returns  OK|<solution>
```

This SDK is a thin, friendly wrapper around that API. Every solve follows the
same three steps, which the SDK does for you:

1. **Submit** the captcha (`in.php`) and receive a captcha ID.
2. **Poll** the result endpoint (`res.php`) every few seconds while the answer is
   not ready.
3. **Return** the solution once CapSkip finishes.

You never have to write the polling loop yourself — call one method and get the
answer back.

---

## 2. Install and configure

### Install CapSkip

Download and launch the CapSkip desktop app from [capskip.com](https://capskip.com),
and leave it running. In **Settings**, note the **API port** (default `8080`) and,
if API-key validation is enabled, your **API key**.

### Install the SDK

```bash
pip install capskip
```

Verify:

```bash
python -c "import capskip; print(capskip.__version__)"
python examples/verify_connection.py     # checks CapSkip is reachable
```

### Configure the client

```python
from capskip import CapSkip

solver = CapSkip(
    apiKey="capskip",        # your CapSkip API key (any string if validation is off)
    host="127.0.0.1",        # where CapSkip is listening
    port=8080,               # API port from CapSkip settings
    defaultTimeout=120,      # seconds to wait for an image captcha
    recaptchaTimeout=300,    # seconds to wait for reCAPTCHA / Turnstile
    pollingInterval=5,       # max seconds between result polls (starts at 0.25s, backs off to this)
)
```

In production, read configuration from the environment instead of hard-coding it:

```python
import os
from capskip import CapSkip

solver = CapSkip(
    apiKey=os.getenv("CAPSKIP_API_KEY", "capskip"),
    host=os.getenv("CAPSKIP_HOST", "127.0.0.1"),
    port=int(os.getenv("CAPSKIP_PORT", "8080")),
)
```

---

## 3. Your first solve

```python
from capskip import CapSkip

solver = CapSkip(host="127.0.0.1", port=8080)

result = solver.recaptcha(
    sitekey="6Le-wvkS...your-sitekey",
    url="https://example.com/page-with-recaptcha",
)

print(result["code"])       # the g-recaptcha-response token
print(result["captchaId"])  # CapSkip's internal ID for this solve
```

`result` is always a dictionary. The solution is in `result["code"]`.

---

## 4. Image captcha

Use `solver.normal(...)` for classic distorted-text images. The SDK accepts four
input forms and auto-detects which one you passed:

```python
# 1. Local file path
result = solver.normal("captcha.png")

# 2. Remote image URL (the SDK downloads and encodes it)
result = solver.normal("https://example.com/captcha.jpg")

# 3. Base64 string (no file extension, longer than 50 characters)
import base64
with open("captcha.png", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
result = solver.normal(b64)

# 4. Data-URI
result = solver.normal("data:image/png;base64,iVBORw0KGgo...")

print(result["code"])   # the recognized text
```

Image captcha accepts only one extra argument, `json`, which controls the raw
response format from CapSkip:

```python
result = solver.normal("captcha.png", json=1)
```

> **Note:** Proxies are **not** supported for image captcha — passing one raises
> `ValidationException`. Proxies apply only to reCAPTCHA and Turnstile.

---

## 5. reCAPTCHA v2

`solver.recaptcha(sitekey, url)` handles reCAPTCHA v2 by default. The `sitekey` is
the `data-sitekey` attribute of the widget; `url` is the full page URL where it
appears.

```python
# Standard checkbox
result = solver.recaptcha(
    sitekey="6Le-wvkS...",
    url="https://example.com/login",
)

# Invisible reCAPTCHA v2
result = solver.recaptcha(sitekey="6Le-wvkS...", url="https://example.com", invisible=1)

# Enterprise reCAPTCHA v2
result = solver.recaptcha(sitekey="6Le-wvkS...", url="https://example.com", enterprise=1)

# Enterprise with a data-s value (SDK alias: datas)
result = solver.recaptcha(
    sitekey="6Le-wvkS...",
    url="https://example.com",
    enterprise=1,
    datas="Crb7Vs...",
)

print(result["code"])   # g-recaptcha-response token
```

Do **not** pass `version`, `action`, or `min_score` to a v2 solve — those belong
to v3 and will raise `ValidationException`.

---

## 6. reCAPTCHA v3

reCAPTCHA v3 is score-based. Pass `version="v3"` plus the `action` your target page
uses and, optionally, a minimum score.

```python
result = solver.recaptcha(
    sitekey="6Le-wvkS...",
    url="https://example.com",
    version="v3",
    action="submit",     # must match the action in grecaptcha.execute()
    score=0.7,           # SDK alias for min_score (0.1 – 0.9)
    enterprise=0,        # set 1 for Enterprise v3
)

print(result["code"])
```

`invisible` is a v2-only flag and is rejected for v3.

---

## 7. Cloudflare Turnstile

`solver.turnstile(sitekey, url)` solves Cloudflare Turnstile. The SDK automatically
requests the JSON response so it can return the **User-Agent** Cloudflare expects.

```python
# Standalone widget
result = solver.turnstile(sitekey="0x4AAAAAAA...", url="https://example.com")
print(result["code"])            # cf-turnstile-response token
print(result.get("userAgent"))   # present when CapSkip returns it

# With an explicit action
result = solver.turnstile(sitekey="0x4AAAAAAA...", url="https://example.com", action="login")

# Cloudflare challenge page (needs cData and chlPageData from the page)
result = solver.turnstile(
    sitekey="0x4AAAAAAA...",
    url="https://example.com",
    action="managed",
    data="your_cData_value",
    pagedata="your_chlPageData_value",
)
```

> **Important:** For challenge pages you **must** send the returned token *and* use
> `result["userAgent"]` as the `User-Agent` header when you submit it. Mismatched
> User-Agents are the most common reason a valid token gets rejected.

---

## 8. Using a proxy

Solving through the same IP you will submit from greatly improves acceptance rates
for reCAPTCHA and Turnstile. Pass the proxy as a dict with `type` and `uri`:

```python
proxy = {"type": "HTTPS", "uri": "user:pass@1.2.3.4:3128"}

result = solver.recaptcha(sitekey="...", url="https://example.com", proxy=proxy)
result = solver.turnstile(sitekey="...", url="https://example.com", proxy=proxy)
```

Supported proxy types: `HTTP`, `HTTPS`, `SOCKS5`, `SOCKS5H`. The `uri` may include
credentials (`login:password@host:port`) or be a bare `host:port`.

---

## 9. Async and concurrency

`AsyncCapSkip` has the exact same method names as `CapSkip`, but every solve method
is a coroutine. This lets you solve many captchas concurrently.

```python
import asyncio
from capskip import AsyncCapSkip

async def main():
    solver = AsyncCapSkip(host="127.0.0.1", port=8080)

    r1, r2, r3 = await asyncio.gather(
        solver.recaptcha(sitekey="...", url="https://a.com"),
        solver.recaptcha(sitekey="...", url="https://b.com", version="v3", action="submit"),
        solver.turnstile(sitekey="0x4A...", url="https://c.com"),
    )

    print(r1["code"], r2["code"], r3["code"])

asyncio.run(main())
```

Use `return_exceptions=True` in `gather` if you want one failure not to cancel the
others:

```python
results = await asyncio.gather(task1, task2, return_exceptions=True)
```

---

## 10. The manual workflow

If you want to submit now and collect the answer later, use the two low-level steps
directly.

```python
from capskip import NetworkException

# 1. Submit — returns the captcha ID immediately, without waiting.
captcha_id = solver.send(
    method="userrecaptcha",
    googlekey="6Le-wvkS...",
    pageurl="https://example.com",
)

# 2. Poll once. NetworkException means "not ready yet" — retry.
import time
while True:
    try:
        code = solver.get_result(captcha_id)
        break
    except NetworkException:
        time.sleep(5)

print(code)
```

Pass `json=1` to `get_result` to get the full dictionary (including `userAgent` for
Turnstile) instead of a plain string.

---

## 11. Return values

Every high-level solve method (`normal`, `recaptcha`, `turnstile`, `solve`) returns
a dictionary:

```python
{
    "captchaId": "12345",       # CapSkip's internal ID for this solve
    "code": "TOKEN_OR_TEXT",    # the solution: text for images, token otherwise
    "userAgent": "Mozilla/..."  # Turnstile only, when CapSkip provides it
}
```

`solver.send()` returns just the ID string. `solver.get_result()` returns the
solution string (or a dict when `json=1`).

---

## 12. Error handling

The SDK raises four exception types, all subclasses of `CapSkipError`:

| Exception | When it is raised |
|---|---|
| `ValidationException` | Invalid or unsupported parameters (e.g. proxy on image captcha) |
| `NetworkException` | CapSkip is unreachable, or the captcha is not ready yet |
| `ApiException` | CapSkip returned an error code (e.g. `ERROR_WRONG_USER_KEY`) |
| `TimeoutException` | Polling exceeded the configured timeout |

```python
from capskip import (
    CapSkip, ValidationException, NetworkException, ApiException, TimeoutException,
)

solver = CapSkip(host="127.0.0.1", port=8080)

try:
    result = solver.recaptcha(sitekey="...", url="https://example.com")
    print(result["code"])
except ValidationException as e:
    print("Bad parameters:", e)
except NetworkException as e:
    print("Is CapSkip running?", e)
except ApiException as e:
    print("CapSkip returned an error:", e)
except TimeoutException as e:
    print("Gave up waiting:", e)
```

You can also catch them all at once with the base class:

```python
from capskip import CapSkipError

try:
    result = solver.turnstile(sitekey="...", url="...")
except CapSkipError as e:
    print("Solve failed:", e)
```

---

## 13. End-to-end: solve and submit

A realistic flow — solve a reCAPTCHA, then submit the token to the target site
through the **same** proxy:

```python
import os
import requests
from capskip import CapSkip, CapSkipError

solver = CapSkip(
    apiKey=os.getenv("CAPSKIP_API_KEY", "capskip"),
    host="127.0.0.1",
    port=8080,
)

SITEKEY = "6Le-wvkS...your-sitekey"
LOGIN_URL = "https://example.com/login"
PROXY = {"type": "HTTP", "uri": "1.2.3.4:3128"}

try:
    solved = solver.recaptcha(sitekey=SITEKEY, url=LOGIN_URL, proxy=PROXY)
except CapSkipError as e:
    raise SystemExit(f"Could not solve captcha: {e}")

token = solved["code"]

# Submit the form using the same proxy so the IP matches.
response = requests.post(
    LOGIN_URL,
    data={
        "username": "myuser",
        "password": "mypass",
        "g-recaptcha-response": token,
    },
    proxies={"http": f"http://{PROXY['uri']}", "https": f"http://{PROXY['uri']}"},
)

print(response.status_code)
```

For Turnstile challenge pages, also set the User-Agent header:

```python
solved = solver.turnstile(sitekey="0x4A...", url=CHALLENGE_URL,
                          data="cData", pagedata="chlPageData")
headers = {"User-Agent": solved["userAgent"]}
requests.post(CHALLENGE_URL, data={"cf-turnstile-response": solved["code"]}, headers=headers)
```

---

## 14. Parameter reference

### Solve methods

| Method | Signature |
|---|---|
| Image | `normal(file, json=0)` |
| reCAPTCHA | `recaptcha(sitekey, url, version="v2", enterprise=0, **kwargs)` |
| Turnstile | `turnstile(sitekey, url, **kwargs)` |
| Manual submit | `send(**kwargs) -> id` |
| Manual poll | `get_result(id, json=0)` |

### Convenience aliases

The SDK accepts friendly names and converts them to the raw API parameters:

| SDK name | CapSkip API parameter |
|---|---|
| `url` | `pageurl` |
| `score`, `minScore` | `min_score` |
| `datas`, `data_s` | `data-s` |
| `proxy` (dict) | `proxy` + `proxytype` strings |

Anything CapSkip does not document for a given captcha type is rejected with
`ValidationException`, so typos fail fast instead of silently doing nothing.

---

## 15. Best practices

- **Keep CapSkip running.** The SDK talks to a local app; if it is not running you
  get `NetworkException`.
- **Use the token immediately.** reCAPTCHA and Turnstile tokens expire within a
  couple of minutes.
- **Match sitekey and pageurl exactly** to the page the widget loads on.
- **Solve and submit from the same IP** (same proxy) for reCAPTCHA and Turnstile.
- **Never commit secrets.** Read `CAPSKIP_API_KEY` and proxy credentials from the
  environment, not source code.
- **Tune timeouts** for slow captcha types with `recaptchaTimeout` and
  `defaultTimeout`.

---

### Where to go next

- [API Reference](API_REFERENCE.md) — every method, parameter, and endpoint
- [Getting Started](GETTING_STARTED.md) — installation walkthrough
- [Troubleshooting](TROUBLESHOOTING.md) — fixes for common errors
- [CapSkip API docs](https://capskip.com/api-docs/) — the raw HTTP API
