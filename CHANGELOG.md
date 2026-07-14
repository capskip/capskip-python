# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-14

### Added

- Initial release of the CapSkip Python SDK
- `CapSkip` synchronous client for the local CapSkip API
- `AsyncCapSkip` asynchronous client (`httpx` + `aiofiles`)
- Image CAPTCHA solving via `normal()` (file, URL, base64, or data-URI)
- reCAPTCHA v2 / v3 solving via `recaptcha()` (invisible, enterprise, proxy)
- Cloudflare Turnstile solving via `turnstile()` (widget and challenge page)
- Turnstile automatically polls with `json=1` and returns `userAgent` when provided
- Manual workflow: `send()`, `get_result()`, `solve()`
- Adaptive result polling — starts at 0.25s and backs off (doubling) up to the
  configured `pollingInterval`, so fast solves (e.g. image captchas) return in a
  fraction of a second; `pollingInterval` also accepts sub-second (float) values
- Familiar parameter aliases (`url`→`pageurl`, `score`→`min_score`, etc.)
- Proxy support via dict format `{'type': '...', 'uri': '...'}`
- Strict per-captcha parameter validation — only documented parameters are accepted
- Exception hierarchy: `ValidationException`, `NetworkException`, `ApiException`, `TimeoutException`
- Example scripts for every supported captcha type
- Unit tests (sync + async) with a mocked API client
- Documentation: Tutorial, Getting Started, API Reference, Troubleshooting

[1.0.0]: https://github.com/capskip/capskip-python/releases/tag/v1.0.0
