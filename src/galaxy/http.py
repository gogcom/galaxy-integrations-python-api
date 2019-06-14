import asyncio
import ssl
from http import HTTPStatus

import aiohttp
import certifi
import logging

from galaxy.api.errors import (
    AccessDenied, AuthenticationRequired, BackendTimeout, BackendNotAvailable, BackendError, NetworkError,
    TooManyRequests, UnknownBackendResponse, UnknownError
)


class HttpClient:
    def __init__(self, limit=20, timeout=aiohttp.ClientTimeout(total=60), cookie_jar=None):
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.load_verify_locations(certifi.where())
        connector = aiohttp.TCPConnector(limit=limit, ssl=ssl_context)
        self._session = aiohttp.ClientSession(connector=connector, timeout=timeout, cookie_jar=cookie_jar)

    async def close(self):
        await self._session.close()

    async def request(self, method, url, *args, **kwargs):
        try:
            response = await self._session.request(method, url, *args, **kwargs)
        except asyncio.TimeoutError:
            raise BackendTimeout()
        except aiohttp.ServerDisconnectedError:
            raise BackendNotAvailable()
        except aiohttp.ClientConnectionError:
            raise NetworkError()
        except aiohttp.ContentTypeError:
            raise UnknownBackendResponse()
        except aiohttp.ClientError:
            logging.exception(
                "Caught exception while running {} request for {}".format(method, url))
            raise UnknownError()
        if response.status == HTTPStatus.UNAUTHORIZED:
            raise AuthenticationRequired()
        if response.status == HTTPStatus.FORBIDDEN:
            raise AccessDenied()
        if response.status == HTTPStatus.SERVICE_UNAVAILABLE:
            raise BackendNotAvailable()
        if response.status == HTTPStatus.TOO_MANY_REQUESTS:
            raise TooManyRequests()
        if response.status >= 500:
            raise BackendError()
        if response.status >= 400:
            logging.warning(
                "Got status {} while running {} request for {}".format(response.status, method, url))
            raise UnknownError()

        return response
