from unittest.mock import call

import pytest
from galaxy.api.consts import OSCompatibility
from galaxy.api.errors import BackendError
from galaxy.unittest.mock import async_return_value

from tests import create_message, get_messages


@pytest.mark.asyncio
async def test_get_os_compatibility_success(plugin, read, write):
    context = "abc"
    plugin.prepare_os_compatibility_context.return_value = async_return_value(context)
    request = {
        "jsonrpc": "2.0",
        "id": "11",
        "method": "start_os_compatibility_import",
        "params": {"game_ids": ["666", "13", "42"]}
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"", 10)]
    plugin.get_os_compatibility.side_effect = [
        async_return_value(OSCompatibility.Linux),
        async_return_value(None),
        async_return_value(OSCompatibility.Windows | OSCompatibility.MacOS),
    ]
    await plugin.run()
    plugin.get_os_compatibility.assert_has_calls([
        call("666", context),
        call("13", context),
        call("42", context),
    ])
    plugin.os_compatibility_import_complete.assert_called_once_with()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "11",
            "result": None
        },
        {
            "jsonrpc": "2.0",
            "method": "os_compatibility_import_success",
            "params": {
                "game_id": "666",
                "os_compatibility": OSCompatibility.Linux.value
            }
        },
        {
            "jsonrpc": "2.0",
            "method": "os_compatibility_import_success",
            "params": {
                "game_id": "13",
                "os_compatibility": None
            }
        },
        {
            "jsonrpc": "2.0",
            "method": "os_compatibility_import_success",
            "params": {
                "game_id": "42",
                "os_compatibility": (OSCompatibility.Windows | OSCompatibility.MacOS).value
            }
        },
        {
            "jsonrpc": "2.0",
            "method": "os_compatibility_import_finished",
            "params": None
        }
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("exception,code,message", [
    (BackendError, 4, "Backend error"),
    (KeyError, 0, "Unknown error")
])
async def test_get_os_compatibility_error(exception, code, message, plugin, read, write):
    game_id = "6"
    request_id = "55"
    plugin.prepare_os_compatibility_context.return_value = async_return_value(None)
    request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "start_os_compatibility_import",
        "params": {"game_ids": [game_id]}
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"", 10)]
    plugin.get_os_compatibility.side_effect = exception
    await plugin.run()
    plugin.get_os_compatibility.assert_called()
    plugin.os_compatibility_import_complete.assert_called_once_with()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": None
        },
        {
            "jsonrpc": "2.0",
            "method": "os_compatibility_import_failure",
            "params": {
                "game_id": game_id,
                "error": {
                    "code": code,
                    "message": message
                }
            }
        },
        {
            "jsonrpc": "2.0",
            "method": "os_compatibility_import_finished",
            "params": None
        }
    ]


@pytest.mark.asyncio
async def test_prepare_get_os_compatibility_context_error(plugin, read, write):
    request_id = "31415"
    plugin.prepare_os_compatibility_context.side_effect = BackendError()
    request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "start_os_compatibility_import",
        "params": {"game_ids": ["6"]}
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"", 10)]
    await plugin.run()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": 4,
                "message": "Backend error"
            }
        }
    ]


@pytest.mark.asyncio
async def test_import_already_in_progress_error(plugin, read, write):
    plugin.prepare_os_compatibility_context.return_value = async_return_value(None)
    requests = [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "method": "start_os_compatibility_import",
            "params": {
                "game_ids": ["42"]
            }
        },
        {
            "jsonrpc": "2.0",
            "id": "4",
            "method": "start_os_compatibility_import",
            "params": {
                "game_ids": ["666"]
            }
        }
    ]
    read.side_effect = [
        async_return_value(create_message(requests[0])),
        async_return_value(create_message(requests[1])),
        async_return_value(b"", 10)
    ]

    await plugin.run()

    responses = get_messages(write)
    assert {
        "jsonrpc": "2.0",
        "id": "3",
        "result": None
    } in responses
    assert {
        "jsonrpc": "2.0",
        "id": "4",
        "error": {
            "code": 600,
            "message": "Import already in progress"
        }
    } in responses

