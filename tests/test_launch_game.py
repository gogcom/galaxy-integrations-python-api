import pytest

from galaxy.unittest.mock import async_return_value

from tests import create_message


@pytest.mark.asyncio
async def test_success(plugin, read):
    request = {
        "jsonrpc": "2.0",
        "method": "launch_game",
        "params": {
            "game_id": "3"
        }
    }

    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"")]
    await plugin.run()
    plugin.launch_game.assert_called_with(game_id="3")
