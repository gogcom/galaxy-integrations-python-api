from galaxy.api.types import FriendInfo
from galaxy.api.errors import UnknownError
from galaxy.unittest.mock import async_return_value

import pytest

from tests import create_message, get_messages


@pytest.mark.asyncio
async def test_get_friends_success(plugin, read, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "import_friends"
    }

    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"")]
    plugin.get_friends.return_value = async_return_value([
        FriendInfo("3", "Jan"),
        FriendInfo("5", "Ola")
    ])
    await plugin.run()
    plugin.get_friends.assert_called_with()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "result": {
                "friend_info_list": [
                    {"user_id": "3", "user_name": "Jan"},
                    {"user_id": "5", "user_name": "Ola"}
                ]
            }
        }
    ]


@pytest.mark.asyncio
async def test_get_friends_failure(plugin, read, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "import_friends"
    }

    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"")]
    plugin.get_friends.side_effect = UnknownError()
    await plugin.run()
    plugin.get_friends.assert_called_with()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "error": {
                "code": 0,
                "message": "Unknown error",
            }
        }
    ]


@pytest.mark.asyncio
async def test_add_friend(plugin, write):
    friend = FriendInfo("7", "Kuba")

    plugin.add_friend(friend)

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "method": "friend_added",
            "params": {
                "friend_info": {"user_id": "7", "user_name": "Kuba"}
            }
        }
    ]


@pytest.mark.asyncio
async def test_remove_friend(plugin, write):
    plugin.remove_friend("5")

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "method": "friend_removed",
            "params": {
                "user_id": "5"
            }
        }
    ]
