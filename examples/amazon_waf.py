"""Solve an AWS WAF (Amazon WAF) CAPTCHA and turn the answer into the cookie.

AWS WAF CAPTCHA is the puzzle Amazon's firewall shows when it wants proof that a
visitor is human: usually a 3 x 3 grid of pictures, sometimes a toy car to steer
along a path. AWS WAF decides which one; CapSkip handles both.

Sites meet it in one of two shapes:

  * The challenge page. The firewall answers with HTTP 405 and a small page
    carrying ``window.gokuProps`` (key, iv, context) and loading challenge.js
    and captcha.js from an awswaf.com host.
  * The widget. An ordinary page loads jsapi.js and draws the puzzle itself
    with ``AwsWafCaptcha.renderCaptcha(..., {apiKey: ...})``.

The answer is not the cookie itself but a pair, ``captcha_voucher`` and
``existing_token``. POST it to the ``voucher`` endpoint next to challenge.js
and the response's ``token`` is the ``aws-waf-token`` cookie.
"""

import os

import requests

from capskip import CapSkip

solver = CapSkip(
    apiKey=os.getenv('CAPSKIP_API_KEY', 'capskip'),
    host=os.getenv('CAPSKIP_HOST', '127.0.0.1'),
    port=int(os.getenv('CAPSKIP_PORT', '8080')),
)

PAGE_URL = 'https://www.example.com/'

# Read these off the 405 page: window.gokuProps = {"key": ..., "iv": ..., "context": ...}
# and the src of its challenge.js script tag. iv and context change with every
# challenge page, so take fresh ones each time.
SITEKEY = 'AQIDAHjcYuEXAMPLEghicBgQ/7bFaQZ+m5FKCMDnO+vTbNg96AHDh0IR5vgzHNceHYqZR+GOAAAAfjB8'
IV = 'CgAFRDIjfgAAA5yY'
CONTEXT = 'Rbp3r8fvbuhmrCqpUe8Mh1TLvs8OSKJZiSs2vCF4dt9rxVZI7xYJa2n5k/9r+XaXe7KUIu2I8nXTDHHkDvIOTDc2'
CHALLENGE_JS = 'https://3f2a9c7d41b0.edge.sdk.awswaf.com/3f2a9c7d41b0/8e51d0c7a2f4/challenge.js'

# The argument order is 2Captcha's: amazon_waf(sitekey, iv, context, url).
result = solver.amazon_waf(SITEKEY, IV, CONTEXT, PAGE_URL, challenge_script=CHALLENGE_JS)

print('Captcha ID:     ', result['captchaId'])
print('Voucher:        ', result['captcha_voucher'][:40] + '...')
print('Existing token: ', result['existing_token'][:40] + '...')

# --- Let CapSkip read iv and context itself -----------------------------------
# Only sitekey and url are required. Whatever you leave out is read from the
# page at solve time -- the safer choice when your copy is more than a few
# minutes old. iv and context travel together: send both or neither.
#
#   result = solver.amazon_waf(SITEKEY, url=PAGE_URL)
#
# --- A widget page ------------------------------------------------------------
# No gokuProps here: send the widget's apiKey as the sitekey and the jsapi.js URL.
#
#   result = solver.amazon_waf(
#       sitekey='Xr9kEXAMPLE2bWQx1vTq8LmZ0aYc4dHs7nFp3gJt6uKw5eRi9AbCdEfGh=_0_1',
#       url='https://www.example.com/contact',
#       jsapiScript='https://5b7e0a19c3d8.us-east-1.captcha-sdk.awswaf.com/5b7e0a19c3d8/jsapi.js',
#   )
#
# --- With a per-request proxy -------------------------------------------------
# Sites behind AWS WAF usually pair the CAPTCHA with rate limits and IP
# reputation rules, so solve at volume through proxies.
#
#   result = solver.amazon_waf(
#       SITEKEY, IV, CONTEXT, PAGE_URL,
#       proxy={'type': 'HTTP', 'uri': 'login:password@1.2.3.4:8080'},
#   )


def exchange_voucher(result, challenge_js, page_origin):
    """Trade the pair for the aws-waf-token on AWS WAF's own token host.

    Do this as soon as the answer arrives rather than storing it for later.
    """
    voucher_url = challenge_js.rsplit('/', 1)[0] + '/voucher'
    response = requests.post(
        voucher_url,
        json={
            'captcha_voucher': result['captcha_voucher'],
            'existing_token': result['existing_token'],
        },
        headers={'Origin': page_origin},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()['token']


# Against a real site, finish like this -- the token goes in the aws-waf-token
# cookie (some widget pages send it in an x-aws-waf-token header instead):
#
#   token = exchange_voucher(result, CHALLENGE_JS, 'https://www.example.com')
#   page = requests.get(PAGE_URL, cookies={'aws-waf-token': token})
#   print(page.status_code)  # the real content instead of the 405 page
#
# The token stays valid for the site's immunity time, 5 minutes by default.
# When the challenge comes back, solve again.
