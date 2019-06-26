import asyncio
import json

import pytest


def assert_rpc_response(write, response_id, result=None):
    assert json.loads(write.call_args[0][0]) == {
        "jsonrpc": "2.0",
        "id": str(response_id),
        "result": result
    }


def assert_rpc_request(write, method, params=None):
    assert json.loads(write.call_args[0][0]) == {
        "jsonrpc": "2.0",
        "method": method,
        "params": {"data": params}
    }


@pytest.fixture
def cache_data():
    return {
        "persistent key": "persistent value",
        "persistent object": {"answer to everything": 42}
    }


def test_initialize_cache(plugin, read, write, cache_data):
    request_id = 3
    request = {
        "jsonrpc": "2.0",
        "id": str(request_id),
        "method": "initialize_cache",
        "params": {"data": cache_data}
    }
    read.side_effect = [json.dumps(request).encode() + b"\n"]

    assert {} == plugin.persistent_cache
    asyncio.run(plugin.run())
    plugin.handshake_complete.assert_called_once_with()
    assert cache_data == plugin.persistent_cache
    assert_rpc_response(write, response_id=request_id)


def test_set_cache(plugin, write, cache_data):
    async def runner():
        assert {} == plugin.persistent_cache

        plugin.persistent_cache.update(cache_data)
        plugin.push_cache()

        assert_rpc_request(write, "push_cache", cache_data)
        assert cache_data == plugin.persistent_cache

    asyncio.run(runner())


def test_clear_cache(plugin, write, cache_data):
    async def runner():
        plugin._persistent_cache = cache_data

        plugin.persistent_cache.clear()
        plugin.push_cache()

        assert_rpc_request(write, "push_cache", {})
        assert {} == plugin.persistent_cache

    asyncio.run(runner())
