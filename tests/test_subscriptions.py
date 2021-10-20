import pytest

from galaxy.api.types import Subscription, SubscriptionGame
from galaxy.api.consts import SubscriptionDiscovery
from galaxy.api.errors import FailedParsingManifest, BackendError, UnknownError
from galaxy.unittest.mock import async_return_value

from tests import create_message, get_messages

@pytest.mark.asyncio
async def test_get_subscriptions_success(plugin, read, write):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "import_subscriptions"
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"", 10)]

    plugin.get_subscriptions.return_value = async_return_value([
        Subscription("1"),
        Subscription("2", False, subscription_discovery=SubscriptionDiscovery.AUTOMATIC),
        Subscription("3", True, 1580899100, SubscriptionDiscovery.USER_ENABLED)
    ])
    await plugin.run()
    plugin.get_subscriptions.assert_called_with()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "result": {
                "subscriptions": [
                    {
                        "subscription_name": "1",
                        'subscription_discovery': 3
                    },
                    {
                        "subscription_name": "2",
                        "owned": False,
                        'subscription_discovery': 1
                    },
                    {
                        "subscription_name": "3",
                        "owned": True,
                        "end_time": 1580899100,
                        'subscription_discovery': 2
                    }
                ]
            }
        }
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error,code,message,internal_type",
    [
        pytest.param(UnknownError, 0, "Unknown error",  "UnknownError", id="unknown_error"),
        pytest.param(FailedParsingManifest, 200, "Failed parsing manifest", "FailedParsingManifest", id="failed_parsing")
    ],
)
async def test_get_subscriptions_failure_generic(plugin, read, write, error, code, message, internal_type):
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "import_subscriptions"
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"", 10)]
    plugin.get_subscriptions.side_effect = error()
    await plugin.run()
    plugin.get_subscriptions.assert_called_with()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "error": {
                "code": code,
                "data": {"internal_type": internal_type},
                "message": message
            }
        }
    ]


@pytest.mark.asyncio
async def test_get_subscription_games_success(plugin, read, write):
    plugin.prepare_subscription_games_context.return_value = async_return_value(5)
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "start_subscription_games_import",
        "params": {
            "subscription_names": ["sub_a"]
        }
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"", 10)]

    async def sub_games():
        games = [
        SubscriptionGame(game_title="game A", game_id="game_A"),
        SubscriptionGame(game_title="game B", game_id="game_B", start_time=1548495632),
        SubscriptionGame(game_title="game C", game_id="game_C", end_time=1548495633),
        SubscriptionGame(game_title="game D", game_id="game_D", start_time=1548495632, end_time=1548495633),
       ]
        yield [game for game in games]

    plugin.get_subscription_games.return_value = sub_games()
    await plugin.run()
    plugin.prepare_subscription_games_context.assert_called_with(["sub_a"])
    plugin.get_subscription_games.assert_called_with("sub_a", 5)
    plugin.subscription_games_import_complete.asert_called_with()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "result": None
        },
        {
            "jsonrpc": "2.0",
            "method": "subscription_games_import_success",
            "params": {
                "subscription_name": "sub_a",
                "subscription_games": [
                    {
                        "game_title": "game A",
                        "game_id": "game_A"
                    },
                    {
                        "game_title": "game B",
                        "game_id": "game_B",
                        "start_time": 1548495632
                    },
                    {
                        "game_title": "game C",
                        "game_id": "game_C",
                        "end_time": 1548495633
                    },
                    {
                        "game_title": "game D",
                        "game_id": "game_D",
                        "start_time": 1548495632,
                        "end_time": 1548495633
                    }
                ]
            }
        },
        {
            'jsonrpc': '2.0',
            'method':
                'subscription_games_partial_import_finished',
                'params': {
                    "subscription_name": "sub_a"
                }
        },
        {
            "jsonrpc": "2.0",
            "method": "subscription_games_import_finished",
            "params": None
        }
    ]

@pytest.mark.asyncio
async def test_get_subscription_games_success_empty(plugin, read, write):
    plugin.prepare_subscription_games_context.return_value = async_return_value(5)
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "start_subscription_games_import",
        "params": {
            "subscription_names": ["sub_a"]
        }
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"", 10)]

    async def sub_games():
        yield None

    plugin.get_subscription_games.return_value = sub_games()
    await plugin.run()
    plugin.prepare_subscription_games_context.assert_called_with(["sub_a"])
    plugin.get_subscription_games.assert_called_with("sub_a", 5)
    plugin.subscription_games_import_complete.asert_called_with()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "result": None
        },
        {
            "jsonrpc": "2.0",
            "method": "subscription_games_import_success",
            "params": {
                "subscription_name": "sub_a",
                "subscription_games": None
            }
        },
        {
            'jsonrpc': '2.0',
            'method':
                'subscription_games_partial_import_finished',
                'params': {
                    "subscription_name": "sub_a"
                }
        },
        {
            "jsonrpc": "2.0",
            "method": "subscription_games_import_finished",
            "params": None
        }
    ]

@pytest.mark.asyncio
@pytest.mark.parametrize("exception,code,message,internal_type", [
    (BackendError, 4, "Backend error", "BackendError"),
    (KeyError, 0, "Unknown error", "UnknownError")
])
async def test_get_subscription_games_error(exception, code, message, internal_type, plugin, read, write):
    plugin.prepare_subscription_games_context.return_value = async_return_value(None)
    request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "start_subscription_games_import",
        "params": {
            "subscription_names": ["sub_a"]
        }
    }

    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"", 10)]
    plugin.get_subscription_games.side_effect = exception
    await plugin.run()
    plugin.get_subscription_games.assert_called()
    plugin.subscription_games_import_complete.asert_called_with()

    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "result": None
        },
        {
            "jsonrpc": "2.0",
            "method": "subscription_games_import_failure",
            "params": {
                "subscription_name": "sub_a",
                "error": {
                    "code": code,
                    "message": message,
                    "data": {"internal_type": internal_type}
                }
            }
        },
        {
            'jsonrpc': '2.0',
            'method':
                'subscription_games_partial_import_finished',
                'params': {
                    "subscription_name": "sub_a"
                }
        },
        {
            "jsonrpc": "2.0",
            "method": "subscription_games_import_finished",
            "params": None
        }
    ]


@pytest.mark.asyncio
async def test_prepare_get_subscription_games_context_error(plugin, read, write):
    request_id = "31415"
    error_details = {"Details": "Unexpected backend error"}
    error_message, error_code = BackendError().message, BackendError().code
    plugin.prepare_subscription_games_context.side_effect = BackendError(data=error_details)
    request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "start_subscription_games_import",
        "params": {"subscription_names": ["sub_a", "sub_b"]}
    }
    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"", 10)]
    await plugin.run()
    assert get_messages(write) == [
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": error_code,
                "message": error_message,
                "data": {
                    "internal_type": "BackendError",
                    "Details": "Unexpected backend error"
                }
            }
        }
    ]


@pytest.mark.asyncio
async def test_import_already_in_progress_error(plugin, read, write):
    plugin.prepare_subscription_games_context.return_value = async_return_value(None)
    requests = [
        {
            "jsonrpc": "2.0",
            "id": "3",
            "method": "start_subscription_games_import",
            "params": {
                "subscription_names": ["sub_a"]
            }
        },
        {
            "jsonrpc": "2.0",
            "id": "4",
            "method": "start_subscription_games_import",
            "params": {
                "subscription_names": ["sub_a","sub_b"]
            }
        }
    ]
    read.side_effect = [
        async_return_value(create_message(requests[0])),
        async_return_value(create_message(requests[1])),
        async_return_value(b"", 10)
    ]

    await plugin.run()

    responses = get_messages(write)
    assert {
        "jsonrpc": "2.0",
        "id": "3",
        "result": None
    } in responses
    assert {
        "jsonrpc": "2.0",
        "id": "4",
        "error": {
            "code": 600,
            "message": "Import already in progress",
            "data": {"internal_type": "ImportInProgress"}
        }
    } in responses

