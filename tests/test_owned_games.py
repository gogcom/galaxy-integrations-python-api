import asyncio
import json

from galaxy.api.types import Game, Dlc, LicenseInfo, GetGamesError

def test_success(plugin, readline, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "import_owned_games"
    }

    readline.side_effect = [json.dumps(request), ""]
    plugin.get_owned_games.return_value = [
        Game("3", "Doom", None, LicenseInfo("SinglePurchase", None)),
        Game(
            "5",
            "Witcher 3",
            [
                Dlc("7", "Hearts of Stone", LicenseInfo("SinglePurchase", None)),
                Dlc("8", "Temerian Armor Set", LicenseInfo("FreeToPlay", None)),
            ],
            LicenseInfo("SinglePurchase", None))
    ]
    asyncio.run(plugin.run())
    plugin.get_owned_games.assert_called_with()
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "id": "3",
        "result": {
            "owned_games": [
                {
                    "game_id": "3",
                    "game_title": "Doom",
                    "license_info": {
                        "license_type": "SinglePurchase"
                    }
                },
                {
                    "game_id": "5",
                    "game_title": "Witcher 3",
                    "dlcs": [
                        {
                            "dlc_id": "7",
                            "dlc_title": "Hearts of Stone",
                            "license_info": {
                                "license_type": "SinglePurchase"
                            }
                        },
                        {
                            "dlc_id": "8",
                            "dlc_title": "Temerian Armor Set",
                            "license_info": {
                                "license_type": "FreeToPlay"
                            }
                        }
                    ],
                    "license_info": {
                        "license_type": "SinglePurchase"
                    }
                }
            ]
        }
    }

def test_failure(plugin, readline, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "import_owned_games"
    }

    readline.side_effect = [json.dumps(request), ""]
    plugin.get_owned_games.side_effect = GetGamesError("reason")
    asyncio.run(plugin.run())
    plugin.get_owned_games.assert_called_with()
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

def test_add_game(plugin, write):
    game = Game("3", "Doom", None, LicenseInfo("SinglePurchase", None))

    async def couritine():
        plugin.add_game(game)

    asyncio.run(couritine())
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "method": "owned_game_added",
        "params": {
            "owned_game": {
                "game_id": "3",
                "game_title": "Doom",
                "license_info": {
                    "license_type": "SinglePurchase"
                }
            }
        }
    }

def test_remove_game(plugin, write):
    async def couritine():
        plugin.remove_game("5")

    asyncio.run(couritine())
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "method": "owned_game_removed",
        "params": {
            "game_id": "5"
        }
    }

def test_update_game(plugin, write):
    game = Game("3", "Doom", None, LicenseInfo("SinglePurchase", None))

    async def couritine():
        plugin.update_game(game)

    asyncio.run(couritine())
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "method": "owned_game_updated",
        "params": {
            "owned_game": {
                "game_id": "3",
                "game_title": "Doom",
                "license_info": {
                    "license_type": "SinglePurchase"
                }
            }
        }
    }
