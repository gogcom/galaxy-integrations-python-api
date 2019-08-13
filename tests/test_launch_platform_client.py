import pytest

from galaxy.unittest.mock import async_return_value

from tests import create_message

@pytest.mark.asyncio
async def test_success(plugin, read):
    request = {
        "jsonrpc": "2.0",
        "method": "launch_platform_client"
    }

    read.side_effect = [async_return_value(create_message(request)), async_return_value(b"")]
    plugin.launch_platform_client.return_value = async_return_value(None)
    await plugin.run()
    plugin.launch_platform_client.assert_called_with()
