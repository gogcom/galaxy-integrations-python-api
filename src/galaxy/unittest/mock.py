import asyncio
from unittest.mock import MagicMock


class AsyncMock(MagicMock):
    """
    .. deprecated:: 0.45
      Use: :class:`MagicMock` with meth:`~.async_return_value`.
    """
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


def coroutine_mock():
    """
    .. deprecated:: 0.45
      Use: :class:`MagicMock` with meth:`~.async_return_value`.
    """
    coro = MagicMock(name="CoroutineResult")
    corofunc = MagicMock(name="CoroutineFunction", side_effect=asyncio.coroutine(coro))
    corofunc.coro = coro
    return corofunc


async def skip_loop(iterations=1):
    for _ in range(iterations):
        await asyncio.sleep(0)


async def async_return_value(return_value, loop_iterations_delay=0):
    if loop_iterations_delay > 0:
        await skip_loop(loop_iterations_delay)
    return return_value


async def async_raise(error, loop_iterations_delay=0):
    if loop_iterations_delay > 0:
        await skip_loop(loop_iterations_delay)
    raise error
