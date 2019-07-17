import json

import pytest

@pytest.mark.asyncio
async def test_success(plugin, read):
    request = {
        "jsonrpc": "2.0",
        "method": "shutdown_platform_client"
    }

    read.side_effect = [json.dumps(request).encode() + b"\n", b""]
    plugin.shutdown_platform_client.return_value = None
    await plugin.run()
    plugin.shutdown_platform_client.assert_called_with()
