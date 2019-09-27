from contextlib import ExitStack
import logging
from unittest.mock import patch, MagicMock

import pytest

from galaxy.api.plugin import Plugin
from galaxy.api.consts import Platform
from galaxy.unittest.mock import async_return_value

@pytest.fixture()
def reader():
    stream = MagicMock(name="stream_reader")
    stream.read = MagicMock()
    yield stream

@pytest.fixture()
async def writer():
    stream = MagicMock(name="stream_writer")
    stream.drain.side_effect = lambda: async_return_value(None)
    yield stream

@pytest.fixture()
def read(reader):
    yield reader.read

@pytest.fixture()
def write(writer):
    yield writer.write

@pytest.fixture()
async def plugin(reader, writer):
    """Return plugin instance with all feature methods mocked"""
    methods = (
        "handshake_complete",
        "authenticate",
        "get_owned_games",
        "prepare_achievements_context",
        "get_unlocked_achievements",
        "achievements_import_complete",
        "get_local_games",
        "launch_game",
        "launch_platform_client",
        "install_game",
        "uninstall_game",
        "get_friends",
        "get_game_time",
        "prepare_game_times_context",
        "game_times_import_complete",
        "shutdown_platform_client",
        "shutdown",
        "tick",
        "get_game_library_settings",
        "prepare_game_library_settings_context",
        "game_library_settings_import_complete",
    )

    with ExitStack() as stack:
        for method in methods:
            stack.enter_context(patch.object(Plugin, method))

        async with Plugin(Platform.Generic, "0.1", reader, writer, "token") as plugin:
            plugin.shutdown.return_value = async_return_value(None)
            yield plugin


@pytest.fixture(autouse=True)
def my_caplog(caplog):
    caplog.set_level(logging.DEBUG)
