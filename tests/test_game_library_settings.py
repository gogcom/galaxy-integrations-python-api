from unittest.mock import call

import pytest
from galaxy.api.types import GameLibrarySettings
from galaxy.api.errors import BackendError
from galaxy.unittest.mock import async_return_value

from tests import create_message, get_messages


@pytest.mark.asyncio
async def test_get_game_time_success(plugin, read, write):
    plugin.prepare_game_library_settings_context.return_value = async_return_value("abc")
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "start_game_library_settings_import",
        "params": {
            "game_ids": ["3", "5", "7"]
        }
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"", 10)]
    plugin.get_game_library_settings.side_effect = [
        async_return_value(GameLibrarySettings("3", None, True)),
        async_return_value(GameLibrarySettings("5", [], False)),
        async_return_value(GameLibrarySettings("7", ["tag1", "tag2", "tag3"], None)),
    ]
    await plugin.run()
    plugin.get_game_library_settings.assert_has_calls([
        call("3", "abc"),
        call("5", "abc"),
        call("7", "abc"),
    ])
    plugin.game_library_settings_import_complete.assert_called_once_with()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "result": None
        },
        {
            "jsonrpc": "2.0",
            "method": "game_library_settings_import_success",
            "params": {
                "game_library_settings": {
                    "game_id": "3",
                    "hidden": True
                }
            }
        },
        {
            "jsonrpc": "2.0",
            "method": "game_library_settings_import_success",
            "params": {
                "game_library_settings": {
                    "game_id": "5",
                    "tags": [],
                    "hidden": False
                }
            }
        },
        {
            "jsonrpc": "2.0",
            "method": "game_library_settings_import_success",
            "params": {
                "game_library_settings": {
                    "game_id": "7",
                    "tags": ["tag1", "tag2", "tag3"]
                }
            }
        },
        {
            "jsonrpc": "2.0",
            "method": "game_library_settings_import_finished",
            "params": None
        }
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("exception,code,message", [
    (BackendError, 4, "Backend error"),
    (KeyError, 0, "Unknown error")
])
async def test_get_game_library_settings_error(exception, code, message, plugin, read, write):
    plugin.prepare_game_library_settings_context.return_value = async_return_value(None)
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "start_game_library_settings_import",
        "params": {
            "game_ids": ["6"]
        }
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"", 10)]
    plugin.get_game_library_settings.side_effect = exception
    await plugin.run()
    plugin.get_game_library_settings.assert_called()
    plugin.game_library_settings_import_complete.assert_called_once_with()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "result": None
        },
        {
            "jsonrpc": "2.0",
            "method": "game_library_settings_import_failure",
            "params": {
                "game_id": "6",
                "error": {
                    "code": code,
                    "message": message
                }
            }
        },
        {
            "jsonrpc": "2.0",
            "method": "game_library_settings_import_finished",
            "params": None
        }
    ]


@pytest.mark.asyncio
async def test_prepare_get_game_library_settings_context_error(plugin, read, write):
    plugin.prepare_game_library_settings_context.side_effect = BackendError()
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "start_game_library_settings_import",
        "params": {
            "game_ids": ["6"]
        }
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"", 10)]
    await plugin.run()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "error": {
                "code": 4,
                "message": "Backend error"
            }
        }
    ]


@pytest.mark.asyncio
async def test_import_in_progress(plugin, read, write):
    plugin.prepare_game_library_settings_context.return_value = async_return_value(None)
    requests = [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "method": "start_game_library_settings_import",
            "params": {
                "game_ids": ["6"]
            }
        },
        {
            "jsonrpc": "2.0",
            "id": "4",
            "method": "start_game_library_settings_import",
            "params": {
                "game_ids": ["7"]
            }
        }
    ]
    read.side_effect = [
        async_return_value(create_message(requests[0])),
        async_return_value(create_message(requests[1])),
        async_return_value(b"", 10)
    ]

    await plugin.run()

    messages = get_messages(write)
    assert {
        "jsonrpc": "2.0",
        "id": "3",
        "result": None
    } in messages
    assert {
        "jsonrpc": "2.0",
        "id": "4",
        "error": {
            "code": 600,
            "message": "Import already in progress"
        }
    } in messages

