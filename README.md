# CapSkip Python SDK

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://github.com/capskip/capskip-python/actions/workflows/ci.yml/badge.svg)](https://github.com/capskip/capskip-python/actions/workflows/ci.yml)

Official Python client for the [CapSkip](https://capskip.com) **local** captcha solver.

CapSkip runs on your machine and exposes a standard captcha-solver HTTP API (the familiar `in.php` / `res.php` endpoints). This SDK wraps that API with clean, familiar method names, so you can solve captchas locally — no cloud service and no per-solve API fees beyond your CapSkip license.

---

## Quick start (5 minutes)

### 1. Install CapSkip

Download and run the CapSkip desktop app from [capskip.com](https://capskip.com). Leave it running in the background.

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

## Supported captcha types

| Type | SDK method |
|---|---|
| Image CAPTCHA (distorted text) | `solver.normal(file)` |
| reCAPTCHA v2 (checkbox) | `solver.recaptcha(sitekey, url)` |
| reCAPTCHA v2 Invisible | `solver.recaptcha(..., invisible=1)` |
| reCAPTCHA v2 Enterprise | `solver.recaptcha(..., enterprise=1)` |
| reCAPTCHA v3 | `solver.recaptcha(..., version="v3")` |
| reCAPTCHA v3 Enterprise | `solver.recaptcha(..., version="v3", enterprise=1)` |
| Cloudflare Turnstile (widget) | `solver.turnstile(sitekey, url)` |
| Cloudflare Turnstile (challenge page) | `solver.turnstile(..., data=..., pagedata=...)` |

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
    defaultTimeout=120,      # seconds — image captcha polling timeout
    recaptchaTimeout=300,    # seconds — reCAPTCHA / Turnstile polling timeout
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

### With a proxy (reCAPTCHA & Turnstile only)

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

## Return value

Every solve method returns:

```python
{
    "captchaId": "12345",   # internal ID from CapSkip
    "code": "TOKEN_OR_TEXT" # solution — text for image, token for reCAPTCHA/Turnstile
    "userAgent": "..."      # Turnstile only — use when submitting challenge-page tokens
}
```

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

- [CapSkip website](https://capskip.com)
- [CapSkip API docs](https://capskip.com/api-docs/)
- [Report an issue](https://github.com/capskip/capskip-python/issues)
- [PyPI package](https://pypi.org/project/capskip/)

---

## License

MIT — see [LICENSE](LICENSE).
