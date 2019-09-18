import pytest

from galaxy.api.types import LocalGame
from galaxy.api.consts import LocalGameState
from galaxy.api.errors import UnknownError, FailedParsingManifest
from galaxy.unittest.mock import async_return_value

from tests import create_message, get_messages


@pytest.mark.asyncio
async def test_success(plugin, read, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "import_local_games"
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"", 10)]

    plugin.get_local_games.return_value = async_return_value([
        LocalGame("1", LocalGameState.Running),
        LocalGame("2", LocalGameState.Installed),
        LocalGame("3", LocalGameState.Installed | LocalGameState.Running)
    ])
    await plugin.run()
    plugin.get_local_games.assert_called_with()

    assert get_messages(write) == [
        {
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
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error,code,message",
    [
        pytest.param(UnknownError, 0, "Unknown error", id="unknown_error"),
        pytest.param(FailedParsingManifest, 200, "Failed parsing manifest", id="failed_parsing")
    ],
)
async def test_failure(plugin, read, write, error, code, message):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "import_local_games"
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"", 10)]
    plugin.get_local_games.side_effect = error()
    await plugin.run()
    plugin.get_local_games.assert_called_with()

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
async def test_local_game_state_update(plugin, write):
    game = LocalGame("1", LocalGameState.Running)
    plugin.update_local_game_status(game)

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "method": "local_game_status_changed",
            "params": {
                "local_game": {
                    "game_id": "1",
                    "local_game_state": LocalGameState.Running.value
                }
            }
        }
    ]
