from unittest.mock import call

import pytest

from galaxy.api.consts import PresenceState
from galaxy.api.errors import BackendError
from galaxy.api.types import UserPresence
from galaxy.unittest.mock import async_return_value, skip_loop
from tests import create_message, get_messages


@pytest.mark.asyncio
async def test_get_user_presence_success(plugin, read, write):
    context = "abc"
    user_ids = ["666", "13", "42", "69", "22"]
    plugin.prepare_user_presence_context.return_value = async_return_value(context)
    request = {
        "jsonrpc": "2.0",
        "id": "11",
        "method": "start_user_presence_import",
        "params": {"user_ids": user_ids}
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"", 10)]
    plugin.get_user_presence.side_effect = [
        async_return_value(UserPresence(
            PresenceState.Unknown,
            "game-id1",
            None,
            "unknown state",
            None
        )),
        async_return_value(UserPresence(
            PresenceState.Offline,
            None,
            None,
            "Going to grandma's house",
            None
        )),
        async_return_value(UserPresence(
            PresenceState.Online,
            "game-id3",
            "game-title3",
            "Pew pew",
            None
        )),
        async_return_value(UserPresence(
            PresenceState.Away,
            None,
            "game-title4",
            "AFKKTHXBY",
            None
        )),
        async_return_value(UserPresence(
            PresenceState.Away,
            None,
            "game-title5",
            None,
            "Playing game-title5: In Menu"
        )),
    ]
    await plugin.run()
    plugin.get_user_presence.assert_has_calls([
        call(user_id, context) for user_id in user_ids
    ])
    plugin.user_presence_import_complete.assert_called_once_with()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "11",
            "result": None
        },
        {
            "jsonrpc": "2.0",
            "method": "user_presence_import_success",
            "params": {
                "user_id": "666",
                "presence": {
                    "presence_state": PresenceState.Unknown.value,
                    "game_id": "game-id1",
                    "in_game_status": "unknown state"
                }
            }
        },
        {
            "jsonrpc": "2.0",
            "method": "user_presence_import_success",
            "params": {
                "user_id": "13",
                "presence": {
                    "presence_state": PresenceState.Offline.value,
                    "in_game_status": "Going to grandma's house"
                }
            }
        },
        {
            "jsonrpc": "2.0",
            "method": "user_presence_import_success",
            "params": {
                "user_id": "42",
                "presence": {
                    "presence_state": PresenceState.Online.value,
                    "game_id": "game-id3",
                    "game_title": "game-title3",
                    "in_game_status": "Pew pew"
                }
            }
        },
        {
            "jsonrpc": "2.0",
            "method": "user_presence_import_success",
            "params": {
                "user_id": "69",
                "presence": {
                    "presence_state": PresenceState.Away.value,
                    "game_title": "game-title4",
                    "in_game_status": "AFKKTHXBY"
                }
            }
        },
        {
            "jsonrpc": "2.0",
            "method": "user_presence_import_success",
            "params": {
                "user_id": "22",
                "presence": {
                    "presence_state": PresenceState.Away.value,
                    "game_title": "game-title5",
                    "full_status": "Playing game-title5: In Menu"
                }
            }
        },
        {
            "jsonrpc": "2.0",
            "method": "user_presence_import_finished",
            "params": None
        }
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("exception,code,message", [
    (BackendError, 4, "Backend error"),
    (KeyError, 0, "Unknown error")
])
async def test_get_user_presence_error(exception, code, message, plugin, read, write):
    user_id = "69"
    request_id = "55"
    plugin.prepare_user_presence_context.return_value = async_return_value(None)
    request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "start_user_presence_import",
        "params": {"user_ids": [user_id]}
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"", 10)]
    plugin.get_user_presence.side_effect = exception
    await plugin.run()
    plugin.get_user_presence.assert_called()
    plugin.user_presence_import_complete.assert_called_once_with()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": None
        },
        {
            "jsonrpc": "2.0",
            "method": "user_presence_import_failure",
            "params": {
                "user_id": user_id,
                "error": {
                    "code": code,
                    "message": message
                }
            }
        },
        {
            "jsonrpc": "2.0",
            "method": "user_presence_import_finished",
            "params": None
        }
    ]


@pytest.mark.asyncio
async def test_prepare_get_user_presence_context_error(plugin, read, write):
    request_id = "31415"
    plugin.prepare_user_presence_context.side_effect = BackendError()
    request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "start_user_presence_import",
        "params": {"user_ids": ["6"]}
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"", 10)]
    await plugin.run()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": 4,
                "message": "Backend error"
            }
        }
    ]


@pytest.mark.asyncio
async def test_import_already_in_progress_error(plugin, read, write):
    plugin.prepare_user_presence_context.return_value = async_return_value(None)
    requests = [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "method": "start_user_presence_import",
            "params": {
                "user_ids": ["42"]
            }
        },
        {
            "jsonrpc": "2.0",
            "id": "4",
            "method": "start_user_presence_import",
            "params": {
                "user_ids": ["666"]
            }
        }
    ]
    read.side_effect = [
        async_return_value(create_message(requests[0])),
        async_return_value(create_message(requests[1])),
        async_return_value(b"", 10)
    ]

    await plugin.run()

    responses = get_messages(write)
    assert {
        "jsonrpc": "2.0",
        "id": "3",
        "result": None
    } in responses
    assert {
         "jsonrpc": "2.0",
         "id": "4",
         "error": {
             "code": 600,
             "message": "Import already in progress"
         }
    } in responses


@pytest.mark.asyncio
async def test_update_user_presence(plugin, write):
    plugin.update_user_presence("42", UserPresence(PresenceState.Online, "game-id", "game-title", "Pew pew"))
    await skip_loop()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "method": "user_presence_updated",
            "params": {
                "user_id": "42",
                "presence": {
                    "presence_state": PresenceState.Online.value,
                    "game_id": "game-id",
                    "game_title": "game-title",
                    "in_game_status": "Pew pew"
                }
            }
        }
    ]
