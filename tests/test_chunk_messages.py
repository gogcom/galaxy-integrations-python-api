import asyncio
import json

def test_chunked_messages(plugin, read):
    request = {
        "jsonrpc": "2.0",
        "method": "install_game",
        "params": {
            "game_id": "3"
        }
    }

    message = json.dumps(request).encode() + b"\n"
    read.side_effect = [message[:5], message[5:], b""]
    plugin.get_owned_games.return_value = None
    asyncio.run(plugin.run())
    plugin.install_game.assert_called_with(game_id="3")
