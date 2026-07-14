# Contributing to CapSkip Python SDK

Thank you for helping improve the CapSkip Python SDK. This document explains how to set up your environment, run tests, and submit changes.

---

## Prerequisites

- Python 3.10 or newer
- Git
- CapSkip desktop app (for integration testing against a live instance)

---

## Development setup

```bash
# Clone the repository
git clone https://github.com/capskip/capskip-python.git
cd capskip-python

# Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

---

## Running tests

Unit tests mock the HTTP layer — CapSkip does not need to be running.

```bash
# Run all tests
pytest

# Verbose output
pytest -v

# With coverage
pytest --cov=capskip --cov-report=term-missing
```

### Test structure

| File | Description |
|---|---|
| `tests/abstract.py` | Sync mock `ApiClient` + `AbstractTest` base class |
| `tests/abstract_async.py` | Async mock + helpers |
| `tests/test_*.py` | Per-captcha-type unit tests (mocked HTTP) |
| `tests/conftest.py` | Local mock CapSkip server fixture |
| `tests/test_integration.py` | End-to-end tests driving the real HTTP layer |

Unit tests verify that SDK methods send the correct parameters to the CapSkip API.
Integration tests spin up a local mock server and exercise the full submit/poll
round trip — no CapSkip app or network access required.

---

## Code style

- Match the existing code style in `capskip/`
- Keep changes focused — one feature or fix per pull request
- Add or update tests for any behavior change
- Update documentation in `docs/` and `README.md` when adding features

---

## Pull request process

1. Fork the repository and create a feature branch:

   ```bash
   git checkout -b feature/my-improvement
   ```

2. Make your changes and ensure tests pass:

   ```bash
   pytest
   ```

3. Update `CHANGELOG.md` under `[Unreleased]` if applicable.

4. Push and open a pull request against `main`.

5. Fill in the pull request template completely.

---

## Reporting bugs

Use the [Bug Report issue template](.github/ISSUE_TEMPLATE/bug_report.yml) and include:

- Python version
- SDK version
- CapSkip port and captcha type
- Minimal reproduction steps
- Full traceback (redact secrets)

---

## Feature requests

CapSkip only supports: **image captcha**, **reCAPTCHA v2/v3**, and **Cloudflare Turnstile**.

Before requesting a new captcha type, confirm it is supported by [CapSkip API docs](https://capskip.com/api-docs/). Use the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.yml) for SDK improvements.

---

## Project structure

```
capskip/              # Package source
docs/                 # Documentation
examples/             # Runnable example scripts
tests/                # Unit tests
.github/              # GitHub Actions and templates
```

---

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
