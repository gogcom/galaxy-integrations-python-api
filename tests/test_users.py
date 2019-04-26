import asyncio
import json

from galaxy.api.types import UserInfo, Presence
from galaxy.api.errors import UnknownError
from galaxy.api.consts import PresenceState


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
