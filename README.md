# CapSkip Python SDK — Captcha Solver for Python

[![PyPI](https://img.shields.io/pypi/v/capskip.svg)](https://pypi.org/project/capskip/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://github.com/capskip/capskip-python/actions/workflows/ci.yml/badge.svg)](https://github.com/capskip/capskip-python/actions/workflows/ci.yml)

**Solve reCAPTCHA v2, reCAPTCHA v3, Cloudflare Turnstile, GeeTest, ALTCHA, Capy Puzzle, CaptchaFox, Friendly Captcha, AWS WAF, DataDome, hCaptcha and image captchas from Python.**

Official Python client for [CapSkip](https://capskip.com), a **local captcha solver** that runs on your own machine. Licensed once, not billed per solve.

```bash
pip install capskip
```

---

## How it works

CapSkip is a desktop app. It does the solving on your machine and exposes the standard captcha-solver HTTP API — the same `in.php` / `res.php` endpoints every 2captcha-compatible client already speaks — on `127.0.0.1:8080`.

This SDK is a thin wrapper over that API, with the method names you would expect: `normal()`, `recaptcha()`, `turnstile()`, `geetest()`, `altcha()`, `capy()`, `captchafox()`, `friendly_captcha()`, `amazon_waf()`, `datadome()`, `hcaptcha()`. Nothing leaves your network, and there is no credit balance to keep an eye on.

## Supported captcha types

| Captcha | Method |
|---|---|
| **Image captcha solver** (distorted text / OCR) | `solver.normal(file)` |
| **reCAPTCHA v2 solver** (checkbox) | `solver.recaptcha(sitekey, url)` |
| **reCAPTCHA v2 invisible solver** | `solver.recaptcha(..., invisible=1)` |
| **reCAPTCHA Enterprise solver** | `solver.recaptcha(..., enterprise=1)` |
| **reCAPTCHA v3 solver** | `solver.recaptcha(..., version="v3", action="submit")` |
| reCAPTCHA v3 Enterprise | `solver.recaptcha(..., version="v3", enterprise=1)` |
| **Cloudflare Turnstile solver** (widget) | `solver.turnstile(sitekey, url)` |
| Cloudflare Turnstile (challenge page) | `solver.turnstile(..., data=..., pagedata=...)` |
| **GeeTest v3 solver** (slide puzzle) | `solver.geetest(gt, challenge, url)` |
| **ALTCHA solver** (proof-of-work) | `solver.altcha(url, challenge_url=...)` |
| **Capy Puzzle solver** (slide puzzle) | `solver.capy(sitekey, url)` |
| **CaptchaFox solver** (widget) | `solver.captchafox(sitekey, url)` |
| **Friendly Captcha solver** (proof-of-work) | `solver.friendly_captcha(sitekey, url, version="v2")` |
| **AWS WAF CAPTCHA solver** (Amazon WAF) | `solver.amazon_waf(sitekey, iv, context, url)` |
| **DataDome solver** (slider and device check) | `solver.datadome(captcha_url, pageurl)` |
| **hCaptcha solver** (checkbox, invisible and Enterprise) | `solver.hcaptcha(sitekey, url)` |

**FunCaptcha/Arkose is not supported.** hCaptcha and reCAPTCHA both put a `data-sitekey` on the widget, so tell them apart before choosing a method: `class="h-captcha"` or a `js.hcaptcha.com` script means `hcaptcha()`, `class="g-recaptcha"` means `recaptcha()`.

Point the SDK at the [live captcha demo pages](https://capskip.com/captcha-demo/) to sanity-check your setup against real widgets.

---

## Quick start (5 minutes)

### 1. Install the CapSkip captcha solver

Download and run the CapSkip desktop app — [CapSkipInstaller.msi](https://capskip.com/download/CapSkipInstaller.msi). Leave it running in the background.

In CapSkip settings, note:

- **API port** (default: `8080`)
- **API key** (optional — if validation is disabled, any string works)

### 2. Install the SDK

```bash
pip install capskip
```

Or from source:

```bash
git clone https://github.com/capskip/capskip-python.git
cd capskip-python
pip install -e .
```

### 3. Solve your first captcha

```python
from capskip import CapSkip

solver = CapSkip(host="127.0.0.1", port=8080)

result = solver.recaptcha(
    sitekey="YOUR_SITEKEY",
    url="https://example.com/page-with-recaptcha",
)

print(result["code"])  # g-recaptcha-response token
```

> **Prerequisite:** CapSkip must be running before you call the SDK. If you see a connection error, see [Troubleshooting](docs/TROUBLESHOOTING.md).

---

## Why solve captchas locally

Cloud captcha APIs charge per solve, which turns a retry loop into an expense and routes every page URL and sitekey you touch through someone else's queue.

CapSkip flips that around:

- **Unlimited solving** — one license, no per-captcha charge, no balance to top up
- **Runs on `127.0.0.1`** — the SDK never talks to a third-party server
- **No per-key rate limit** — throughput is whatever your machine can manage
- **Fast** — image captchas come back in well under a second; a typical reCAPTCHA v2 lands in 30–45 seconds

### Coming from 2captcha or Anti-Captcha

CapSkip answers on the same `in.php` / `res.php` endpoints, so it works as a **2captcha API alternative**: an existing integration usually needs nothing more than its host pointed at `127.0.0.1:8080`. The [migration notes](https://capskip.com/2captcha-api-alternative/) cover the details, if you would rather keep your current client library than switch to this one.

---

## Documentation

| Guide | Description |
|---|---|
| [Tutorial](docs/TUTORIAL.md) | Complete walkthrough of every captcha type, sync and async |
| [Getting Started](docs/GETTING_STARTED.md) | Full setup: CapSkip app, SDK install, first script |
| [API Reference](docs/API_REFERENCE.md) | All classes, methods, parameters, and return values |
| [Examples](examples/) | Ready-to-run scripts for every captcha type |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Connection errors, timeouts, proxy issues |
| [Contributing](CONTRIBUTING.md) | Development setup, tests, pull requests |
| [Changelog](CHANGELOG.md) | Release history |

---

## Configuration

```python
from capskip import CapSkip

solver = CapSkip(
    apiKey="capskip",        # your CapSkip API key (or any string if validation is off)
    host="127.0.0.1",        # CapSkip host
    port=8080,               # CapSkip port from app settings
    defaultTimeout=120,      # seconds — image captcha and Capy polling timeout
    recaptchaTimeout=300,    # seconds — reCAPTCHA / Turnstile / GeeTest / CaptchaFox /
                             # Friendly Captcha / AWS WAF / DataDome / hCaptcha polling timeout
                             # (ALTCHA and Capy use defaultTimeout — neither is a browser solve)
    pollingInterval=5,       # max seconds between res.php polls (starts at 0.25s, backs off to this)
)
```

Use environment variables in production:

```bash
# Linux / macOS
export CAPSKIP_API_KEY="your-key"
export CAPSKIP_HOST="127.0.0.1"
export CAPSKIP_PORT="8080"
```

```powershell
# Windows PowerShell
$env:CAPSKIP_API_KEY = "your-key"
$env:CAPSKIP_HOST = "127.0.0.1"
$env:CAPSKIP_PORT = "8080"
```

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

## Usage examples

### Image captcha

```python
result = solver.normal("captcha.png")
result = solver.normal("https://example.com/captcha.jpg")
result = solver.normal("data:image/png;base64,iVBORw0KGgo...")
print(result["code"])
```

### reCAPTCHA v2 / v3

```python
# reCAPTCHA v2
result = solver.recaptcha(sitekey="...", url="https://example.com")

# reCAPTCHA v3
result = solver.recaptcha(
    sitekey="...",
    url="https://example.com",
    version="v3",
    action="submit",
    score=0.7,
)
```

### Cloudflare Turnstile

```python
result = solver.turnstile(
    sitekey="0x4AAAAAAA...",
    url="https://example.com",
)
```

### GeeTest v3

`gt` is static per site, but `challenge` is single-use and expires in about a
minute — fetch a fresh pair right before solving.

```python
result = solver.geetest(
    gt="81388ea1fc187e0c335c0a8907ff2625",
    challenge="7cf6a8b1a2c34d5e6f7089abcdef0123",
    url="https://example.com/login",
)

# Post these back exactly as the site's own front-end would
result["challenge"], result["validate"], result["seccode"]
```

### ALTCHA

ALTCHA is proof-of-work, not recognition — there is nothing to read, so a solve
is deterministic and takes milliseconds. Give CapSkip the endpoint that serves
the challenge, or the challenge document itself.

```python
result = solver.altcha(
    url="https://example.com/signup",
    challenge_url="https://example.com/captcha/api/altcha/challenge",
)

# Post this back in the form field the widget uses, named `altcha`
result["token"]
```

Challenges expire fast — some sites inside two minutes — so fetch one
immediately before solving and submit the token promptly.

### Capy Puzzle

A Capy solution is not a token. It is three values that together go into the
target form, so post all three back exactly as returned.

```python
result = solver.capy(
    "PUZZLE_Abc1dEFghIJKLM2no34P56q7rStu8v",
    "https://example.com/login",
)

# capy_captchakey, capy_challengekey and capy_answer respectively
result["captchakey"], result["challengekey"], result["answer"]
```

`answer` is the drag path the widget would have recorded — submit it verbatim,
without trimming or re-encoding it. The challenge key is single-use and
short-lived, so submit promptly rather than caching the three values.

Pass `api_server=` when the widget script points somewhere other than
`https://jp.api.capy.me`. Only the `puzzle` family is solved; `version="avatar"`
is refused rather than answered with a puzzle answer the site would reject.

### CaptchaFox

```python
result = solver.captchafox(
    "sk_xtNxpk6fCdFbxh1_xJeGflSdCE9tn99G",
    "https://example.com/signup",
)

# Post this back in the form field the widget uses, named `cf-captcha-response`
result["token"]

# The UA the token was minted under — submit under this one, not your own
result.get("userAgent")
```

`url` has to be the page the widget actually runs on: CaptchaFox checks it
against the domains the key is registered for and refuses a mismatch
permanently, not intermittently.

Pass `api_server=` only when the page does not load the default widget. A page
loading the MAM package expects a `MAM_` prefixed token, and sending the wrong
source still succeeds — it just returns a token the site will not accept, which
reads as a silent verification failure rather than an error.

### Friendly Captcha

Two different protocols ship under this name and a sitekey does not tell you
which one a site uses, so say which — or send the widget script and let CapSkip
read it off the build the site actually loads.

```python
result = solver.friendly_captcha(
    "FCMGEMUD2M567T8G",
    "https://example.com/signup",
    version="v2",
)

# v1 → frc-captcha-solution, v2 → frc-captcha-response
result["token"]
```

```python
# Or let the script URL decide the version
result = solver.friendly_captcha(
    "FCMGEMUD2M567T8G",
    "https://example.com/signup",
    module_script="https://cdn.example.com/@friendlycaptcha/sdk@0.1.6/site.min.js",
)
```

Solving the wrong version returns a well-formed token the target site rejects,
with nothing to indicate the version was the problem. With neither `version` nor
a script URL, v1 is assumed. Pass `api_server="eu"` for a sitekey on the EU
data-residency tenant. A v2 token is roughly six kilobytes, so size whatever
carries it accordingly.

### AWS WAF

AWS WAF CAPTCHA is the puzzle Amazon's firewall shows when it wants proof that a
visitor is human. The arguments follow 2Captcha's `amazon_waf(sitekey, iv,
context, url)`, but only `sitekey` and `url` are required.

```python
# A challenge page: the HTTP 405 page carrying window.gokuProps
result = solver.amazon_waf(
    sitekey="AQIDAHjcYu...",          # gokuProps.key
    iv="CgAFRDIjfgAAA5yY",            # gokuProps.iv
    context="Rbp3r8fvbuhmrCqp...",    # gokuProps.context
    url="https://www.example.com/",
    challenge_script="https://3f2a9c7d41b0.edge.sdk.awswaf.com/3f2a9c7d41b0/8e51d0c7a2f4/challenge.js",
)

# A widget page: AwsWafCaptcha.renderCaptcha with an apiKey, no gokuProps
result = solver.amazon_waf(
    sitekey="Xr9kEXAMPLE...=_0_1",    # the widget's apiKey
    url="https://www.example.com/contact",
    jsapiScript="https://5b7e0a19c3d8.us-east-1.captcha-sdk.awswaf.com/5b7e0a19c3d8/jsapi.js",
)

result["captcha_voucher"], result["existing_token"]
```

`iv` and `context` travel together: send both or neither. Left out, CapSkip
reads them from `url` at solve time, which is the safer choice when your copy of
the page is more than a few minutes old. Every script URL has to be an https
URL on an awswaf.com host; anything else is refused before the request is sent.

The answer is a pair, not the cookie itself. POST it as JSON to the `voucher`
endpoint in the same folder as the page's challenge.js, and the response's
`token` is the `aws-waf-token` cookie to send with your next request:

```python
voucher_url = challenge_script.rsplit("/", 1)[0] + "/voucher"
token = requests.post(voucher_url, json={
    "captcha_voucher": result["captcha_voucher"],
    "existing_token": result["existing_token"],
}).json()["token"]
```

Exchange the pair as soon as it arrives rather than storing it for later.

### DataDome

DataDome answers a request it doubts with a block page (status 403, sometimes
401) instead of the site. CapSkip passes the challenge on that page, a slider
or a device check, and returns the `datadome` cookie that lets your requests
through. The arguments follow 2Captcha's `datadome(captcha_url, pageurl,
userAgent, proxy)`, but `userAgent` and `proxy` are optional.

```python
result = solver.datadome(
    captcha_url="https://geo.captcha-delivery.com/captcha/?initialCid=...&hash=...&cid=...&t=fe&referer=...&s=45225&e=...&dm=cd",
    pageurl="https://www.example.com/",            # the page that returned the block page
    userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36",
    proxy={"type": "HTTP", "uri": "login:password@203.0.113.10:8080"},
)

result["cookie"]     # "datadome=..." -- send it as the Cookie header
result["code"]       # the cookie exactly as DataDome set it: Max-Age, Domain, Path...
result["userAgent"]  # the User-Agent the cookie was earned with
result.get("proxy")  # set only when CapSkip picked the proxy, see below
```

`captcha_url` is the address of the challenge iframe on
`geo.captcha-delivery.com`: `/captcha/` for a slider, `/interstitial/` for a
device check. Take the iframe's `src` when the block page has one; most build it
with a script instead, so assemble it from the page's `var dd={...}` object as
the [API docs](https://capskip.com/api-docs/#datadome) show. Each block page is
a fresh challenge, so submit it soon and fetch the page again for the next task.

**The cookie belongs to one IP address and one browser.** DataDome refuses it
from any other address, or with any other User-Agent, so:

- **Send the User-Agent you will use**, or none. It must be Chrome for Windows,
  with the same major version as the browser CapSkip solves with; anything else
  (Firefox, Safari, Edge, mobile, macOS) would earn a cookie the site rejects,
  so it is refused before the request is sent, and a different Chrome major is
  refused by CapSkip with `ERROR_WRONG_USERAGENT`. Send none and CapSkip uses
  its own browser's: copy `result["userAgent"]` into your requests as it is.
- **Solve from the address you will use the cookie from.** If your requests go
  out through a proxy, pass that proxy with the task. If they come from the
  machine running CapSkip, pass none.
- **When CapSkip picks the proxy, it tells you which.** The CapSkip app has a
  DataDome proxy list of its own (Settings, Captcha types, DataDome, Configure
  Proxies). A task sent without a proxy is solved through that list, and the
  result then carries `proxy` as `host:port`: send the cookie through that
  proxy, or it will be refused. A proxy you send always takes priority over
  the list, and then no `proxy` comes back.

```python
import requests

session = requests.Session()
session.headers["User-Agent"] = result["userAgent"]
if result.get("proxy"):
    # The list's proxy, named without its login: add your credentials if it has one.
    session.proxies = {"http": f"http://{result['proxy']}", "https": f"http://{result['proxy']}"}
session.headers["Cookie"] = result["cookie"]
page = session.get("https://www.example.com/")
```

A block page whose `dd` object carries `'t':'bv'` means DataDome has banned the
address that fetched it; no solve from there can pass, so it is refused before
the request is sent. Change the address and request the page again.

### hCaptcha

hCaptcha is the checkbox widget behind many sign-up, login and checkout forms.
CapSkip passes the widget for the sitekey and page you send and returns the
token. The arguments follow 2Captcha's `hcaptcha(sitekey, url, **kwargs)`, and
invisible and Enterprise widgets use the same method.

```python
result = solver.hcaptcha(
    sitekey="a5f74b19-9e45-40e0-b45d-47ff91b7a6c2",    # data-sitekey of the widget
    url="https://accounts.hcaptcha.com/demo",          # the page the widget is on
    # invisible=1,                # for a widget with data-size="invisible"
    # data="...",                 # hCaptcha Enterprise: the rqdata the page passes to hcaptcha.setData()
    # userAgent="Mozilla/5.0 ...",# the User-Agent you will submit the form with
    # proxy={"type": "HTTP", "uri": "login:password@203.0.113.10:8080"},
)

result["token"]      # put it in h-captcha-response (and g-recaptcha-response, if present)
result["respKey"]    # the second value hCaptcha hands the widget; usually empty or unused
result["userAgent"]  # the User-Agent the token was earned with
```

The sitekey is on the widget container as `data-sitekey`, in the `sitekey`
option of `hcaptcha.render()`, or in the `sitekey=` parameter of the hCaptcha
iframe's address. An Enterprise `rqdata` value is issued for one challenge and
expires quickly, so read a fresh one for every task.

Put the token in the form's `h-captcha-response` field (and `g-recaptcha-response`,
if the form has one), or pass it to the widget's `data-callback`, and submit with
the User-Agent from the result. Tokens are single use and expire about two
minutes after they are issued, so submit each one soon.

```python
driver.execute_script("""
    document.querySelector('[name="h-captcha-response"]').value = arguments[0];
    const g = document.querySelector('[name="g-recaptcha-response"]');
    if (g) g.value = arguments[0];
""", result["token"])
```

A `userAgent` you send is used only when it matches the browser CapSkip solves
with; the result always names the one the token was actually earned with. At
volume, hCaptcha scores the network a token comes from as well as the browser,
so send a proxy with each task or configure a pool in the CapSkip app (Settings,
Captcha types, hCaptcha, Configure Proxies). If a strict site still refuses the
tokens, turn on High score mode for hCaptcha in the same settings page.

### With a proxy (every method except image captcha)

```python
# Proxy is not supported for image captcha
result = solver.recaptcha(
    sitekey="...",
    url="https://example.com",
    proxy={"type": "HTTPS", "uri": "user:pass@1.2.3.4:3128"},
)
result = solver.turnstile(
    sitekey="...",
    url="https://example.com",
    proxy={"type": "HTTP", "uri": "1.2.3.4:3128"},
)
```

### Async (parallel solving)

```python
import asyncio
from capskip import AsyncCapSkip

async def main():
    solver = AsyncCapSkip()
    r1, r2 = await asyncio.gather(
        solver.recaptcha(sitekey="...", url="https://a.com"),
        solver.turnstile(sitekey="...", url="https://b.com"),
    )
    print(r1["code"], r2["code"])

asyncio.run(main())
```

More examples: [`examples/`](examples/)

---

## Selenium, Playwright and Scrapy

The SDK hands back a token; your existing browser tooling does the driving. The shape is the same whichever you use:

1. Read the sitekey off the page (`data-sitekey`, or the widget's config object).
2. Call the matching solve method with that sitekey and the page URL.
3. Write the token into the response field and submit.

### Selenium

```python
sitekey = driver.find_element(By.CSS_SELECTOR, "[data-sitekey]").get_attribute("data-sitekey")
token = solver.recaptcha(sitekey=sitekey, url=driver.current_url)["code"]

driver.execute_script(
    "document.getElementById('g-recaptcha-response').value = arguments[0];", token
)
driver.find_element(By.CSS_SELECTOR, "form").submit()
```

### Playwright

```python
from capskip import AsyncCapSkip

solver = AsyncCapSkip()
sitekey = await page.get_attribute("[data-sitekey]", "data-sitekey")
result = await solver.recaptcha(sitekey=sitekey, url=page.url)

await page.evaluate(
    "t => document.getElementById('g-recaptcha-response').value = t", result["code"]
)
```

Scrapy and plain `requests` work the same way — solve first, then send the token as whatever form field the site expects. Longer walkthroughs: [Selenium](https://capskip.com/selenium-captcha-solver/) and [Playwright](https://capskip.com/playwright-captcha-solver/).

---

## Return value

Every solve method returns:

```python
{
    "captchaId": "12345",   # internal ID from CapSkip
    "code": "TOKEN_OR_TEXT" # solution — text for image, token for reCAPTCHA/Turnstile
    "userAgent": "..."      # Turnstile only — use when submitting challenge-page tokens
}
```

GeeTest additionally expands its answer into `challenge`, `validate`, and
`seccode`, while `code` keeps the raw JSON string. ALTCHA adds `token` (the same
string as `code`) and `number`, the counter that solved it. CaptchaFox and
Friendly Captcha add `token`, the same string as `code`. Capy expands its answer
into `captchakey`, `challengekey` and `answer` — it returns an object rather than
a token, and `code` keeps the raw answer. AWS WAF does the same with its pair,
`captcha_voucher` and `existing_token`. DataDome adds `cookie`, the
`datadome=...` pair alone, while `code` keeps the cookie with its attributes;
it also carries `userAgent`, and `proxy` when CapSkip chose the proxy.
hCaptcha adds `token`, the same string as `code`, `respKey` (always present,
empty when the widget handed out none) and `userAgent`.

---

## Error handling

```python
from capskip import CapSkip, ValidationException, NetworkException, ApiException, TimeoutException

try:
    result = solver.recaptcha(sitekey="...", url="...")
except ValidationException:
    pass  # invalid parameters
except NetworkException:
    pass  # CapSkip not running, or captcha not ready (manual polling)
except ApiException:
    pass  # API returned an error code
except TimeoutException:
    pass  # polling timeout exceeded
```

---

## FAQ

### How do I solve a captcha in Python?

Install the CapSkip desktop app, `pip install capskip`, then call the method that matches the widget — `recaptcha()`, `turnstile()`, `geetest()`, `altcha()`, `capy()`, `captchafox()`, `friendly_captcha()`, `amazon_waf()`, `datadome()`, `hcaptcha()` or `normal()`. Each one polls until CapSkip has an answer, then returns a token (a cookie for DataDome), or the recognized text in the case of an image captcha.

### Is this a free captcha solver?

The SDK itself is MIT-licensed and free. Solving needs the CapSkip app, which is bought once rather than metered per captcha, so your cost stops scaling with volume.

### Which captchas can it solve?

reCAPTCHA v2 (checkbox and invisible), reCAPTCHA v3, reCAPTCHA Enterprise, Cloudflare Turnstile, GeeTest v3, ALTCHA, Capy Puzzle, CaptchaFox, Friendly Captcha, AWS WAF (Amazon WAF), DataDome, hCaptcha (including invisible and Enterprise), and image/text captchas. Not FunCaptcha/Arkose.

### Does it work with Selenium and Playwright?

Yes — see [above](#selenium-playwright-and-scrapy). The SDK never touches a browser itself, so it drops into whatever stack you already have, Scrapy and plain `requests` included.

### Why is my reCAPTCHA v3 score low?

Google derives v3 scores from IP reputation, cookies and browsing history. A solver returns a valid token, but it cannot change how Google grades that token — `score=` is forwarded as the target you want, not a guarantee. If a site enforces a high threshold, solve through a cleaner IP using the `proxy` argument.

### Can I use it as a 2captcha alternative?

Yes. CapSkip serves the same endpoints, so you can either move to this SDK or repoint an existing 2captcha client at `127.0.0.1:8080`.

### Does the captcha have to be on a public page?

For widget captchas, yes — CapSkip loads the URL you pass it. Image captchas only need the image, and that can be a local file.

### Is asyncio supported?

`AsyncCapSkip` is a full async client. Use it with `asyncio.gather` to run several solves at once.

---

## Development

```bash
git clone https://github.com/capskip/capskip-python.git
cd capskip-python
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -e ".[dev]"
pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full development workflow.

---

## Links

- [CapSkip — local captcha solver](https://capskip.com) · [download the app](https://capskip.com/download/CapSkipInstaller.msi)
- [Captcha demo pages](https://capskip.com/captcha-demo/) — live reCAPTCHA, Turnstile, GeeTest and image widgets
- [Python captcha solver guide](https://capskip.com/python-captcha-solver/)
- [HTTP API docs](https://capskip.com/api-docs/)
- Other clients: [Node.js](https://github.com/capskip/capskip-node) · [PHP](https://github.com/capskip/capskip-php) · [.NET](https://github.com/capskip/capskip-dotnet) · [MCP server for AI agents](https://github.com/capskip/capskip-mcp)
- [PyPI package](https://pypi.org/project/capskip/) · [report an issue](https://github.com/capskip/capskip-python/issues)

---

## License

MIT — see [LICENSE](LICENSE).
