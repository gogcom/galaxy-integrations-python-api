import json

import pytest
from pytest import raises

from galaxy.api.types import Achievement
from galaxy.api.errors import BackendError
from galaxy.unittest.mock import async_return_value

from tests import create_message, get_messages


def test_initialization_no_unlock_time():
    with raises(Exception):
        Achievement(achievement_id="lvl30", achievement_name="Got level 30")


def test_initialization_no_id_nor_name():
    with raises(AssertionError):
        Achievement(unlock_time=1234567890)


@pytest.mark.asyncio
async def test_get_unlocked_achievements_success(plugin, read, write):
    plugin.prepare_achievements_context.return_value = async_return_value(5)
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "start_achievements_import",
        "params": {
            "game_ids": ["14"]
        }
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"", 10)]
    plugin.get_unlocked_achievements.return_value = async_return_value([
        Achievement(achievement_id="lvl10", unlock_time=1548421241),
        Achievement(achievement_name="Got level 20", unlock_time=1548422395),
        Achievement(achievement_id="lvl30", achievement_name="Got level 30", unlock_time=1548495633)
    ])
    await plugin.run()
    plugin.prepare_achievements_context.assert_called_with(["14"])
    plugin.get_unlocked_achievements.assert_called_with("14", 5)
    plugin.achievements_import_complete.asert_called_with()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "result": None
        },
        {
            "jsonrpc": "2.0",
            "method": "game_achievements_import_success",
            "params": {
                "game_id": "14",
                "unlocked_achievements": [
                    {
                        "achievement_id": "lvl10",
                        "unlock_time": 1548421241
                    },
                    {
                        "achievement_name": "Got level 20",
                        "unlock_time": 1548422395
                    },
                    {
                        "achievement_id": "lvl30",
                        "achievement_name": "Got level 30",
                        "unlock_time": 1548495633
                    }
                ]
            }
        },
        {
            "jsonrpc": "2.0",
            "method": "achievements_import_finished",
            "params": None
        }
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("exception,code,message", [
    (BackendError, 4, "Backend error"),
    (KeyError, 0, "Unknown error")
])
async def test_get_unlocked_achievements_error(exception, code, message, plugin, read, write):
    plugin.prepare_achievements_context.return_value = async_return_value(None)
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "start_achievements_import",
        "params": {
            "game_ids": ["14"]
        }
    }

    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"", 10)]
    plugin.get_unlocked_achievements.side_effect = exception
    await plugin.run()
    plugin.get_unlocked_achievements.assert_called()
    plugin.achievements_import_complete.asert_called_with()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "result": None
        },
        {
            "jsonrpc": "2.0",
            "method": "game_achievements_import_failure",
            "params": {
                "game_id": "14",
                "error": {
                    "code": code,
                    "message": message
                }
            }
        },
        {
            "jsonrpc": "2.0",
            "method": "achievements_import_finished",
            "params": None
        }
    ]

@pytest.mark.asyncio
async def test_prepare_get_unlocked_achievements_context_error(plugin, read, write):
    plugin.prepare_achievements_context.side_effect = BackendError()
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "start_achievements_import",
        "params": {
            "game_ids": ["14"]
        }
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"")]

    await plugin.run()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "error": {
                "code": 4,
                "message": "Backend error"
            }
        }
    ]


@pytest.mark.asyncio
async def test_import_in_progress(plugin, read, write):
    plugin.prepare_achievements_context.return_value = async_return_value(None)
    plugin.get_unlocked_achievements.return_value = async_return_value([])
    requests = [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "method": "start_achievements_import",
            "params": {
                "game_ids": ["14"]
            }
        },
        {
            "jsonrpc": "2.0",
            "id": "4",
            "method": "start_achievements_import",
            "params": {
                "game_ids": ["15"]
            }
        }
    ]
    read.side_effect = [
        async_return_value(create_message(requests[0])),
        async_return_value(create_message(requests[1])),
        async_return_value(b"")
    ]

    await plugin.run()

    messages = get_messages(write)
    assert {
        "jsonrpc": "2.0",
        "id": "3",
        "result": None
    } in messages
    assert {
        "jsonrpc": "2.0",
        "id": "4",
        "error": {
            "code": 600,
            "message": "Import already in progress"
        }
    } in messages


@pytest.mark.asyncio
async def test_unlock_achievement(plugin, write):
    achievement = Achievement(achievement_id="lvl20", unlock_time=1548422395)
    plugin.unlock_achievement("14", achievement)
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "method": "achievement_unlocked",
        "params": {
            "game_id": "14",
            "achievement": {
                "achievement_id": "lvl20",
                "unlock_time": 1548422395
            }
        }
    }
