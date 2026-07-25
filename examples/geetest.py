"""Solve a GeeTest v3 slider.

GeeTest v3 needs two values from the target site:

  * ``gt``        - static per site
  * ``challenge`` - single-use, expires in about a minute

The site fetches them itself from an endpoint that returns
``{"gt": "...", "challenge": "..."}`` (often ``.../register.php`` or a
``gettype``/``get.php`` request). Open DevTools -> Network to find that request,
then request a *fresh* pair right before solving, as this example does.
"""

import json
import os

import requests

from capskip import CapSkip

solver = CapSkip(
    apiKey=os.getenv('CAPSKIP_API_KEY', 'capskip'),
    host=os.getenv('CAPSKIP_HOST', '127.0.0.1'),
    port=int(os.getenv('CAPSKIP_PORT', '8080')),
)

# A public GeeTest v3 demo page, and the endpoint that page calls to issue a
# fresh gt/challenge pair. Safe to run as-is.
PAGE_URL = 'https://2captcha.com/demo/geetest'
REGISTER_URL = 'https://2captcha.com/api/v1/captcha-demo/gee-test/init-params'


def fetch_challenge():
    """Get a fresh gt/challenge pair. Replace with the endpoint your target uses."""
    resp = requests.get(REGISTER_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data['gt'], data['challenge']


gt, challenge = fetch_challenge()

result = solver.geetest(gt=gt, challenge=challenge, url=PAGE_URL)

print('Captcha ID:', result['captchaId'])
print('Challenge: ', result['challenge'])
print('Validate:  ', result['validate'])
print('Seccode:   ', result['seccode'])

# `code` holds the same answer as a raw JSON string, which is what you forward
# if you are porting code written against another solver's API.
print('Raw code:  ', result['code'])

# Post these back exactly as the site's own front-end would, e.g.:
#
#   requests.post(LOGIN_URL, data={
#       'geetest_challenge': result['challenge'],
#       'geetest_validate':  result['validate'],
#       'geetest_seccode':   result['seccode'],
#   })
print('Form fields:', json.dumps({
    'geetest_challenge': result['challenge'],
    'geetest_validate': result['validate'],
    'geetest_seccode': result['seccode'],
}, indent=2))
