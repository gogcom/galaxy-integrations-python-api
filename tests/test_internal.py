import pytest

from galaxy.api.plugin import Plugin
from galaxy.api.consts import Platform
from galaxy.api.jsonrpc import InvalidParams
from galaxy.unittest.mock import delayed_return_value_iterable

from tests import create_message, get_messages


@pytest.mark.asyncio
async def test_get_capabilities(reader, writer, read, write):
    class PluginImpl(Plugin): #pylint: disable=abstract-method
        async def get_owned_games(self):
            pass

    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "get_capabilities"
    }
    token = "token"
    plugin = PluginImpl(Platform.Generic, "0.1", reader, writer, token)
    read.side_effect = [create_message(request), b""]
    await plugin.run()
    await plugin.wait_closed()
    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "result": {
                "platform_name": "generic",
                "features": [
                    "ImportOwnedGames"
                ],
                "token": token
            }
        }
    ]


@pytest.mark.asyncio
async def test_shutdown(plugin, read, write):
    request = {
        "jsonrpc": "2.0",
        "id": "5",
        "method": "shutdown"
    }
    read.side_effect = [create_message(request)]
    await plugin.run()
    await plugin.wait_closed()
    plugin.shutdown.assert_called_with()
    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "5",
            "result": None
        }
    ]


@pytest.mark.asyncio
async def test_ping(plugin, read, write):
    request = {
        "jsonrpc": "2.0",
        "id": "7",
        "method": "ping"
    }
    read.side_effect = [create_message(request), b""]
    await plugin.run()
    await plugin.wait_closed()
    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "7",
            "result": None
        }
    ]


@pytest.mark.asyncio
async def test_tick_before_handshake(plugin, read):
    read.side_effect = [b""]
    await plugin.run()
    await plugin.wait_closed()
    plugin.tick.assert_not_called()


@pytest.mark.asyncio
async def test_tick_after_handshake(plugin, read):
    request = {
        "jsonrpc": "2.0",
        "id": "6",
        "method": "initialize_cache",
        "params": {"data": {}}
    }
    read.side_effect = delayed_return_value_iterable([create_message(request), b""], 1)
    await plugin.run()
    await plugin.wait_closed()
    plugin.tick.assert_called_with()


@pytest.mark.asyncio
async def test_notification_invalid_params_does_not_crash(plugin, read, write):
    request = {
        "jsonrpc": "2.0",
        "method": "install_game",
        "params": {}
    }
    read.side_effect = [create_message(request), b""]

    await plugin.run()
    await plugin.wait_closed()

    plugin.install_game.assert_not_called()
    assert get_messages(write) == []


@pytest.mark.asyncio
async def test_request_invalid_params_returns_error(plugin, read, write):
    request = {
        "jsonrpc": "2.0",
        "id": "8",
        "method": "start_achievements_import",
        "params": {}
    }
    read.side_effect = [create_message(request), b""]

    await plugin.run()
    await plugin.wait_closed()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "8",
            "error": InvalidParams().json()
        }
    ]
