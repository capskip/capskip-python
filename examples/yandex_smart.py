"""Solve a Yandex SmartCaptcha.

Yandex SmartCaptcha is the CAPTCHA service of Yandex Cloud, used on sign-up,
login, contact and checkout forms. The visitor ticks "I'm not a robot" or pulls a
slider, and Yandex may then ask for a challenge. When the visitor passes, the
widget writes a token into a hidden form field named ``smart-token``. CapSkip
takes the sitekey and page address and returns that token, whatever challenges
Yandex asks for on the way.

You need two values, both read off the target page:

  * ``sitekey`` - the ``data-sitekey`` of the widget's container::

        <div class="smart-captcha" data-sitekey="ysc1_HrTv0IuXWNH5JxfcWnRozoir2pTFbxsaZbrbGI4e292406f2"></div>

    Pages that render the widget from their own script pass the same key to
    ``window.smartCaptcha.render`` as ``sitekey``. Client keys usually start
    with ``ysc1_``.
  * ``url`` - the full URL of the page the widget is on. Yandex checks the
    sitekey against that domain.
"""

import os

from capskip import CapSkip

solver = CapSkip(
    apiKey=os.getenv('CAPSKIP_API_KEY', 'capskip'),
    host=os.getenv('CAPSKIP_HOST', '127.0.0.1'),
    port=int(os.getenv('CAPSKIP_PORT', '8080')),
)

# Yandex's public SmartCaptcha demo page and its sitekey.
SITEKEY = 'FEXfAbHQsToo97VidNVk3j4dC74nGW1DgdxjtNB9'
PAGE_URL = 'https://smartcaptcha.yandexcloud.net/demo'

result = solver.yandex_smart(SITEKEY, PAGE_URL)

print('Captcha ID:', result['captchaId'])
print('Token:     ', result['token'][:60] + '...')

# --- Optional parameters -------------------------------------------------------
#
#   result = solver.yandex_smart(
#       SITEKEY,
#       PAGE_URL,
#       userAgent='Mozilla/5.0 ...',        # the User-Agent to present to Yandex
#       proxy={'type': 'HTTP', 'uri': 'login:password@203.0.113.10:8080'},
#   )
#
# --- Submitting the token ------------------------------------------------------
#
# Put the token in the form's smart-token field and submit the form as the page
# would. A token is valid for five minutes and can be checked only once. With
# Selenium:
#
#   driver.execute_script(
#       "document.querySelector('input[name=\"smart-token\"]').value = arguments[0];",
#       result['token'])
