import asyncio
import ssl
from http import HTTPStatus

import aiohttp
import certifi

from galaxy.api.errors import (
    AccessDenied, AuthenticationRequired,
    BackendTimeout, BackendNotAvailable, BackendError, NetworkError, UnknownError
)

class HttpClient:
    def __init__(self, limit=20, timeout=aiohttp.ClientTimeout(total=60)):
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.load_verify_locations(certifi.where())
        connector = aiohttp.TCPConnector(limit=limit, timeout=timeout, ssl=ssl_context)
        self._session = aiohttp.ClientSession(connector=connector)

    async def close(self):
        await self._session.close()

    async def request(self, method, *args, **kwargs):
        try:
            response = await self._session.request(method, *args, **kwargs)
        except asyncio.TimeoutError:
            raise BackendTimeout()
        except aiohttp.ClientConnectionError:
            raise NetworkError()
        except aiohttp.ServerDisconnectedError:
            raise BackendNotAvailable()
        if response.status == HTTPStatus.UNAUTHORIZED:
            raise AuthenticationRequired()
        if response.status == HTTPStatus.FORBIDDEN:
            raise AccessDenied()
        if response.status == HTTPStatus.SERVICE_UNAVAILABLE:
            raise BackendNotAvailable()
        if response.status >= 500:
            raise BackendError()
        if response.status >= 400:
            raise UnknownError()

        return response
