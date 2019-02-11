import asyncio
import json

from galaxy.api.types import GetLocalGamesError, LocalGame
from galaxy.api.consts import LocalGameState

def test_success(plugin, readline, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "import_local_games"
    }

    readline.side_effect = [json.dumps(request), ""]

    plugin.get_local_games.return_value = [
        LocalGame("1", "Running"),
        LocalGame("2", "Installed")
    ]
    asyncio.run(plugin.run())
    plugin.get_local_games.assert_called_with()

    response = json.loads(write.call_args[0][0])
    assert response == {
        "jsonrpc": "2.0",
        "id": "3",
        "result": {
            "local_games" : [
                {
                    "game_id": "1",
                    "local_game_state": "Running"
                },
                {
                    "game_id": "2",
                    "local_game_state": "Installed"
                }
            ]
        }
    }

def test_failure(plugin, readline, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "import_local_games"
    }

    readline.side_effect = [json.dumps(request), ""]
    plugin.get_local_games.side_effect = GetLocalGamesError("reason")
    asyncio.run(plugin.run())
    plugin.get_local_games.assert_called_with()
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

def test_local_game_state_update(plugin, write):
    game = LocalGame("1", LocalGameState.Running)

    async def couritine():
        plugin.update_local_game_status(game)

    asyncio.run(couritine())
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "method": "local_game_status_changed",
        "params": {
            "local_game": {
                "game_id": "1",
                "local_game_state": "Running"
            }
        }
    }
