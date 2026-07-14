import os

from capskip import CapSkip

solver = CapSkip(
    apiKey=os.getenv('CAPSKIP_API_KEY', 'capskip'),
    host=os.getenv('CAPSKIP_HOST', '127.0.0.1'),
    port=int(os.getenv('CAPSKIP_PORT', '8080')),
)

# Google's official reCAPTCHA v2 test key and demo page — safe to run as-is.
SITEKEY = '6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI'
PAGE_URL = 'https://www.google.com/recaptcha/api2/demo'

result = solver.recaptcha(sitekey=SITEKEY, url=PAGE_URL)

print('Captcha ID:', result['captchaId'])
print('Token:     ', result['code'])
