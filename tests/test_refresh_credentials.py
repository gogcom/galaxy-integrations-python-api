import pytest
import asyncio

from galaxy.unittest.mock import async_return_value
from tests import create_message, get_messages
from galaxy.api.errors import (
    BackendNotAvailable, BackendTimeout, BackendError, InvalidCredentials, NetworkError, AccessDenied, UnknownError
)
from galaxy.api.jsonrpc import JsonRpcError
@pytest.mark.asyncio
async def test_refresh_credentials_success(plugin, read, write):

    run_task = asyncio.create_task(plugin.run())

    refreshed_credentials = {
        "access_token": "new_access_token"
    }

    response = {
        "jsonrpc": "2.0",
        "id": "1",
        "result": refreshed_credentials
    }
    # 2 loop iterations delay is to force sending response after request has been sent
    read.side_effect = [async_return_value(create_message(response), loop_iterations_delay=2)]

    result = await plugin.refresh_credentials({}, False)
    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "method": "refresh_credentials",
            "params": {
            },
            "id": "1"
        }
    ]

    assert result == refreshed_credentials
    await run_task

@pytest.mark.asyncio
@pytest.mark.parametrize("exception", [
    BackendNotAvailable, BackendTimeout, BackendError, InvalidCredentials, NetworkError, AccessDenied, UnknownError
])
async def test_refresh_credentials_failure(exception, plugin, read, write):

    run_task = asyncio.create_task(plugin.run())
    error = exception()
    response = {
        "jsonrpc": "2.0",
        "id": "1",
        "error": error.json()
    }

    # 2 loop iterations delay is to force sending response after request has been sent
    read.side_effect = [async_return_value(create_message(response), loop_iterations_delay=2)]

    with pytest.raises(JsonRpcError) as e:
        await plugin.refresh_credentials({}, False)

    assert error == e.value
    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "method": "refresh_credentials",
            "params": {
            },
            "id": "1"
        }
    ]

    await run_task
