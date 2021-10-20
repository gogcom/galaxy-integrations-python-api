from unittest.mock import call

import pytest
from galaxy.api.errors import FailedParsingManifest
from galaxy.unittest.mock import async_return_value

from tests import create_message, get_messages


@pytest.mark.asyncio
async def test_get_local_size_success(plugin, read, write):
    context = {'abc': 'def'}
    plugin.prepare_local_size_context.return_value = async_return_value(context)
    request = {
        "jsonrpc": "2.0",
        "id": "11",
        "method": "start_local_size_import",
        "params": {"game_ids": ["777", "13", "42"]}
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"", 10)]
    plugin.get_local_size.side_effect = [
        async_return_value(100000000000, 1),
        async_return_value(None),
        async_return_value(3333333)
    ]
    await plugin.run()
    plugin.get_local_size.assert_has_calls([
        call("777", context),
        call("13", context),
        call("42", context)
    ])
    plugin.local_size_import_complete.assert_called_once_with()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "11",
            "result": None
        },
        {
            "jsonrpc": "2.0",
            "method": "local_size_import_success",
            "params": {
                "game_id": "777",
                "local_size": 100000000000
            }
        },
        {
            "jsonrpc": "2.0",
            "method": "local_size_import_success",
            "params": {
                "game_id": "13",
                "local_size": None
            }
        },
        {
            "jsonrpc": "2.0",
            "method": "local_size_import_success",
            "params": {
                "game_id": "42",
                "local_size": 3333333
            }
        },
        {
            "jsonrpc": "2.0",
            "method": "local_size_import_finished",
            "params": None
        }
    ]

@pytest.mark.asyncio
@pytest.mark.parametrize("exception,code,message,internal_type", [
    (FailedParsingManifest, 200, "Failed parsing manifest", "FailedParsingManifest"),
    (KeyError, 0, "Unknown error", "UnknownError")
])
async def test_get_local_size_error(exception, code, message, internal_type, plugin, read, write):
    game_id = "6"
    request_id = "55"
    plugin.prepare_local_size_context.return_value = async_return_value(None)
    request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "start_local_size_import",
        "params": {"game_ids": [game_id]}
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"", 10)]
    plugin.get_local_size.side_effect = exception
    await plugin.run()
    plugin.get_local_size.assert_called()
    plugin.local_size_import_complete.assert_called_once_with()

    direct_response = {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": None
    }
    responses = get_messages(write)
    assert direct_response in responses
    responses.remove(direct_response)
    assert responses == [
        {
            "jsonrpc": "2.0",
            "method": "local_size_import_failure",
            "params": {
                "game_id": game_id,
                "error": {
                    "code": code,
                    "message": message,
                    "data": {
                        "internal_type": internal_type
                    }
                }
            }
        },
        {
            "jsonrpc": "2.0",
            "method": "local_size_import_finished",
            "params": None
        }
    ]


@pytest.mark.asyncio
async def test_prepare_get_local_size_context_error(plugin, read, write):
    request_id = "31415"
    error_details = {"Details": "Unexpected syntax"}
    error_message, error_code = FailedParsingManifest().message, FailedParsingManifest().code
    plugin.prepare_local_size_context.side_effect = FailedParsingManifest(data=error_details)
    request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "start_local_size_import",
        "params": {"game_ids": ["6"]}
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"", 10)]
    await plugin.run()
    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": error_code,
                "message": error_message,
                "data": {
                    "internal_type": "FailedParsingManifest",
                    "Details": "Unexpected syntax"
                }
            }
        }
    ]


@pytest.mark.asyncio
async def test_import_already_in_progress_error(plugin, read, write):
    plugin.prepare_local_size_context.return_value = async_return_value(None)
    plugin.get_local_size.return_value = async_return_value(100, 5)
    requests = [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "method": "start_local_size_import",
            "params": {
                "game_ids": ["42"]
            }
        },
        {
            "jsonrpc": "2.0",
            "id": "4",
            "method": "start_local_size_import",
            "params": {
                "game_ids": ["13"]
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
            "message": "Import already in progress",
            "data": {"internal_type": "ImportInProgress"}
        }
    } in responses
