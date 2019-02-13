import asyncio
import json

from galaxy.api.types import Authentication, LoginError

def test_success(plugin, readline, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "init_authentication"
    }

    readline.side_effect = [json.dumps(request), ""]
    plugin.authenticate.return_value = Authentication("132", "Zenek")
    asyncio.run(plugin.run())
    plugin.authenticate.assert_called_with()
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "id": "3",
        "result": {
            "user_id": "132",
            "user_name": "Zenek"
        }
    }

def test_failure(plugin, readline, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "init_authentication"
    }

    readline.side_effect = [json.dumps(request), ""]
    plugin.authenticate.side_effect = LoginError("step", "reason")
    asyncio.run(plugin.run())
    plugin.authenticate.assert_called_with()
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "id": "3",
        "error": {
            "code": -32003,
            "message": "Custom error",
            "data": {
                "current_step": "step",
                "reason": "reason"
            }
        }
    }

def test_stored_credentials(plugin, readline, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "init_authentication",
        "params": {
            "stored_credentials": {
                "token": "ABC"
            }
        }
    }
    readline.side_effect = [json.dumps(request), ""]
    plugin.authenticate.return_value = Authentication("132", "Zenek")
    asyncio.run(plugin.run())
    plugin.authenticate.assert_called_with(stored_credentials={"token": "ABC"})
    write.assert_called()

def test_store_credentials(plugin, write):
    credentials = {
        "token": "ABC"
    }

    async def couritine():
        plugin.store_credentials(credentials)

    asyncio.run(couritine())
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "method": "store_credentials",
        "params": credentials
    }

def test_lost_authentication(plugin, readline, write):

    async def couritine():
        plugin.lost_authentication()

    asyncio.run(couritine())
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "method": "authentication_lost",
        "params": None
    }
