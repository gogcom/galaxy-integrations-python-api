import asyncio
from collections import namedtuple
from collections.abc import Iterable
import logging
import inspect
import json

from galaxy.reader import StreamLineReader
from galaxy.task_manager import TaskManager

class JsonRpcError(Exception):
    def __init__(self, code, message, data=None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__()

    def __eq__(self, other):
        return self.code == other.code and self.message == other.message and self.data == other.data

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
        super().__init__(-32602, "Invalid params")

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

class UnknownError(ApplicationError):
    def __init__(self, data=None):
        super().__init__(0, "Unknown error", data)

Request = namedtuple("Request", ["method", "params", "id"], defaults=[{}, None])
Method = namedtuple("Method", ["callback", "signature", "immediate", "sensitive_params"])


def anonymise_sensitive_params(params, sensitive_params):
    anomized_data = "****"

    if isinstance(sensitive_params, bool):
        if sensitive_params:
            return {k:anomized_data for k,v in params.items()}

    if isinstance(sensitive_params, Iterable):
        return {k: anomized_data if k in sensitive_params else v for k, v in params.items()}

    return params

class Server():
    def __init__(self, reader, writer, encoder=json.JSONEncoder()):
        self._active = True
        self._reader = StreamLineReader(reader)
        self._writer = writer
        self._encoder = encoder
        self._methods = {}
        self._notifications = {}
        self._task_manager = TaskManager("jsonrpc server")

    def register_method(self, name, callback, immediate, sensitive_params=False):
        """
        Register method

        :param name:
        :param callback:
        :param internal: if True the callback will be processed immediately (synchronously)
        :param sensitive_params: list of parameters that are anonymized before logging; \
            if False - no params are considered sensitive, if True - all params are considered sensitive
        """
        self._methods[name] = Method(callback, inspect.signature(callback), immediate, sensitive_params)

    def register_notification(self, name, callback, immediate, sensitive_params=False):
        """
        Register notification

        :param name:
        :param callback:
        :param internal: if True the callback will be processed immediately (synchronously)
        :param sensitive_params: list of parameters that are anonymized before logging; \
            if False - no params are considered sensitive, if True - all params are considered sensitive
        """
        self._notifications[name] = Method(callback, inspect.signature(callback), immediate, sensitive_params)

    async def run(self):
        while self._active:
            try:
                data = await self._reader.readline()
                if not data:
                    self._eof()
                    continue
            except:
                self._eof()
                continue
            data = data.strip()
            logging.debug("Received %d bytes of data", len(data))
            self._handle_input(data)
            await asyncio.sleep(0) # To not starve task queue

    def close(self):
        logging.info("Closing JSON-RPC server - not more messages will be read")
        self._active = False

    async def wait_closed(self):
        await self._task_manager.wait()

    def _eof(self):
        logging.info("Received EOF")
        self.close()

    def _handle_input(self, data):
        try:
            request = self._parse_request(data)
        except JsonRpcError as error:
            self._send_error(None, error)
            return

        if request.id is not None:
            self._handle_request(request)
        else:
            self._handle_notification(request)

    def _handle_notification(self, request):
        method = self._notifications.get(request.method)
        if not method:
            logging.error("Received unknown notification: %s", request.method)
            return

        callback, signature, immediate, sensitive_params = method
        self._log_request(request, sensitive_params)

        try:
            bound_args = signature.bind(**request.params)
        except TypeError:
            self._send_error(request.id, InvalidParams())

        if immediate:
            callback(*bound_args.args, **bound_args.kwargs)
        else:
            try:
                self._task_manager.create_task(callback(*bound_args.args, **bound_args.kwargs), request.method)
            except Exception:
                logging.exception("Unexpected exception raised in notification handler")

    def _handle_request(self, request):
        method = self._methods.get(request.method)
        if not method:
            logging.error("Received unknown request: %s", request.method)
            self._send_error(request.id, MethodNotFound())
            return

        callback, signature, immediate, sensitive_params = method
        self._log_request(request, sensitive_params)

        try:
            bound_args = signature.bind(**request.params)
        except TypeError:
            self._send_error(request.id, InvalidParams())

        if immediate:
            response = callback(*bound_args.args, **bound_args.kwargs)
            self._send_response(request.id, response)
        else:
            async def handle():
                try:
                    result = await callback(*bound_args.args, **bound_args.kwargs)
                    self._send_response(request.id, result)
                except NotImplementedError:
                    self._send_error(request.id, MethodNotFound())
                except JsonRpcError as error:
                    self._send_error(request.id, error)
                except asyncio.CancelledError:
                    self._send_error(request.id, Aborted())
                except Exception as e:  #pylint: disable=broad-except
                    logging.exception("Unexpected exception raised in plugin handler")
                    self._send_error(request.id, UnknownError(str(e)))

            self._task_manager.create_task(handle(), request.method)

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
            data = (line + "\n").encode("utf-8")
            self._writer.write(data)
            self._task_manager.create_task(self._writer.drain(), "drain")
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

    @staticmethod
    def _log_request(request, sensitive_params):
        params = anonymise_sensitive_params(request.params, sensitive_params)
        if request.id is not None:
            logging.info("Handling request: id=%s, method=%s, params=%s", request.id, request.method, params)
        else:
            logging.info("Handling notification: method=%s, params=%s", request.method, params)

class NotificationClient():
    def __init__(self, writer, encoder=json.JSONEncoder()):
        self._writer = writer
        self._encoder = encoder
        self._methods = {}
        self._task_manager = TaskManager("notification client")

    def notify(self, method, params, sensitive_params=False):
        """
        Send notification

        :param method:
        :param params:
        :param sensitive_params: list of parameters that are anonymized before logging; \
            if False - no params are considered sensitive, if True - all params are considered sensitive
        """
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        self._log(method, params, sensitive_params)
        self._send(notification)

    async def close(self):
        await self._task_manager.wait()

    def _send(self, data):
        try:
            line = self._encoder.encode(data)
            data = (line + "\n").encode("utf-8")
            logging.debug("Sending %d byte of data", len(data))
            self._writer.write(data)
            self._task_manager.create_task(self._writer.drain(), "drain")
        except TypeError as error:
            logging.error("Failed to parse outgoing message: %s", str(error))

    @staticmethod
    def _log(method, params, sensitive_params):
        params = anonymise_sensitive_params(params, sensitive_params)
        logging.info("Sending notification: method=%s, params=%s", method, params)
