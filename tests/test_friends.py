import asyncio
import json

from galaxy.api.types import FriendInfo
from galaxy.api.errors import UnknownError


def test_get_friends_success(plugin, read, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "import_friends"
    }

    read.side_effect = [json.dumps(request).encode() + b"\n", b""]
    plugin.get_friends.coro.return_value = [
        FriendInfo("3", "Jan"),
        FriendInfo("5", "Ola")
    ]
    asyncio.run(plugin.run())
    plugin.get_friends.assert_called_with()
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "id": "3",
        "result": {
            "friend_info_list": [
                {"user_id": "3", "user_name": "Jan"},
                {"user_id": "5", "user_name": "Ola"}
            ]
        }
    }


def test_get_friends_failure(plugin, read, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "import_friends"
    }

    read.side_effect = [json.dumps(request).encode() + b"\n", b""]
    plugin.get_friends.coro.side_effect = UnknownError()
    asyncio.run(plugin.run())
    plugin.get_friends.assert_called_with()
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "id": "3",
        "error": {
            "code": 0,
            "message": "Unknown error",
        }
    }


def test_add_friend(plugin, write):
    friend = FriendInfo("7", "Kuba")

    async def couritine():
        plugin.add_friend(friend)

    asyncio.run(couritine())
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "method": "friend_added",
        "params": {
            "friend_info": {"user_id": "7", "user_name": "Kuba"}
        }
    }


def test_remove_friend(plugin, write):
    async def couritine():
        plugin.remove_friend("5")

    asyncio.run(couritine())
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "method": "friend_removed",
        "params": {
            "user_id": "5"
        }
    }
