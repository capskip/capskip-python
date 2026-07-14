import os

from capskip import CapSkip

solver = CapSkip(
    apiKey=os.getenv('CAPSKIP_API_KEY', 'capskip'),
    host=os.getenv('CAPSKIP_HOST', '127.0.0.1'),
    port=int(os.getenv('CAPSKIP_PORT', '8080')),
)

# Sample captcha image shipped alongside this script — resolved relative to the
# file so it works no matter which directory you run from.
IMAGE = os.path.join(os.path.dirname(__file__), 'captcha.png')

result = solver.normal(IMAGE)

print('Captcha ID:', result['captchaId'])
print('Solution:  ', result['code'])
