import asyncio
from collections import namedtuple
import logging
import json

class JsonRpcError(Exception):
    def __init__(self, code, message, data=None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__()

class ParseError(JsonRpcError):
    def __init__(self):
        super().__init__(-32700, "Parse error")

class InvalidRequest(JsonRpcError):
    def __init__(self):
        super().__init__(-32600, "Invalid Request")

class MethodNotFound(JsonRpcError):
    def __init__(self):
        super().__init__(-32601, "Method not found")

class InvalidParams(JsonRpcError):
    def __init__(self):
        super().__init__(-32601, "Invalid params")

class Timeout(JsonRpcError):
    def __init__(self):
        super().__init__(-32000, "Method timed out")

class Aborted(JsonRpcError):
    def __init__(self):
        super().__init__(-32001, "Method aborted")

class ApplicationError(JsonRpcError):
    def __init__(self, code, message, data):
        if code >= -32768 and code <= -32000:
            raise ValueError("The error code in reserved range")
        super().__init__(code, message, data)

Request = namedtuple("Request", ["method", "params", "id"], defaults=[{}, None])
Method = namedtuple("Method", ["callback", "internal"])

class Server():
    def __init__(self, reader, writer, encoder=json.JSONEncoder()):
        self._active = True
        self._reader = reader
        self._writer = writer
        self._encoder = encoder
        self._methods = {}
        self._notifications = {}
        self._eof_listeners = []

    def register_method(self, name, callback, internal):
        self._methods[name] = Method(callback, internal)

    def register_notification(self, name, callback, internal):
        self._notifications[name] = Method(callback, internal)

    def register_eof(self, callback):
        self._eof_listeners.append(callback)

    async def run(self):
        while self._active:
            data = await self._reader.readline()
            if not data:
                # on windows rederecting a pipe to stdin result on continues
                # not-blocking return of empty line on EOF
                self._eof()
                continue
            data = data.strip()
            logging.debug("Received data: %s", data)
            self._handle_input(data)

    def stop(self):
        self._active = False

    def _eof(self):
        logging.info("Received EOF")
        self.stop()
        for listener in self._eof_listeners:
            listener()

    def _handle_input(self, data):
        try:
            request = self._parse_request(data)
        except JsonRpcError as error:
            self._send_error(None, error)
            return

        logging.debug("Parsed input: %s", request)

        if request.id is not None:
            self._handle_request(request)
        else:
            self._handle_notification(request)

    def _handle_notification(self, request):
        logging.debug("Handling notification %s", request)
        method = self._notifications.get(request.method)
        if not method:
            logging.error("Received uknown notification: %s", request.method)

        callback, internal = method
        if internal:
            # internal requests are handled immediately
            callback(**request.params)
        else:
            try:
                asyncio.create_task(callback(**request.params))
            except Exception as error: #pylint: disable=broad-except
                logging.error(
                    "Unexpected exception raised in notification handler: %s",
                    repr(error)
                )

    def _handle_request(self, request):
        logging.debug("Handling request %s", request)
        method = self._methods.get(request.method)

        if not method:
            logging.error("Received uknown request: %s", request.method)
            self._send_error(request.id, MethodNotFound())
            return

        callback, internal = method
        if internal:
            # internal requests are handled immediately
            response = callback(request.params)
            self._send_response(request.id, response)
        else:
            async def handle():
                try:
                    result = await callback(request.params)
                    self._send_response(request.id, result)
                except TypeError:
                    self._send_error(request.id, InvalidParams())
                except NotImplementedError:
                    self._send_error(request.id, MethodNotFound())
                except JsonRpcError as error:
                    self._send_error(request.id, error)
                except Exception as error: #pylint: disable=broad-except
                    logging.error("Unexpected exception raised in plugin handler: %s", repr(error))

            asyncio.create_task(handle())

    @staticmethod
    def _parse_request(data):
        try:
            jsonrpc_request = json.loads(data, encoding="utf-8")
            if jsonrpc_request.get("jsonrpc") != "2.0":
                raise InvalidRequest()
            del jsonrpc_request["jsonrpc"]
            return Request(**jsonrpc_request)
        except json.JSONDecodeError:
            raise ParseError()
        except TypeError:
            raise InvalidRequest()

    def _send(self, data):
        try:
            line = self._encoder.encode(data)
            logging.debug("Sending data: %s", line)
            self._writer.write((line + "\n").encode("utf-8"))
            asyncio.create_task(self._writer.drain())
        except TypeError as error:
            logging.error(str(error))

    def _send_response(self, request_id, result):
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }
        self._send(response)

    def _send_error(self, request_id, error):
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": error.code,
                "message": error.message
            }
        }

        if error.data is not None:
            response["error"]["data"] = error.data

        self._send(response)

class NotificationClient():
    def __init__(self, writer, encoder=json.JSONEncoder()):
        self._writer = writer
        self._encoder = encoder
        self._methods = {}

    def notify(self, method, params):
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        self._send(notification)

    def _send(self, data):
        try:
            line = self._encoder.encode(data)
            logging.debug("Sending data: %s", line)
            self._writer.write((line + "\n").encode("utf-8"))
            asyncio.create_task(self._writer.drain())
        except TypeError as error:
            logging.error("Failed to parse outgoing message: %s", str(error))
