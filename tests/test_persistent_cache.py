import pytest

from galaxy.unittest.mock import async_return_value

from tests import create_message, get_messages


def assert_rpc_response(write, response_id, result=None):
    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": str(response_id),
            "result": result
        }
    ]


def assert_rpc_request(write, method, params=None):
    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "method": method,
            "params": {"data": params}
        }
    ]


@pytest.fixture
def cache_data():
    return {
        "persistent key": "persistent value",
        "persistent object": {"answer to everything": 42}
    }


@pytest.mark.asyncio
async def test_initialize_cache(plugin, read, write, cache_data):
    request_id = 3
    request = {
        "jsonrpc": "2.0",
        "id": str(request_id),
        "method": "initialize_cache",
        "params": {"data": cache_data}
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"")]

    assert {} == plugin.persistent_cache
    await plugin.run()
    plugin.handshake_complete.assert_called_once_with()
    assert cache_data == plugin.persistent_cache
    assert_rpc_response(write, response_id=request_id)


@pytest.mark.asyncio
async def test_set_cache(plugin, write, cache_data):
    assert {} == plugin.persistent_cache

    plugin.persistent_cache.update(cache_data)
    plugin.push_cache()

    assert_rpc_request(write, "push_cache", cache_data)
    assert cache_data == plugin.persistent_cache


@pytest.mark.asyncio
async def test_clear_cache(plugin, write, cache_data):
    plugin._persistent_cache = cache_data

    plugin.persistent_cache.clear()
    plugin.push_cache()

    assert_rpc_request(write, "push_cache", {})
    assert {} == plugin.persistent_cache
