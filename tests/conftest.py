from contextlib import ExitStack
import logging
from unittest.mock import patch, MagicMock

import pytest

from galaxy.api.plugin import Plugin
from galaxy.api.consts import Platform

@pytest.fixture()
def reader():
    stream = MagicMock(name="stream_reader")
    stream.read = MagicMock()
    yield stream

@pytest.fixture()
async def writer():
    stream = MagicMock(name="stream_writer")
    stream.write = MagicMock()
    stream.drain = MagicMock()
    yield stream

@pytest.fixture()
def read(reader):
    yield reader.read

@pytest.fixture()
def write(writer):
    yield writer.write

@pytest.fixture()
def plugin(reader, writer):
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
        "install_game",
        "uninstall_game",
        "get_friends",
        "get_game_time",
        "prepare_game_times_context",
        "game_times_import_complete",
        "shutdown_platform_client",
        "shutdown",
        "tick"
    )

    with ExitStack() as stack:
        for method in methods:
            stack.enter_context(patch.object(Plugin, method))
        yield Plugin(Platform.Generic, "0.1", reader, writer, "token")


@pytest.fixture(autouse=True)
def my_caplog(caplog):
    caplog.set_level(logging.DEBUG)
