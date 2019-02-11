from contextlib import ExitStack
import logging
from unittest.mock import patch

import pytest

from galaxy.api.plugin import Plugin
from galaxy.api.stream import StdinReader, StdoutWriter
from galaxy.api.consts import Platform
from tests.async_mock import AsyncMock

@pytest.fixture()
def plugin():
    """Return plugin instance with all feature methods mocked"""
    async_methods = (
        "authenticate",
        "pass_login_credentials",
        "get_owned_games",
        "get_unlocked_achievements",
        "get_local_games",
        "launch_game",
        "install_game",
        "uninstall_game",
        "get_friends",
        "get_users",
        "send_message",
        "mark_as_read",
        "get_rooms",
        "get_room_history_from_message",
        "get_room_history_from_timestamp",
        "get_game_times"
    )

    methods = (
        "shutdown",
        "tick"
    )

    with ExitStack() as stack:
        for method in async_methods:
            stack.enter_context(patch.object(Plugin, method, new_callable=AsyncMock))
        for method in methods:
            stack.enter_context(patch.object(Plugin, method))
        yield Plugin(Platform.Generic)

@pytest.fixture()
def readline():
    with patch.object(StdinReader, "readline", new_callable=AsyncMock) as mock:
        yield mock

@pytest.fixture()
def write():
    with patch.object(StdoutWriter, "write") as mock:
        yield mock

@pytest.fixture(autouse=True)
def my_caplog(caplog):
    caplog.set_level(logging.DEBUG)
