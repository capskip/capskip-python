import asyncio
import os

from capskip import AsyncCapSkip

# Official public test keys and demo pages — safe to run as-is.
RECAPTCHA_SITEKEY = '6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI'  # Google reCAPTCHA v2 test key
RECAPTCHA_URL = 'https://www.google.com/recaptcha/api2/demo'
TURNSTILE_SITEKEY = '1x00000000000000000000AA'  # Cloudflare Turnstile test key (always passes)
TURNSTILE_URL = 'https://demo.turnstile.workers.dev/'


async def main():
    solver = AsyncCapSkip(
        apiKey=os.getenv('CAPSKIP_API_KEY', 'capskip'),
        host=os.getenv('CAPSKIP_HOST', '127.0.0.1'),
        port=int(os.getenv('CAPSKIP_PORT', '8080')),
    )

    results = await asyncio.gather(
        solver.recaptcha(sitekey=RECAPTCHA_SITEKEY, url=RECAPTCHA_URL),
        solver.recaptcha(sitekey=RECAPTCHA_SITEKEY, url=RECAPTCHA_URL, version='v3', action='submit', score=0.7),
        solver.turnstile(sitekey=TURNSTILE_SITEKEY, url=TURNSTILE_URL),
        return_exceptions=True,
    )

    for name, res in zip(('recaptcha v2', 'recaptcha v3', 'turnstile'), results):
        print(f'{name}: {res}')


if __name__ == '__main__':
    asyncio.run(main())
