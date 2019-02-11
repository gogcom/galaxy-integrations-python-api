import asyncio
import sys

class StdinReader():
    def __init__(self):
        self._stdin = sys.stdin.buffer

    async def readline(self):
        # a single call to sys.stdin.readline() is thread-safe
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._stdin.readline)

class StdoutWriter():
    def __init__(self):
        self._buffer = []
        self._stdout = sys.stdout.buffer

    def write(self, data):
        self._buffer.append(data)

    async def drain(self):
        data, self._buffer = self._buffer, []
        # a single call to sys.stdout.writelines() is thread-safe
        def write(data):
            sys.stdout.writelines(data)
            sys.stdout.flush()

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, write, data)

def stdio():
    # no support for asyncio stdio yet on Windows, see https://bugs.python.org/issue26832
    # use an executor to read from stdio and write to stdout
    # note: if nothing ever drains the writer explicitly, no flushing ever takes place!
    return StdinReader(), StdoutWriter()
