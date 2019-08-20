import json

import pytest

from galaxy.unittest.mock import async_return_value


@pytest.mark.asyncio
async def test_chunked_messages(plugin, read):
    request = {
        "jsonrpc": "2.0",
        "method": "install_game",
        "params": {
            "game_id": "3"
        }
    }

    message = json.dumps(request).encode() + b"\n"
    read.side_effect = [async_return_value(message[:5]), async_return_value(message[5:]), async_return_value(b"")]
    await plugin.run()
    plugin.install_game.assert_called_with(game_id="3")


@pytest.mark.asyncio
async def test_joined_messages(plugin, read):
    requests = [
        {
            "jsonrpc": "2.0",
            "method": "install_game",
            "params": {
                "game_id": "3"
            }
        },
        {
            "jsonrpc": "2.0",
            "method": "launch_game",
            "params": {
                "game_id": "3"
            }
        }
    ]
    data = b"".join([json.dumps(request).encode() + b"\n" for request in requests])

    read.side_effect = [async_return_value(data), async_return_value(b"")]
    await plugin.run()
    plugin.install_game.assert_called_with(game_id="3")
    plugin.launch_game.assert_called_with(game_id="3")


@pytest.mark.asyncio
async def test_not_finished(plugin, read):
    request = {
        "jsonrpc": "2.0",
        "method": "install_game",
        "params": {
            "game_id": "3"
        }
    }

    message = json.dumps(request).encode() # no new line
    read.side_effect = [async_return_value(message), async_return_value(b"")]
    await plugin.run()
    plugin.install_game.assert_not_called()
