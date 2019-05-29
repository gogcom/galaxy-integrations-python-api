import asyncio
import json
from unittest.mock import call

import pytest
from galaxy.api.types import GameTime
from galaxy.api.errors import UnknownError, ImportInProgress, BackendError

def test_success(plugin, readline, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "import_game_times"
    }

    readline.side_effect = [json.dumps(request), ""]
    plugin.get_game_times.coro.return_value = [
        GameTime("3", 60, 1549550504),
        GameTime("5", 10, 1549550502)
    ]
    asyncio.run(plugin.run())
    plugin.get_game_times.assert_called_with()
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "id": "3",
        "result": {
            "game_times": [
                {
                    "game_id": "3",
                    "time_played": 60,
                    "last_played_time": 1549550504
                },
                {
                    "game_id": "5",
                    "time_played": 10,
                    "last_played_time": 1549550502
                }
            ]
        }
    }

def test_failure(plugin, readline, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "import_game_times"
    }

    readline.side_effect = [json.dumps(request), ""]
    plugin.get_game_times.coro.side_effect = UnknownError()
    asyncio.run(plugin.run())
    plugin.get_game_times.assert_called_with()
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "id": "3",
        "error": {
            "code": 0,
            "message": "Unknown error",
        }
    }

def test_update_game(plugin, write):
    game_time = GameTime("3", 60, 1549550504)

    async def couritine():
        plugin.update_game_time(game_time)

    asyncio.run(couritine())
    response = json.loads(write.call_args[0][0])

    assert response == {
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

@pytest.mark.asyncio
async def test_game_time_import_success(plugin, write):
    plugin.game_time_import_success(GameTime("3", 60, 1549550504))
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "method": "game_time_import_success",
        "params": {
            "game_time": {
                "game_id": "3",
                "time_played": 60,
                "last_played_time": 1549550504
            }
        }
    }

@pytest.mark.asyncio
async def test_game_time_import_failure(plugin, write):
    plugin.game_time_import_failure("134", ImportInProgress())
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "method": "game_time_import_failure",
        "params": {
            "game_id": "134",
            "error": {
                "code": 600,
                "message": "Import already in progress"
            }
        }
    }

@pytest.mark.asyncio
async def test_game_times_import_finished(plugin, write):
    plugin.game_times_import_finished()
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "method": "game_times_import_finished",
        "params": None
    }

@pytest.mark.asyncio
async def test_start_game_times_import(plugin, write, mocker):
    game_time_import_success = mocker.patch.object(plugin, "game_time_import_success")
    game_time_import_failure = mocker.patch.object(plugin, "game_time_import_failure")
    game_times_import_finished = mocker.patch.object(plugin, "game_times_import_finished")

    game_ids = ["1", "5"]
    game_time = GameTime("1", 10, 1549550502)
    plugin.get_game_times.coro.return_value = [
        game_time
    ]
    await plugin.start_game_times_import(game_ids)

    with pytest.raises(ImportInProgress):
        await plugin.start_game_times_import(["4", "8"])

    # wait until all tasks are finished
    for _ in range(4):
        await asyncio.sleep(0)

    plugin.get_game_times.coro.assert_called_once_with()
    game_time_import_success.assert_called_once_with(game_time)
    game_time_import_failure.assert_called_once_with("5", UnknownError())
    game_times_import_finished.assert_called_once_with()

@pytest.mark.asyncio
async def test_start_game_times_import_failure(plugin, write, mocker):
    game_time_import_failure = mocker.patch.object(plugin, "game_time_import_failure")
    game_times_import_finished = mocker.patch.object(plugin, "game_times_import_finished")

    game_ids = ["1", "5"]
    error = BackendError()
    plugin.get_game_times.coro.side_effect = error

    await plugin.start_game_times_import(game_ids)

    # wait until all tasks are finished
    for _ in range(4):
        await asyncio.sleep(0)

    plugin.get_game_times.coro.assert_called_once_with()

    assert game_time_import_failure.mock_calls == [call("1", error), call("5", error)]
    game_times_import_finished.assert_called_once_with()
