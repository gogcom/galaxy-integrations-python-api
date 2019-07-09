from unittest.mock import MagicMock

import pytest

from galaxy.reader import StreamLineReader
from galaxy.unittest.mock import AsyncMock

@pytest.fixture()
def stream_reader():
    reader = MagicMock()
    reader.read = AsyncMock()
    return reader

@pytest.fixture()
def read(stream_reader):
    return stream_reader.read

@pytest.fixture()
def reader(stream_reader):
    return StreamLineReader(stream_reader)

@pytest.mark.asyncio
async def test_message(reader, read):
    read.return_value = b"a\n"
    assert await reader.readline() == b"a"
    read.assert_called_once()

@pytest.mark.asyncio
async def test_separate_messages(reader, read):
    read.side_effect = [b"a\n", b"b\n"]
    assert await reader.readline() == b"a"
    assert await reader.readline() == b"b"
    assert read.call_count == 2

@pytest.mark.asyncio
async def test_connected_messages(reader, read):
    read.return_value = b"a\nb\n"
    assert await reader.readline() == b"a"
    assert await reader.readline() == b"b"
    read.assert_called_once()

@pytest.mark.asyncio
async def test_cut_message(reader, read):
    read.side_effect = [b"a", b"b\n"]
    assert await reader.readline() == b"ab"
    assert read.call_count == 2

@pytest.mark.asyncio
async def test_half_message(reader, read):
    read.side_effect = [b"a", b""]
    assert await reader.readline() == b""
    assert read.call_count == 2
