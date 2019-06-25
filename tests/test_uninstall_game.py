import asyncio
import json

def test_success(plugin, read):
    request = {
        "jsonrpc": "2.0",
        "method": "uninstall_game",
        "params": {
            "game_id": "3"
        }
    }

    read.side_effect = [json.dumps(request).encode() + b"\n", b""]
    plugin.get_owned_games.return_value = None
    asyncio.run(plugin.run())
    plugin.uninstall_game.assert_called_with(game_id="3")
