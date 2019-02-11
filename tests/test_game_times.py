import asyncio
import json

from galaxy.api.types import GameTime, GetGameTimeError

def test_success(plugin, readline, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "import_game_times"
    }

    readline.side_effect = [json.dumps(request), ""]
    plugin.get_game_times.return_value = [
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
    plugin.get_game_times.side_effect = GetGameTimeError("reason")
    asyncio.run(plugin.run())
    plugin.get_game_times.assert_called_with()
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "id": "3",
        "error": {
            "code": -32003,
            "message": "Custom error",
            "data": {
                "reason": "reason"
            }
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
