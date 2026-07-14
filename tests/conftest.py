import itertools
import struct
import threading
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

CODE = 'SOLVED_TOKEN_abc123'
USER_AGENT = 'CapSkipUA/1.0'


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
