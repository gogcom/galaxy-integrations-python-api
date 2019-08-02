from contextlib import ExitStack
import logging
from unittest.mock import patch, MagicMock

import pytest

from galaxy.api.plugin import Plugin
from galaxy.api.consts import Platform
from galaxy.unittest.mock import AsyncMock, coroutine_mock, skip_loop

@pytest.fixture()
def reader():
    stream = MagicMock(name="stream_reader")
    stream.read = AsyncMock()
    yield stream

@pytest.fixture()
async def writer():
    stream = MagicMock(name="stream_writer")
    stream.write = MagicMock()
    stream.drain = AsyncMock(return_value=None)
    yield stream
    await skip_loop(1) # drain

@pytest.fixture()
def read(reader):
    yield reader.read

@pytest.fixture()
def write(writer):
    yield writer.write

@pytest.fixture()
def plugin(reader, writer):
    """Return plugin instance with all feature methods mocked"""
    async_methods = (
        "handshake_complete",
        "authenticate",
        "get_owned_games",
        "prepare_achievements_context",
        "get_unlocked_achievements",
        "get_local_games",
        "launch_game",
        "install_game",
        "uninstall_game",
        "get_friends",
        "get_game_time",
        "prepare_game_times_context",
        "shutdown_platform_client"
    )

    methods = (
        "shutdown",
        "tick"
    )

    with ExitStack() as stack:
        for method in async_methods:
            stack.enter_context(patch.object(Plugin, method, new_callable=coroutine_mock))
        for method in methods:
            stack.enter_context(patch.object(Plugin, method))
        yield Plugin(Platform.Generic, "0.1", reader, writer, "token")


@pytest.fixture(autouse=True)
def my_caplog(caplog):
    caplog.set_level(logging.DEBUG)
