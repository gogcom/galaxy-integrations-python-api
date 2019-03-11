import asyncio
import json

import pytest

from galaxy.api.types import LocalGame
from galaxy.api.consts import LocalGameState
from galaxy.api.errors import UnknownError, FailedParsingManifest

def test_success(plugin, readline, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "import_local_games"
    }

    readline.side_effect = [json.dumps(request), ""]

    plugin.get_local_games.return_value = [
        LocalGame("1", LocalGameState.Running),
        LocalGame("2", LocalGameState.Installed),
        LocalGame("3", LocalGameState.Installed | LocalGameState.Running)
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
                    "local_game_state": LocalGameState.Running.value
                },
                {
                    "game_id": "2",
                    "local_game_state": LocalGameState.Installed.value
                },
                {
                    "game_id": "3",
                    "local_game_state": (LocalGameState.Installed | LocalGameState.Running).value
                }
            ]
        }
    }

@pytest.mark.parametrize(
    "error,code,message",
    [
        pytest.param(UnknownError, 0, "Unknown error", id="unknown_error"),
        pytest.param(FailedParsingManifest, 200, "Failed parsing manifest", id="failed_parsing")
    ],
)
def test_failure(plugin, readline, write, error, code, message):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "import_local_games"
    }

    readline.side_effect = [json.dumps(request), ""]
    plugin.get_local_games.side_effect = error()
    asyncio.run(plugin.run())
    plugin.get_local_games.assert_called_with()
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "id": "3",
        "error": {
            "code": code,
            "message": message
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
                "local_game_state": LocalGameState.Running.value
            }
        }
    }
