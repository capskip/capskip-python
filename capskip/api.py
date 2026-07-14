import requests

from .exceptions import ApiException, NetworkException


class ApiClient:
    """Low-level HTTP client for CapSkip in.php / res.php endpoints."""

    def __init__(self, host='127.0.0.1', port=8080):
        self.host = host
        self.port = port

    @property
    def base_url(self):
        return f'http://{self.host}:{self.port}'

    def in_(self, files=None, **kwargs):
        files = files or {}
        try:
            url = f'{self.base_url}/in.php'
            if files:
                opened = {key: open(path, 'rb') for key, path in files.items()}
                try:
                    resp = requests.post(url, data=kwargs, files=opened)
                finally:
                    for f in opened.values():
                        f.close()
            elif 'file' in kwargs:
                with open(kwargs.pop('file'), 'rb') as f:
                    resp = requests.post(url, data=kwargs, files={'file': f})
            else:
                resp = requests.post(url, data=kwargs)
        except requests.RequestException as e:
            raise NetworkException(e) from e

        if resp.status_code != 200:
            raise NetworkException(f'bad response: {resp.status_code}')

        text = resp.content.decode('utf-8')
        if 'ERROR' in text:
            raise ApiException(text)
        return text

    def res(self, **kwargs):
        try:
            resp = requests.get(f'{self.base_url}/res.php', params=kwargs)
        except requests.RequestException as e:
            raise NetworkException(e) from e

        if resp.status_code != 200:
            raise NetworkException(f'bad response: {resp.status_code}')

        text = resp.content.decode('utf-8')
        if 'ERROR' in text:
            raise ApiException(text)
        return text
