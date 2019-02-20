import asyncio
import json

from galaxy.api.plugin import Plugin
from galaxy.api.consts import Platform

def test_get_capabilites(reader, writer, readline, write):
    class PluginImpl(Plugin): #pylint: disable=abstract-method
        async def get_owned_games(self):
            pass

    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "get_capabilities"
    }
    token = "token"
    plugin = PluginImpl(Platform.Generic, reader, writer, token)
    readline.side_effect = [json.dumps(request), ""]
    asyncio.run(plugin.run())
    response = json.loads(write.call_args[0][0])
    assert response == {
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

def test_shutdown(plugin, readline, write):
    request = {
        "jsonrpc": "2.0",
        "id": "5",
        "method": "shutdown"
    }
    readline.side_effect = [json.dumps(request)]
    asyncio.run(plugin.run())
    plugin.shutdown.assert_called_with()
    response = json.loads(write.call_args[0][0])
    assert response == {
        "jsonrpc": "2.0",
        "id": "5",
        "result": None
    }

def test_ping(plugin, readline, write):
    request = {
        "jsonrpc": "2.0",
        "id": "7",
        "method": "ping"
    }
    readline.side_effect = [json.dumps(request), ""]
    asyncio.run(plugin.run())
    response = json.loads(write.call_args[0][0])
    assert response == {
        "jsonrpc": "2.0",
        "id": "7",
        "result": None
    }

def test_tick(plugin, readline):
    readline.side_effect = [""]
    asyncio.run(plugin.run())
    plugin.tick.assert_called_with()
