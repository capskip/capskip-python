from contextlib import AsyncExitStack

import aiofiles
import httpx

from .exceptions import ApiException, NetworkException


class AsyncApiClient:
    """Async HTTP client for CapSkip in.php / res.php endpoints."""

    def __init__(self, host='127.0.0.1', port=8080):
        self.host = host
        self.port = port

    @property
    def base_url(self):
        return f'http://{self.host}:{self.port}'

    async def in_(self, files=None, **kwargs):
        files = files or {}
        url = f'{self.base_url}/in.php'
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                if files:
                    async with AsyncExitStack() as stack:
                        file_objects = {}
                        for key, path in files.items():
                            handle = await stack.enter_async_context(aiofiles.open(path, 'rb'))
                            file_objects[key] = await handle.read()
                        resp = await client.post(url, data=kwargs, files=file_objects)
                elif 'file' in kwargs:
                    path = kwargs.pop('file')
                    async with aiofiles.open(path, 'rb') as handle:
                        content = await handle.read()
                    resp = await client.post(url, data=kwargs, files={'file': content})
                else:
                    resp = await client.post(url, data=kwargs)
        except httpx.RequestError as e:
            raise NetworkException(e) from e

        if resp.status_code != 200:
            raise NetworkException(f'bad response: {resp.status_code}')

        text = resp.content.decode('utf-8')
        if 'ERROR' in text:
            raise ApiException(text)
        return text

    async def res(self, **kwargs):
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(f'{self.base_url}/res.php', params=kwargs)
        except httpx.RequestError as e:
            raise NetworkException(e) from e

        if resp.status_code != 200:
            raise NetworkException(f'bad response: {resp.status_code}')

        text = resp.content.decode('utf-8')
        if 'ERROR' in text:
            raise ApiException(text)
        return text
