import pytest

from galaxy.api.plugin import Plugin
from galaxy.api.consts import Platform
from galaxy.unittest.mock import async_return_value

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
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"")]
    await plugin.run()
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
    read.side_effect = [async_return_value(create_message(request))]
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
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"")]
    await plugin.run()
    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "7",
            "result": None
        }
    ]


@pytest.mark.asyncio
async def test_tick_before_handshake(plugin, read):
    read.side_effect = [async_return_value(b"")]
    await plugin.run()
    plugin.tick.assert_not_called()


@pytest.mark.asyncio
async def test_tick_after_handshake(plugin, read):
    request = {
        "jsonrpc": "2.0",
        "id": "6",
        "method": "initialize_cache",
        "params": {"data": {}}
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"")]
    await plugin.run()
    plugin.tick.assert_called_with()
