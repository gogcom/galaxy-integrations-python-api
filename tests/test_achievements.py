import asyncio
import json
from unittest.mock import call

import pytest
from pytest import raises

from galaxy.api.types import Achievement
from galaxy.api.errors import UnknownError, ImportInProgress, BackendError

def test_initialization_no_unlock_time():
    with raises(Exception):
        Achievement(achievement_id="lvl30", achievement_name="Got level 30")

def test_initialization_no_id_nor_name():
    with raises(AssertionError):
        Achievement(unlock_time=1234567890)

def test_success(plugin, readline, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "import_unlocked_achievements",
        "params": {
            "game_id": "14"
        }
    }
    readline.side_effect = [json.dumps(request), ""]
    plugin.get_unlocked_achievements.coro.return_value = [
        Achievement(achievement_id="lvl10", unlock_time=1548421241),
        Achievement(achievement_name="Got level 20", unlock_time=1548422395),
        Achievement(achievement_id="lvl30", achievement_name="Got level 30", unlock_time=1548495633)
    ]
    asyncio.run(plugin.run())
    plugin.get_unlocked_achievements.assert_called_with(game_id="14")
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "id": "3",
        "result": {
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
    }

def test_failure(plugin, readline, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "import_unlocked_achievements",
        "params": {
            "game_id": "14"
        }
    }

    readline.side_effect = [json.dumps(request), ""]
    plugin.get_unlocked_achievements.coro.side_effect = UnknownError()
    asyncio.run(plugin.run())
    plugin.get_unlocked_achievements.assert_called()
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "id": "3",
        "error": {
            "code": 0,
            "message": "Unknown error"
        }
    }

def test_unlock_achievement(plugin, write):
    achievement = Achievement(achievement_id="lvl20", unlock_time=1548422395)

    async def couritine():
        plugin.unlock_achievement("14", achievement)

    asyncio.run(couritine())
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

@pytest.mark.asyncio
async def test_game_achievements_import_success(plugin, write):
    achievements = [
        Achievement(achievement_id="lvl10", unlock_time=1548421241),
        Achievement(achievement_name="Got level 20", unlock_time=1548422395)
    ]
    plugin.game_achievements_import_success("134", achievements)
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "method": "game_achievements_import_success",
        "params": {
            "game_id": "134",
            "unlocked_achievements": [
                {
                    "achievement_id": "lvl10",
                    "unlock_time": 1548421241
                },
                {
                    "achievement_name": "Got level 20",
                    "unlock_time": 1548422395
                }
            ]
        }
    }

@pytest.mark.asyncio
async def test_game_achievements_import_failure(plugin, write):
    plugin.game_achievements_import_failure("134", ImportInProgress())
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "method": "game_achievements_import_failure",
        "params": {
            "game_id": "134",
            "error": {
                "code": 600,
                "message": "Import already in progress"
            }
        }
    }

@pytest.mark.asyncio
async def test_achievements_import_finished(plugin, write):
    plugin.achievements_import_finished()
    response = json.loads(write.call_args[0][0])

    assert response == {
        "jsonrpc": "2.0",
        "method": "achievements_import_finished",
        "params": None
    }

@pytest.mark.asyncio
async def test_start_achievements_import(plugin, write, mocker):
    game_achievements_import_success = mocker.patch.object(plugin, "game_achievements_import_success")
    game_achievements_import_failure = mocker.patch.object(plugin, "game_achievements_import_failure")
    achievements_import_finished = mocker.patch.object(plugin, "achievements_import_finished")

    game_ids = ["1", "5", "9"]
    error = BackendError()
    achievements = [
        Achievement(achievement_id="lvl10", unlock_time=1548421241),
        Achievement(achievement_name="Got level 20", unlock_time=1548422395)
    ]
    plugin.get_unlocked_achievements.coro.side_effect = [
        achievements,
        [],
        error
    ]
    await plugin.start_achievements_import(game_ids)

    with pytest.raises(ImportInProgress):
        await plugin.start_achievements_import(["4", "8"])

    # wait until all tasks are finished
    for _ in range(4):
        await asyncio.sleep(0)

    plugin.get_unlocked_achievements.coro.assert_has_calls([call("1"), call("5"), call("9")])
    game_achievements_import_success.assert_has_calls([
        call("1", achievements),
        call("5", [])
    ])
    game_achievements_import_failure.assert_called_once_with("9", error)
    achievements_import_finished.assert_called_once_with()
