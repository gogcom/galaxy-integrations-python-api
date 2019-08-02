import pytest

from galaxy.api.types import Game, Dlc, LicenseInfo
from galaxy.api.consts import LicenseType
from galaxy.api.errors import UnknownError
from galaxy.unittest.mock import async_return_value

from tests import create_message, get_messages


@pytest.mark.asyncio
async def test_success(plugin, read, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "import_owned_games"
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"")]

    plugin.get_owned_games.return_value = async_return_value([
        Game("3", "Doom", None, LicenseInfo(LicenseType.SinglePurchase, None)),
        Game(
            "5",
            "Witcher 3",
            [
                Dlc("7", "Hearts of Stone", LicenseInfo(LicenseType.SinglePurchase, None)),
                Dlc("8", "Temerian Armor Set", LicenseInfo(LicenseType.FreeToPlay, None)),
            ],
            LicenseInfo(LicenseType.SinglePurchase, None))
    ])
    await plugin.run()
    plugin.get_owned_games.assert_called_with()
    assert get_messages(write) == [
        {
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
    ]


@pytest.mark.asyncio
async def test_failure(plugin, read, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "import_owned_games"
    }

    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"")]
    plugin.get_owned_games.side_effect = UnknownError()
    await plugin.run()
    plugin.get_owned_games.assert_called_with()
    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "error": {
                "code": 0,
                "message": "Unknown error"
            }
        }
    ]


@pytest.mark.asyncio
async def test_add_game(plugin, write):
    game = Game("3", "Doom", None, LicenseInfo(LicenseType.SinglePurchase, None))
    plugin.add_game(game)
    assert get_messages(write) == [
        {
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
    ]


@pytest.mark.asyncio
async def test_remove_game(plugin, write):
    plugin.remove_game("5")
    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "method": "owned_game_removed",
            "params": {
                "game_id": "5"
            }
        }
    ]


@pytest.mark.asyncio
async def test_update_game(plugin, write):
    game = Game("3", "Doom", None, LicenseInfo(LicenseType.SinglePurchase, None))
    plugin.update_game(game)
    assert get_messages(write) == [
        {
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
    ]
