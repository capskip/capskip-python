"""Pass a DataDome challenge and fetch the page with the cookie.

DataDome answers a request it doubts with a block page (status 403, sometimes
401) instead of the site. That page carries a ``var dd={...}`` object and loads
the challenge in an iframe from geo.captcha-delivery.com: a slider under
/captcha/, or a few-second device check under /interstitial/. CapSkip passes
either and returns the ``datadome`` cookie.

The cookie belongs to one IP address and one User-Agent, so:

  * solve through the proxy your requests use (or none, if they leave from the
    machine running CapSkip), and
  * send the User-Agent CapSkip reports back with every request.

When you send no proxy and the CapSkip app has its own DataDome proxy list, it
solves through one of those and the result names it as ``proxy`` (host:port):
the cookie then only works through that proxy.

Environment:
  TARGET_URL         a page behind DataDome (default: https://www.example.com/)
  DATADOME_PROXY     optional, e.g. http://login:password@203.0.113.10:8080
  CAPSKIP_API_KEY / CAPSKIP_HOST / CAPSKIP_PORT
"""

import json
import os
import re
from urllib.parse import urlencode, urlsplit

import requests

from capskip import CapSkip

solver = CapSkip(
    apiKey=os.getenv('CAPSKIP_API_KEY', 'capskip'),
    host=os.getenv('CAPSKIP_HOST', '127.0.0.1'),
    port=int(os.getenv('CAPSKIP_PORT', '8080')),
)

PAGE_URL = os.getenv('TARGET_URL', 'https://www.example.com/')
PROXY = os.getenv('DATADOME_PROXY')  # scheme://[login:password@]host:port, or unset


def captcha_url_from_block_page(html, page_url):
    """The challenge iframe address, as the block page's own script builds it."""
    iframe = re.search(r'<iframe[^>]+src="(https://[^"]*captcha-delivery\.com/[^"]+)"', html)
    if iframe:
        return iframe.group(1)  # HTML-escaped &amp; is fine, CapSkip decodes it
    match = re.search(r'var dd=(\{[^}]*\})', html)
    if not match:
        return None
    dd = json.loads(match.group(1).replace("'", '"'))
    path = 'interstitial' if dd.get('rt') == 'i' else 'captcha'
    query = {'initialCid': dd['cid'], 'hash': dd['hsh'], 'cid': dd['cookie']}
    if dd.get('t'):
        query['t'] = dd['t']
    query['referer'] = page_url
    query['s'] = dd['s']
    for key in ('e', 'b'):
        if dd.get(key):
            query[key] = dd[key]
    query['dm'] = 'cd'
    return f"https://{dd.get('host', 'geo.captcha-delivery.com')}/{path}/?{urlencode(query)}"


session = requests.Session()
if PROXY:
    session.proxies = {'http': PROXY, 'https': PROXY}

# 1. Request the page. A 403/401 with a dd object is DataDome's block page.
response = session.get(PAGE_URL, timeout=30)
captcha_url = captcha_url_from_block_page(response.text, PAGE_URL)
if response.status_code not in (401, 403) or not captcha_url:
    print(f'No DataDome block page at {PAGE_URL} (HTTP {response.status_code}).')
    raise SystemExit(0)
print('Block page:', captcha_url[:90] + '...')

# 2. Solve it. 2Captcha's argument order: datadome(captcha_url, pageurl, userAgent, proxy).
#    No userAgent: CapSkip uses its own browser's and reports it. With one, it
#    must be Chrome for Windows with the same major version as that browser.
proxy = None
if PROXY:
    parts = urlsplit(PROXY)
    proxy = {'type': (parts.scheme or 'http').upper(), 'uri': PROXY.split('://', 1)[-1]}
result = solver.datadome(captcha_url, PAGE_URL, proxy=proxy)

print('Captcha ID:', result['captchaId'])
print('Cookie:    ', result['cookie'][:60] + '...')
print('User-Agent:', result['userAgent'])
if result.get('proxy'):
    print('Proxy:     ', result['proxy'], '(from the CapSkip app DataDome list; the cookie only works through it)')

# 3. Repeat the request with the cookie, the same User-Agent and the same IP.
if result.get('proxy') and not PROXY:
    # Named without its login: add yours if that list entry has one.
    via = 'http://' + result['proxy']
    session.proxies = {'http': via, 'https': via}
session.headers['User-Agent'] = result['userAgent']
# `cookie` is the datadome=... pair; `code` keeps the Domain DataDome chose.
domain = re.search(r';\s*Domain=([^;]+)', result['code'], re.I)
session.cookies.set('datadome', result['cookie'].split('=', 1)[1],
                    domain=domain.group(1).strip() if domain else urlsplit(PAGE_URL).hostname)
again = session.get(PAGE_URL, timeout=30)
print('With the cookie: HTTP', again.status_code)
