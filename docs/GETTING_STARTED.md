# Getting Started

This guide walks you through installing CapSkip, installing the Python SDK, and running your first captcha solve.

---

## Prerequisites

| Requirement | Details |
|---|---|
| **CapSkip app** | Windows desktop app from [capskip.com](https://capskip.com) |
| **Python** | 3.10 or newer |
| **Network** | SDK talks to CapSkip on `localhost` — no internet required for the API itself |

---

## Step 1 — Install and configure CapSkip

1. Download CapSkip from [capskip.com](https://capskip.com).
2. Install and launch the application.
3. Open **Settings** and confirm:
   - **Port** — default is `8080` (remember this value)
   - **API key validation** — if enabled, copy your API key; if disabled, any string (e.g. `capskip`) is accepted

CapSkip exposes a standard captcha-solver API:

```
POST http://127.0.0.1:<port>/in.php   → submit captcha, returns OK|<id>
GET  http://127.0.0.1:<port>/res.php  → poll result, returns OK|<answer>
```

### Verify CapSkip is running

**Windows (PowerShell):**

```powershell
Invoke-WebRequest "http://127.0.0.1:8080/res.php?key=capskip&action=get&id=0" -UseBasicParsing
```

You should get a response (even an error like `ERROR_WRONG_CAPTCHA_ID` confirms the server is up).

**Linux / macOS:**

```bash
curl "http://127.0.0.1:8080/res.php?key=capskip&action=get&id=0"
```

---

## Step 2 — Install the Python SDK

### From PyPI (recommended)

```bash
pip install capskip
```

### From source (development)

```bash
git clone https://github.com/capskip/capskip-python.git
cd capskip-python
pip install -e .
```

### Verify installation

```bash
python -c "import capskip; print(capskip.__version__)"
```

Expected output: `1.0.1` (or your installed version).

### Verify CapSkip connectivity

```bash
python examples/verify_connection.py
```

If CapSkip is running, you should see `Status: OK — CapSkip is reachable`.

## Step 3 — Create a virtual environment (recommended)

```bash
python -m venv .venv
```

**Windows:**

```powershell
.venv\Scripts\activate
pip install capskip
```

**Linux / macOS:**

```bash
source .venv/bin/activate
pip install capskip
```

---

## Step 4 — Your first script

Create `solve_recaptcha.py`:

```python
import os
from capskip import CapSkip, NetworkException, TimeoutException

solver = CapSkip(
    apiKey=os.getenv("CAPSKIP_API_KEY", "capskip"),
    host=os.getenv("CAPSKIP_HOST", "127.0.0.1"),
    port=int(os.getenv("CAPSKIP_PORT", "8080")),
)

SITEKEY = "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-"  # replace with your target page sitekey
PAGE_URL = "https://example.com/login"                 # replace with your target page URL

try:
    result = solver.recaptcha(sitekey=SITEKEY, url=PAGE_URL)
    print("Captcha ID:", result["captchaId"])
    print("Token:     ", result["code"][:80], "...")
except NetworkException as e:
    print("Cannot reach CapSkip — is the app running?", e)
except TimeoutException as e:
    print("Timed out:", e)
```

Run it:

```bash
python solve_recaptcha.py
```

---

## Step 5 — Run the bundled examples

Clone the repository (if you haven't already) and run an example:

```bash
cd capskip-python
python examples/recaptcha.py
```

| Example | What it demonstrates |
|---|---|
| `image_captcha.py` | Image captcha from file, URL, or base64 |
| `recaptcha.py` | reCAPTCHA v2, v3, invisible, enterprise, proxy |
| `turnstile.py` | Cloudflare Turnstile widget and challenge page |
| `async_example.py` | Parallel async solving |
| `verify_connection.py` | Check CapSkip is running |

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `CAPSKIP_API_KEY` | `capskip` | API key sent with every request |
| `CAPSKIP_HOST` | `127.0.0.1` | CapSkip host |
| `CAPSKIP_PORT` | `8080` | CapSkip port |

Example `.env` file (load with [python-dotenv](https://pypi.org/project/python-dotenv/) if you use it):

```env
CAPSKIP_API_KEY=capskip
CAPSKIP_HOST=127.0.0.1
CAPSKIP_PORT=8080
```

---

## Next steps

- [Tutorial](TUTORIAL.md) — complete walkthrough of every captcha type
- [API Reference](API_REFERENCE.md) — all methods and parameters
- [Troubleshooting](TROUBLESHOOTING.md) — fix common errors
- [CapSkip API docs](https://capskip.com/api-docs/) — raw HTTP API reference
