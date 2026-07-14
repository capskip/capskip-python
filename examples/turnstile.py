import os

from capskip import CapSkip

solver = CapSkip(
    apiKey=os.getenv('CAPSKIP_API_KEY', 'capskip'),
    host=os.getenv('CAPSKIP_HOST', '127.0.0.1'),
    port=int(os.getenv('CAPSKIP_PORT', '8080')),
)

# Cloudflare's official Turnstile test key (always passes) and demo page — safe to run as-is.
SITEKEY = '1x00000000000000000000AA'
PAGE_URL = 'https://demo.turnstile.workers.dev/'

result = solver.turnstile(sitekey=SITEKEY, url=PAGE_URL)

print('Captcha ID:', result['captchaId'])
print('Token:     ', result['code'])
print('User-Agent:', result.get('userAgent'))
