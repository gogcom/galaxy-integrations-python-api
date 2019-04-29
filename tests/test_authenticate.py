import asyncio
import json

import pytest

from galaxy.api.types import Authentication
from galaxy.api.errors import (
    UnknownError, InvalidCredentials, NetworkError, LoggedInElsewhere, ProtocolError,
    BackendNotAvailable, BackendTimeout, BackendError, TemporaryBlocked, Banned, AccessDenied,
    ParentalControlBlock, DeviceBlocked, RegionBlocked
)

def test_success(plugin, readline, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "init_authentication"
    }

    readline.side_effect = [json.dumps(request), ""]
    plugin.authenticate.coro.return_value = Authentication("132", "Zenek")
    asyncio.run(plugin.run())
    plugin.authenticate.assert_called_with()
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "id": "3",
        "result": {
            "user_id": "132",
            "user_name": "Zenek"
        }
    }

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
    pytest.param(ParentalControlBlock, 107, "Parental control block", id="parental_control_clock"),
    pytest.param(DeviceBlocked, 108, "Device blocked", id="device_blocked"),
    pytest.param(RegionBlocked, 109, "Region blocked", id="region_blocked")
])
def test_failure(plugin, readline, write, error, code, message):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "init_authentication"
    }

    readline.side_effect = [json.dumps(request), ""]
    plugin.authenticate.coro.side_effect = error()
    asyncio.run(plugin.run())
    plugin.authenticate.assert_called_with()
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "id": "3",
        "error": {
            "code": code,
            "message": message
        }
    }

def test_stored_credentials(plugin, readline, write):
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
    readline.side_effect = [json.dumps(request), ""]
    plugin.authenticate.coro.return_value = Authentication("132", "Zenek")
    asyncio.run(plugin.run())
    plugin.authenticate.assert_called_with(stored_credentials={"token": "ABC"})
    write.assert_called()

def test_store_credentials(plugin, write):
    credentials = {
        "token": "ABC"
    }

    async def couritine():
        plugin.store_credentials(credentials)

    asyncio.run(couritine())
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "method": "store_credentials",
        "params": credentials
    }

def test_lost_authentication(plugin, readline, write):

    async def couritine():
        plugin.lost_authentication()

    asyncio.run(couritine())
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "method": "authentication_lost",
        "params": None
    }
