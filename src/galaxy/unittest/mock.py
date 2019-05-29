from asyncio import coroutine
from unittest.mock import MagicMock

class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)

def coroutine_mock():
    coro = MagicMock(name="CoroutineResult")
    corofunc = MagicMock(name="CoroutineFunction", side_effect=coroutine(coro))
    corofunc.coro = coro
    return corofunc