from unittest.mock import MagicMock

class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        # pylint: disable=useless-super-delegation
        return super(AsyncMock, self).__call__(*args, **kwargs)
