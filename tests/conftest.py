import base64
import itertools
import json
import struct
import threading
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

CODE = 'SOLVED_TOKEN_abc123'
USER_AGENT = 'CapSkipUA/1.0'

# ALTCHA answers are base64 of the challenge document with the winning counter
# added, so the mock has to return a real one for the token/number parsing to
# mean anything.
ALTCHA_NUMBER = 9661
ALTCHA_TOKEN = base64.b64encode(json.dumps({
    'algorithm': 'SHA-256',
    'challenge': '3dd28253be6cc0c54d95f7f98c517e68',
    'number': ALTCHA_NUMBER,
    'salt': '46d5b1c8871e5152d902ee3f?expires=1893456000',
    'signature': '4b1cf0e0be0f4e5247e50b0f9a449830',
    'took': 16.58,
}).encode()).decode()


# Capy answers are not a token: three values that together go into the target
# form. `answer` is the drag path the widget would have recorded, so the mock
# carries a realistic one -- the expansion is only meaningful against a real shape.
CAPY_SOLUTION = {
    'captchakey': 'PUZZLE_Abc1dEFghIJKLM2no34P56q7rStu8v',
    'challengekey': 'BalY2gJaI8uA2SGVOZhqBQ3V0CYSNNGP',
    'answer': '0xax8ex0xax84x0xkx7qx0x18x76x0x1ix6sx0x26x68x0x2gx5kx0x34x50x',
    'respKey': '',
}

CAPTCHAFOX_TOKEN = '177f50c25b845601e5c779cdb51b040d523e8ab69efb4d5b343e28df07d05076'
# The UA the browser actually minted the token under -- deliberately not one a
# caller could have sent, so a test can tell the two apart.
CAPTCHAFOX_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36'
)

# A v1 token: four dot-separated parts. A v2 one is a single opaque string of
# roughly six kilobytes, which shape-wise changes nothing the SDK does with it.
FRIENDLY_CAPTCHA_TOKEN = (
    'c62c4da36bbaf7f253873035832709ef.aqwpWwdbzRWKY/UQAQwwpgAAAAAAAAAAM7hBvJOzqjc=.'
    'AAAAAArcCQABAAAAxv8QAAIAAACKYRgA.AgAB'
)


def _png_bytes():
    def chunk(tag, data):
        return (struct.pack('>I', len(data)) + tag + data
                + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff))
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
    idat = chunk(b'IDAT', zlib.compress(b'\x00\xff\x00\x00'))
    iend = chunk(b'IEND', b'')
    return sig + ihdr + idat + iend


PNG = _png_bytes()


def _make_handler():
    ids = itertools.count(1)
    id_type = {}
    poll_count = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, text, ctype='text/plain'):
            body = text.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == '/image.png':
                self.send_response(200)
                self.send_header('Content-Type', 'image/png')
                self.send_header('Content-Length', str(len(PNG)))
                self.end_headers()
                self.wfile.write(PNG)
            elif parsed.path == '/res.php':
                self._res({k: v[0] for k, v in parse_qs(parsed.query).items()})
            else:
                self._send('ERROR_NOT_FOUND')

        def do_POST(self):
            if urlparse(self.path).path != '/in.php':
                self._send('ERROR_NOT_FOUND')
                return
            body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            if self.headers.get('Content-Type', '').startswith('multipart/form-data'):
                fields, key = {'method': 'post'}, 'capskip'
            else:
                fields = {k: v[0] for k, v in parse_qs(body.decode('utf-8')).items()}
                key = fields.get('key', 'capskip')

            if key == 'badkey':
                self._send('ERROR_WRONG_USER_KEY')
                return

            pageurl = fields.get('pageurl', '')
            if 'never' in pageurl:
                cid = f'never{next(ids)}'
            elif 'slow' in pageurl:
                cid = f'slow{next(ids)}'
            elif 'empty' in pageurl:
                cid = f'empty{next(ids)}'
            else:
                cid = str(next(ids))
            id_type[cid] = fields.get('method', '')
            # in.php returns JSON when the submit carried json=1, mirroring CapSkip.
            if str(fields.get('json')) == '1':
                self._send('{"status":1,"request":"' + cid + '"}', 'application/json')
            else:
                self._send('OK|' + cid)

        def _res(self, q):
            cid = q.get('id', '')
            want_json = str(q.get('json')) == '1'
            poll_count[cid] = poll_count.get(cid, 0) + 1

            # CapSkip returns an empty 200 body when no result is available yet
            # (briefly right after submit, for an unknown id, or once a solved
            # token has already been read). It must be treated as "not ready".
            if cid.startswith('empty') and poll_count[cid] < 3:
                self._send('')
                return

            not_ready = cid.startswith('never') or (
                cid.startswith('slow') and poll_count[cid] < 2)

            if not_ready:
                self._send('{"status":0,"request":"CAPCHA_NOT_READY"}'
                           if want_json else 'CAPCHA_NOT_READY',
                           'application/json' if want_json else 'text/plain')
            elif id_type.get(cid) == 'altcha':
                # CapSkip emits a superset: the legacy status/request pair plus
                # the createTask-shaped solution object.
                self._send(json.dumps({
                    'status': 1,
                    'request': ALTCHA_TOKEN,
                    'solution': {'token': ALTCHA_TOKEN, 'number': ALTCHA_NUMBER},
                }), 'application/json') if want_json else self._send(
                    'OK|' + ALTCHA_TOKEN)
            elif id_type.get(cid) == 'capy':
                # The one method whose answer is an object rather than a string:
                # json=1 puts it straight into `request`, and plain text sends it
                # as a single line of JSON after OK|.
                if want_json:
                    self._send(json.dumps({
                        'status': 1,
                        'request': CAPY_SOLUTION,
                        'solution': CAPY_SOLUTION,
                    }), 'application/json')
                else:
                    self._send('OK|' + json.dumps(CAPY_SOLUTION))
            elif id_type.get(cid) == 'captchafox':
                # The UA is the browser's own, and CapSkip reports it at the top
                # level and inside solution both.
                if want_json:
                    self._send(json.dumps({
                        'status': 1,
                        'request': CAPTCHAFOX_TOKEN,
                        'userAgent': CAPTCHAFOX_USER_AGENT,
                        'solution': {
                            'token': CAPTCHAFOX_TOKEN,
                            'userAgent': CAPTCHAFOX_USER_AGENT,
                        },
                    }), 'application/json')
                else:
                    self._send('OK|' + CAPTCHAFOX_TOKEN)
            elif id_type.get(cid) == 'friendly_captcha':
                if want_json:
                    self._send(json.dumps({
                        'status': 1,
                        'request': FRIENDLY_CAPTCHA_TOKEN,
                        'solution': {'token': FRIENDLY_CAPTCHA_TOKEN},
                    }), 'application/json')
                else:
                    self._send('OK|' + FRIENDLY_CAPTCHA_TOKEN)
            elif want_json and id_type.get(cid) == 'turnstile':
                self._send(
                    f'{{"status":1,"request":"{CODE}","useragent":"{USER_AGENT}"}}',
                    'application/json')
            elif want_json:
                self._send(f'{{"status":1,"request":"{CODE}"}}', 'application/json')
            else:
                self._send('OK|' + CODE)

    return Handler


@pytest.fixture(scope='session')
def capskip_server():
    server = ThreadingHTTPServer(('127.0.0.1', 0), _make_handler())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    yield host, port
    server.shutdown()
