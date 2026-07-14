# Troubleshooting

Common issues when using the CapSkip Python SDK and how to fix them.

---

## Connection refused / CapSkip not reachable

**Symptom**

```
NetworkException: ...
Connection refused
Failed to establish a new connection: [WinError 10061]
```

**Cause:** CapSkip desktop app is not running, or the port is wrong.

**Fix**

1. Launch the CapSkip application.
2. Confirm the API server is enabled in Settings.
3. Match the port in your SDK config:

```python
solver = CapSkip(host="127.0.0.1", port=8080)  # use your actual port
```

4. Test with curl:

```bash
curl "http://127.0.0.1:8080/res.php?key=capskip&action=get&id=0"
```

---

## TimeoutException — captcha not solved in time

**Symptom**

```
TimeoutException: timeout 300 exceeded
```

**Cause:** CapSkip needs more time, or the captcha failed silently.

**Fix**

1. Increase the timeout:

```python
solver = CapSkip(recaptchaTimeout=600, defaultTimeout=180)
```

2. Increase poll interval slightly (CapSkip docs recommend ~5 s for reCAPTCHA):

```python
solver = CapSkip(pollingInterval=5)
```

3. Check CapSkip app logs for solve errors on that captcha type.

---

## ApiException — ERROR_WRONG_USER_KEY

**Symptom**

```
ApiException: ERROR_WRONG_USER_KEY
```

**Cause:** API key validation is enabled in CapSkip but the key is wrong.

**Fix**

1. Copy the exact API key from CapSkip Settings.
2. Pass it to the SDK:

```python
solver = CapSkip(apiKey="your-actual-key")
```

Or disable API key validation in CapSkip Settings (development only).

---

## ApiException — ERROR_BAD_PARAMETERS

**Symptom**

```
ApiException: ERROR_BAD_PARAMETERS
```

**Cause:** Missing or invalid API parameters.

**Fix**

- **reCAPTCHA:** ensure `sitekey` and `url` are correct.
- **Turnstile challenge page:** include `data` and `pagedata` if required.
- **Image captcha:** ensure the file exists or the base64 string is valid.

---

## ValidationException — File not found

**Symptom**

```
ValidationException: File not found: captcha.png
```

**Fix**

- Use an absolute path or verify the working directory.
- For base64, pass a string with no file extension and length > 50, or use a data-URI:

```python
solver.normal("data:image/png;base64,iVBORw0KGgo...")
```

---

## reCAPTCHA token rejected by target site

**Symptom:** SDK returns a token, but the website rejects it.

**Possible causes & fixes**

| Cause | Fix |
|---|---|
| Wrong `sitekey` or `pageurl` | Must match the exact page where the widget loads |
| IP mismatch | Use the same proxy for solving and submitting the form |
| Enterprise / invisible flag wrong | Set `enterprise=1` or `invisible=1` if the page uses them |
| v3 action mismatch | Pass the correct `action` from `grecaptcha.execute()` |
| Token expired | Use the token immediately after receiving it |

**Proxy example (same IP for solve and submit):**

```python
proxy = {"type": "HTTP", "uri": "1.2.3.4:3128"}
result = solver.recaptcha(sitekey="...", url="...", proxy=proxy)
# submit form using the same proxy
```

---

## Turnstile challenge page — token works but page still blocks

**Symptom:** Token received but Cloudflare still challenges.

**Fix:** For challenge pages, CapSkip returns a User-Agent that must be used when submitting the token. Enable JSON responses and read the full payload from CapSkip's API, or inspect the raw `res.php` response with `json=1`.

---

## NetworkException during manual polling

**Symptom:** `get_result()` keeps raising `NetworkException`.

**This is expected** while the captcha is still processing. Catch it and retry:

```python
import time
from capskip import NetworkException

while True:
    try:
        code = solver.get_result(captcha_id)
        break
    except NetworkException:
        time.sleep(5)
```

---

## Import errors after install

```bash
pip install --upgrade capskip
python -c "import capskip; print(capskip.__version__)"
```

For development installs:

```bash
pip install -e ".[dev]"
```

---

## Still stuck?

1. [CapSkip API docs](https://capskip.com/api-docs/)
2. [GitHub Issues](https://github.com/capskip/capskip-python/issues)
3. CapSkip support: support@capskip.com

When opening an issue, include:

- Python version (`python --version`)
- SDK version (`python -c "import capskip; print(capskip.__version__)"`)
- CapSkip port and captcha type
- Full error traceback (redact sitekeys/tokens)
