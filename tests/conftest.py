from contextlib import ExitStack
import logging
from unittest.mock import patch, MagicMock

import pytest

from galaxy.api.plugin import Plugin
from galaxy.api.consts import Platform
from tests.async_mock import AsyncMock

@pytest.fixture()
def reader():
    stream = MagicMock(name="stream_reader")
    stream.readline = AsyncMock()
    yield stream

@pytest.fixture()
def writer():
    stream = MagicMock(name="stream_writer")
    stream.write = MagicMock()
    stream.drain = AsyncMock()
    yield stream

@pytest.fixture()
def readline(reader):
    yield reader.readline

@pytest.fixture()
def write(writer):
    yield writer.write

@pytest.fixture()
def plugin(reader, writer):
    """Return plugin instance with all feature methods mocked"""
    async_methods = (
        "authenticate",
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
        yield Plugin(Platform.Generic, reader, writer, "token")

@pytest.fixture(autouse=True)
def my_caplog(caplog):
    caplog.set_level(logging.DEBUG)
