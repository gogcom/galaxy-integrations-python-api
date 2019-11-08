from unittest.mock import call

import pytest
from galaxy.api.types import GameTime
from galaxy.api.errors import BackendError
from galaxy.unittest.mock import async_return_value, skip_loop

from tests import create_message, get_messages


@pytest.mark.asyncio
async def test_get_game_time_success(plugin, read, write):
    plugin.prepare_game_times_context.return_value = async_return_value("abc")
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "start_game_times_import",
        "params": {
            "game_ids": ["3", "5", "7"]
        }
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"", 10)]
    plugin.get_game_time.side_effect = [
        async_return_value(GameTime("3", 60, 1549550504)),
        async_return_value(GameTime("5", 10, None)),
        async_return_value(GameTime("7", None, 1549550502)),
    ]
    await plugin.run()
    plugin.get_game_time.assert_has_calls([
        call("3", "abc"),
        call("5", "abc"),
        call("7", "abc"),
    ])
    plugin.game_times_import_complete.assert_called_once_with()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "result": None
        },
        {
            "jsonrpc": "2.0",
            "method": "game_time_import_success",
            "params": {
                "game_time": {
                    "game_id": "3",
                    "last_played_time": 1549550504,
                    "time_played": 60
                }
            }
        },
        {
            "jsonrpc": "2.0",
            "method": "game_time_import_success",
            "params": {
                "game_time": {
                    "game_id": "5",
                    "time_played": 10
                }
            }
        },
        {
            "jsonrpc": "2.0",
            "method": "game_time_import_success",
            "params": {
                "game_time": {
                    "game_id": "7",
                    "last_played_time": 1549550502
                }
            }
        },
        {
            "jsonrpc": "2.0",
            "method": "game_times_import_finished",
            "params": None
        }
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("exception,code,message", [
    (BackendError, 4, "Backend error"),
    (KeyError, 0, "Unknown error")
])
async def test_get_game_time_error(exception, code, message, plugin, read, write):
    plugin.prepare_game_times_context.return_value = async_return_value(None)
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "start_game_times_import",
        "params": {
            "game_ids": ["6"]
        }
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"", 10)]
    plugin.get_game_time.side_effect = exception
    await plugin.run()
    plugin.get_game_time.assert_called()
    plugin.game_times_import_complete.assert_called_once_with()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "result": None
        },
        {
            "jsonrpc": "2.0",
            "method": "game_time_import_failure",
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
            "method": "game_times_import_finished",
            "params": None
        }
    ]


@pytest.mark.asyncio
async def test_prepare_get_game_time_context_error(plugin, read, write):
    plugin.prepare_game_times_context.side_effect = BackendError()
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "start_game_times_import",
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
    plugin.prepare_game_times_context.return_value = async_return_value(None)
    requests = [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "method": "start_game_times_import",
            "params": {
                "game_ids": ["6"]
            }
        },
        {
            "jsonrpc": "2.0",
            "id": "4",
            "method": "start_game_times_import",
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


@pytest.mark.asyncio
async def test_update_game(plugin, write):
    game_time = GameTime("3", 60, 1549550504)
    plugin.update_game_time(game_time)
    await skip_loop()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "method": "game_time_updated",
            "params": {
                "game_time": {
                    "game_id": "3",
                    "time_played": 60,
                    "last_played_time": 1549550504
                }
            }
        }
    ]
