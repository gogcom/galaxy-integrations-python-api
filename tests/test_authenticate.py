import pytest

from galaxy.api.types import Authentication
from galaxy.api.errors import (
    UnknownError, InvalidCredentials, NetworkError, LoggedInElsewhere, ProtocolError,
    BackendNotAvailable, BackendTimeout, BackendError, TemporaryBlocked, Banned, AccessDenied
)
from galaxy.unittest.mock import async_return_value

from tests import create_message, get_messages


@pytest.mark.asyncio
async def test_success(plugin, read, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "init_authentication"
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"")]
    plugin.authenticate.return_value = async_return_value(Authentication("132", "Zenek"))
    await plugin.run()
    plugin.authenticate.assert_called_with()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "result": {
                "user_id": "132",
                "user_name": "Zenek"
            }
        }
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("error,code,message", [
    pytest.param(UnknownError, 0, "Unknown error", id="unknown_error"),
    pytest.param(BackendNotAvailable, 2, "Backend not available", id="backend_not_available"),
    pytest.param(BackendTimeout, 3, "Backend timed out", id="backend_timeout"),
    pytest.param(BackendError, 4, "Backend error", id="backend_error"),
    pytest.param(InvalidCredentials, 100, "Invalid credentials", id="invalid_credentials"),
    pytest.param(NetworkError, 101, "Network error", id="network_error"),
    pytest.param(LoggedInElsewhere, 102, "Logged in elsewhere", id="logged_elsewhere"),
    pytest.param(ProtocolError, 103, "Protocol error", id="protocol_error"),
    pytest.param(TemporaryBlocked, 104, "Temporary blocked", id="temporary_blocked"),
    pytest.param(Banned, 105, "Banned", id="banned"),
    pytest.param(AccessDenied, 106, "Access denied", id="access_denied"),
])
async def test_failure(plugin, read, write, error, code, message):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "init_authentication"
    }

    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"")]
    plugin.authenticate.side_effect = error()
    await plugin.run()
    plugin.authenticate.assert_called_with()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "error": {
                "code": code,
                "message": message
            }
        }
    ]


@pytest.mark.asyncio
async def test_stored_credentials(plugin, read, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "init_authentication",
        "params": {
            "stored_credentials": {
                "token": "ABC"
            }
        }
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"")]
    plugin.authenticate.return_value = async_return_value(Authentication("132", "Zenek"))
    await plugin.run()
    plugin.authenticate.assert_called_with(stored_credentials={"token": "ABC"})
    write.assert_called()


@pytest.mark.asyncio
async def test_store_credentials(plugin, write):
    credentials = {
        "token": "ABC"
    }
    plugin.store_credentials(credentials)

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "method": "store_credentials",
            "params": credentials
        }
    ]


@pytest.mark.asyncio
async def test_lost_authentication(plugin, write):
    plugin.lost_authentication()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "method": "authentication_lost",
            "params": None
        }
    ]
