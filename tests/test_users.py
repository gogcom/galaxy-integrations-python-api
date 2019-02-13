import asyncio
import json

from galaxy.api.types import UserInfo, Presence
from galaxy.api.errors import UnknownError
from galaxy.api.consts import PresenceState

def test_get_friends_success(plugin, readline, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "import_friends"
    }

    readline.side_effect = [json.dumps(request), ""]
    plugin.get_friends.return_value = [
        UserInfo(
            "3",
            True,
            "Jan",
            "http://avatar1.png",
            Presence(
                PresenceState.Online,
                "123",
                "Main menu"
            )
        ),
        UserInfo(
            "5",
            True,
            "Ola",
            "http://avatar2.png",
            Presence(PresenceState.Offline)
        )
    ]
    asyncio.run(plugin.run())
    plugin.get_friends.assert_called_with()
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "id": "3",
        "result": {
            "user_info_list": [
                {
                    "user_id": "3",
                    "is_friend": True,
                    "user_name": "Jan",
                    "avatar_url": "http://avatar1.png",
                    "presence": {
                        "presence_state": "online",
                        "game_id": "123",
                        "presence_status": "Main menu"
                    }
                },
                {
                    "user_id": "5",
                    "is_friend": True,
                    "user_name": "Ola",
                    "avatar_url": "http://avatar2.png",
                    "presence": {
                        "presence_state": "offline"
                    }
                }
            ]
        }
    }

def test_get_friends_failure(plugin, readline, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "import_friends"
    }

    readline.side_effect = [json.dumps(request), ""]
    plugin.get_friends.side_effect = UnknownError()
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
    friend =  UserInfo("7", True, "Kuba", "http://avatar.png", Presence(PresenceState.Offline))

    async def couritine():
        plugin.add_friend(friend)

    asyncio.run(couritine())
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "method": "friend_added",
        "params": {
            "user_info": {
                "user_id": "7",
                "is_friend": True,
                "user_name": "Kuba",
                "avatar_url": "http://avatar.png",
                "presence": {
                    "presence_state": "offline"
                }
            }
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

def test_update_friend(plugin, write):
    friend =  UserInfo("9", True, "Anna", "http://avatar.png", Presence(PresenceState.Offline))

    async def couritine():
        plugin.update_friend(friend)

    asyncio.run(couritine())
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "method": "friend_updated",
        "params": {
            "user_info": {
                "user_id": "9",
                "is_friend": True,
                "user_name": "Anna",
                "avatar_url": "http://avatar.png",
                "presence": {
                    "presence_state": "offline"
                }
            }
        }
    }

def test_get_users_success(plugin, readline, write):
    request = {
        "jsonrpc": "2.0",
        "id": "8",
        "method": "import_user_infos",
        "params": {
            "user_id_list": ["13"]
        }
    }

    readline.side_effect = [json.dumps(request), ""]
    plugin.get_users.return_value = [
        UserInfo("5", False, "Ula", "http://avatar.png", Presence(PresenceState.Offline))
    ]
    asyncio.run(plugin.run())
    plugin.get_users.assert_called_with(user_id_list=["13"])
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "id": "8",
        "result": {
            "user_info_list": [
                {
                    "user_id": "5",
                    "is_friend": False,
                    "user_name": "Ula",
                    "avatar_url": "http://avatar.png",
                    "presence": {
                        "presence_state": "offline"
                    }
                }
            ]
        }
    }

def test_get_users_failure(plugin, readline, write):
    request = {
        "jsonrpc": "2.0",
        "id": "12",
        "method": "import_user_infos",
        "params": {
            "user_id_list": ["10", "11", "12"]
        }
    }

    readline.side_effect = [json.dumps(request), ""]
    plugin.get_users.side_effect = UnknownError()
    asyncio.run(plugin.run())
    plugin.get_users.assert_called_with(user_id_list=["10", "11", "12"])
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "id": "12",
        "error": {
            "code": 0,
            "message": "Unknown error"
        }
    }
