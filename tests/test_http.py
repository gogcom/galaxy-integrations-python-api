import asyncio
from http import HTTPStatus

import aiohttp
import pytest
from multidict import CIMultiDict, CIMultiDictProxy
from yarl import URL

from galaxy.api.errors import (
    AccessDenied, AuthenticationRequired, BackendTimeout, BackendNotAvailable, BackendError, NetworkError,
    TooManyRequests, UnknownBackendResponse, UnknownError
)
from galaxy.http import handle_exception

request_info = aiohttp.RequestInfo(URL("http://o.pl"), "GET", CIMultiDictProxy(CIMultiDict()))

@pytest.mark.parametrize(
    "aiohttp_exception,expected_exception_type",
    [
        (asyncio.TimeoutError(), BackendTimeout),
        (aiohttp.ServerDisconnectedError(), BackendNotAvailable),
        (aiohttp.ClientConnectionError(), NetworkError),
        (aiohttp.ContentTypeError(request_info, ()), UnknownBackendResponse),
        (aiohttp.ClientResponseError(request_info, (), status=HTTPStatus.UNAUTHORIZED), AuthenticationRequired),
        (aiohttp.ClientResponseError(request_info, (), status=HTTPStatus.FORBIDDEN), AccessDenied),
        (aiohttp.ClientResponseError(request_info, (), status=HTTPStatus.SERVICE_UNAVAILABLE), BackendNotAvailable),
        (aiohttp.ClientResponseError(request_info, (), status=HTTPStatus.TOO_MANY_REQUESTS), TooManyRequests),
        (aiohttp.ClientResponseError(request_info, (), status=HTTPStatus.INTERNAL_SERVER_ERROR), BackendError),
        (aiohttp.ClientResponseError(request_info, (), status=HTTPStatus.NOT_IMPLEMENTED), BackendError),
        (aiohttp.ClientResponseError(request_info, (), status=HTTPStatus.BAD_REQUEST), UnknownError),
        (aiohttp.ClientResponseError(request_info, (), status=HTTPStatus.NOT_FOUND), UnknownError),
        (aiohttp.ClientError(), UnknownError)
    ]
)
def test_handle_exception(aiohttp_exception, expected_exception_type):
    with pytest.raises(expected_exception_type):
        with handle_exception():
            raise aiohttp_exception

