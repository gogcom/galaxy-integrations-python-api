"""
This module standarize http traffic and the error handling for further communication with the GOG Galaxy 2.0.

It is recommended to use provided convenient methods for HTTP requests, especially when dealing with authorized sessions.
Examplary simple web service could looks like:

    .. code-block:: python

        import logging
        from galaxy.http import create_client_session, handle_exception

        class BackendClient:
            AUTH_URL = 'my-integration.com/auth'
            HEADERS = {
                "My-Custom-Header": "true",
            }
            def __init__(self):
                self._session = create_client_session(headers=self.HEADERS)

            async def authenticate(self):
                await self._session.request('POST', self.AUTH_URL)

            async def close(self):
                # to be called on plugin shutdown
                await self._session.close()

            async def _authorized_request(self, method, url, *args, **kwargs):
                with handle_exceptions():
                    return await self._session.request(method, url, *args, **kwargs)
"""

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


#: Default limit of the simultaneous connections for ssl connector.
DEFAULT_LIMIT = 20
#: Default timeout in seconds used for client session.
DEFAULT_TIMEOUT = 60


class HttpClient:
    """
    .. deprecated:: 0.41
      Use http module functions instead
    """
    def __init__(self, limit=DEFAULT_LIMIT, timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT), cookie_jar=None):
        connector = create_tcp_connector(limit=limit)
        self._session = create_client_session(connector=connector, timeout=timeout, cookie_jar=cookie_jar)

    async def close(self):
        """Closes connection. Should be called in :meth:`~galaxy.api.plugin.Plugin.shutdown`"""
        await self._session.close()

    async def request(self, method, url, *args, **kwargs):
        with handle_exception():
            return await self._session.request(method, url, *args, **kwargs)


def create_tcp_connector(*args, **kwargs) -> aiohttp.TCPConnector:
    """
    Creates TCP connector with resonable defaults.
    For details about available parameters refer to
    `aiohttp.TCPConnector <https://docs.aiohttp.org/en/stable/client_reference.html#tcpconnector>`_
    """
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.load_verify_locations(certifi.where())
    kwargs.setdefault("ssl", ssl_context)
    kwargs.setdefault("limit", DEFAULT_LIMIT)
    return aiohttp.TCPConnector(*args, **kwargs)  # type: ignore due to https://github.com/python/mypy/issues/4001


def create_client_session(*args, **kwargs) -> aiohttp.ClientSession:
    """
    Creates client session with resonable defaults.
    For details about available parameters refer to
    `aiohttp.ClientSession <https://docs.aiohttp.org/en/stable/client_reference.html>`_

    Examplary customization:

    .. code-block:: python

        from galaxy.http import create_client_session, create_tcp_connector

        session = create_client_session(
            headers={
                "Keep-Alive": "true"
            },
            connector=create_tcp_connector(limit=40),
            timeout=100)
    """
    kwargs.setdefault("connector", create_tcp_connector())
    kwargs.setdefault("timeout", aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT))
    kwargs.setdefault("raise_for_status", True)
    return aiohttp.ClientSession(*args, **kwargs)  # type: ignore due to https://github.com/python/mypy/issues/4001


@contextmanager
def handle_exception():
    """
    Context manager translating network related exceptions
    to custom :mod:`~galaxy.api.errors`.
    """
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
