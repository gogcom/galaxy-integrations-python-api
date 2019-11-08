from asyncio import StreamReader


class StreamLineReader:
    """Handles StreamReader readline without buffer limit"""
    def __init__(self, reader: StreamReader):
        self._reader = reader
        self._buffer = bytes()
        self._processed_buffer_it = 0

    async def readline(self):
        while True:
            # check if there is no unprocessed data in the buffer
            if not self._buffer or self._processed_buffer_it != 0:
                chunk = await self._reader.read(1024*1024)
                if not chunk:
                    return bytes() # EOF
                self._buffer += chunk

            it = self._buffer.find(b"\n", self._processed_buffer_it)
            if it < 0:
                self._processed_buffer_it = len(self._buffer)
                continue

            line = self._buffer[:it]
            self._buffer = self._buffer[it+1:]
            self._processed_buffer_it = 0
            return line
