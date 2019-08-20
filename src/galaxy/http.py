import asyncio
import ssl
from contextlib import contextmanager
from http import HTTPStatus

import aiohttp
import certifi
import logging

from galaxy.api.errors import (
    AccessDenied, AuthenticationRequired, BackendTimeout, BackendNotAvailable, BackendError, NetworkError,
    TooManyRequests, UnknownBackendResponse, UnknownError
)


DEFAULT_LIMIT = 20
DEFAULT_TIMEOUT = 60  # seconds


class HttpClient:
    """Deprecated"""
    def __init__(self, limit=DEFAULT_LIMIT, timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT), cookie_jar=None):
        connector = create_tcp_connector(limit=limit)
        self._session = create_client_session(connector=connector, timeout=timeout, cookie_jar=cookie_jar)

    async def close(self):
        await self._session.close()

    async def request(self, method, url, *args, **kwargs):
        with handle_exception():
            return await self._session.request(method, url, *args, **kwargs)


def create_tcp_connector(*args, **kwargs):
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.load_verify_locations(certifi.where())
    kwargs.setdefault("ssl", ssl_context)
    kwargs.setdefault("limit", DEFAULT_LIMIT)
    return aiohttp.TCPConnector(*args, **kwargs)


def create_client_session(*args, **kwargs):
    kwargs.setdefault("connector", create_tcp_connector())
    kwargs.setdefault("timeout", aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT))
    kwargs.setdefault("raise_for_status", True)
    return aiohttp.ClientSession(*args, **kwargs)


@contextmanager
def handle_exception():
    try:
        yield
    except asyncio.TimeoutError:
        raise BackendTimeout()
    except aiohttp.ServerDisconnectedError:
        raise BackendNotAvailable()
    except aiohttp.ClientConnectionError:
        raise NetworkError()
    except aiohttp.ContentTypeError:
        raise UnknownBackendResponse()
    except aiohttp.ClientResponseError as error:
        if error.status == HTTPStatus.UNAUTHORIZED:
            raise AuthenticationRequired()
        if error.status == HTTPStatus.FORBIDDEN:
            raise AccessDenied()
        if error.status == HTTPStatus.SERVICE_UNAVAILABLE:
            raise BackendNotAvailable()
        if error.status == HTTPStatus.TOO_MANY_REQUESTS:
            raise TooManyRequests()
        if error.status >= 500:
            raise BackendError()
        if error.status >= 400:
            logging.warning(
                "Got status %d while performing %s request for %s",
                error.status, error.request_info.method, str(error.request_info.url)
            )
            raise UnknownError()
    except aiohttp.ClientError:
        logging.exception("Caught exception while performing request")
        raise UnknownError()

