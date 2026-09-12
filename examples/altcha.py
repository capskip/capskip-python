"""Solve an ALTCHA proof-of-work challenge.

ALTCHA is not a recognition captcha -- there is nothing to read. The site issues
a challenge and the browser must brute-force a number that satisfies it. CapSkip
does that work for you, in milliseconds.

You need the challenge, in one of two forms:

  * ``challenge_url``  - the endpoint that serves it; CapSkip fetches it for you
  * ``challenge_json`` - the challenge document itself, if you already have it

To find them, open DevTools -> Network on the target page and look for the
request the ``<altcha-widget>`` makes for its challenge (often something like
``/altcha/challenge``). The request URL is your ``challenge_url``; its JSON
response is your ``challenge_json``.

Note the widget attribute that names the endpoint changed between versions:
v1/v2 use ``challengeurl="..."``, while v3+ uses ``challenge="..."`` for both a
URL and inline data. Read the page source rather than assuming.

Challenges expire fast -- some sites inside two minutes -- so fetch one
immediately before solving and post the token promptly. An expired challenge is
rejected with a bare "verification failed" that looks exactly like a wrong
answer.

This example issues its own challenge the way a site's server would, so it runs
as-is with no third-party dependency. Swap in your target's endpoint to use it
for real.
"""

import hashlib
import json
import os
import secrets
import time

from capskip import CapSkip

solver = CapSkip(
    apiKey=os.getenv('CAPSKIP_API_KEY', 'capskip'),
    host=os.getenv('CAPSKIP_HOST', '127.0.0.1'),
    port=int(os.getenv('CAPSKIP_PORT', '8080')),
)

PAGE_URL = 'https://example.com/signup'


def issue_challenge(number=54321):
    """Mint an ALTCHA challenge, exactly as a site's own server would.

    Replace this with a fetch of your target's challenge endpoint -- or skip it
    entirely and pass ``challenge_url`` so CapSkip does the fetching.
    """
    salt = f'{secrets.token_hex(12)}?expires={int(time.time()) + 600}'
    return {
        'algorithm': 'SHA-256',
        'challenge': hashlib.sha256(f'{salt}{number}'.encode()).hexdigest(),
        'salt': salt,
        'signature': '0' * 64,
        'maxnumber': 100000,
    }


# --- Option A: you already have the challenge document -----------------------
# No network request at all: CapSkip solves it locally.
challenge = issue_challenge()

result = solver.altcha(url=PAGE_URL, challenge_json=challenge)

print('Captcha ID:', result['captchaId'])
print('Number:    ', result['number'])
print('Token:     ', result['token'][:60] + '...')

# --- Option B: let CapSkip fetch the challenge --------------------------------
# Point it at the endpoint the widget calls. Add `proxy=...` if the endpoint
# should be fetched from a particular IP -- the proxy is used only for that
# fetch, never for the solve itself.
#
#   result = solver.altcha(
#       url=PAGE_URL,
#       challenge_url='https://example.com/captcha/api/altcha/challenge',
#       proxy={'type': 'HTTP', 'uri': 'login:password@1.2.3.4:8080'},
#   )

# Post the token back in the form field the widget uses, named `altcha`:
#
#   requests.post(SIGNUP_URL, data={
#       'email': 'someone@example.com',
#       'altcha': result['token'],
#   })
#
# Do not re-encode, trim or re-order it. The token is base64 of a JSON document
# whose fields are covered by the server's HMAC signature, so any modification
# invalidates it.
print('Form field:', json.dumps({'altcha': result['token'][:60] + '...'}, indent=2))

# `code` holds the same string as `token`, which is what you forward if you are
# porting code written against another solver's API.
assert result['code'] == result['token']
