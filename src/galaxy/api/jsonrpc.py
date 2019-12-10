import asyncio
from collections import namedtuple
from collections.abc import Iterable
import logging
import inspect
import json

from galaxy.reader import StreamLineReader
from galaxy.task_manager import TaskManager


logger = logging.getLogger(__name__)


class JsonRpcError(Exception):
    def __init__(self, code, message, data=None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__()

    def __eq__(self, other):
        return self.code == other.code and self.message == other.message and self.data == other.data

    def json(self):
        obj = {
            "code": self.code,
            "message": self.message
        }

        if self.data is not None:
            obj["data"] = self.data

        return obj

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
Response = namedtuple("Response", ["id", "result", "error"], defaults=[None, {}, {}])
Method = namedtuple("Method", ["callback", "signature", "immediate", "sensitive_params"])


def anonymise_sensitive_params(params, sensitive_params):
    anomized_data = "****"

    if isinstance(sensitive_params, bool):
        if sensitive_params:
            return {k:anomized_data for k,v in params.items()}

    if isinstance(sensitive_params, Iterable):
        return {k: anomized_data if k in sensitive_params else v for k, v in params.items()}

    return params

class Connection():
    def __init__(self, reader, writer, encoder=json.JSONEncoder()):
        self._active = True
        self._reader = StreamLineReader(reader)
        self._writer = writer
        self._encoder = encoder
        self._methods = {}
        self._notifications = {}
        self._task_manager = TaskManager("jsonrpc server")
        self._last_request_id = 0
        self._requests_futures = {}

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

    async def send_request(self, method, params, sensitive_params):
        """
        Send request

        :param method:
        :param params:
        :param sensitive_params: list of parameters that are anonymized before logging; \
            if False - no params are considered sensitive, if True - all params are considered sensitive
        """
        self._last_request_id += 1
        request_id = str(self._last_request_id)

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._requests_futures[self._last_request_id] = (future, sensitive_params)

        logger.info(
            "Sending request: id=%s, method=%s, params=%s",
            request_id, method, anonymise_sensitive_params(params, sensitive_params)
        )

        self._send_request(request_id, method, params)
        return await future

    def send_notification(self, method, params, sensitive_params=False):
        """
        Send notification

        :param method:
        :param params:
        :param sensitive_params: list of parameters that are anonymized before logging; \
            if False - no params are considered sensitive, if True - all params are considered sensitive
        """

        logger.info(
            "Sending notification: method=%s, params=%s",
            method, anonymise_sensitive_params(params, sensitive_params)
        )

        self._send_notification(method, params)

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
            logger.debug("Received %d bytes of data", len(data))
            self._handle_input(data)
            await asyncio.sleep(0) # To not starve task queue

    def close(self):
        if self._active:
            logger.info("Closing JSON-RPC server - not more messages will be read")
            self._active = False

    async def wait_closed(self):
        await self._task_manager.wait()

    def _eof(self):
        logger.info("Received EOF")
        self.close()

    def _handle_input(self, data):
        try:
            message = self._parse_message(data)
        except JsonRpcError as error:
            self._send_error(None, error)
            return

        if isinstance(message, Request):
            if message.id is not None:
                self._handle_request(message)
            else:
                self._handle_notification(message)
        elif isinstance(message, Response):
            self._handle_response(message)

    def _handle_response(self, response):
        request_future = self._requests_futures.get(int(response.id))
        if request_future is None:
            response_type = "response" if response.result is not None else "error"
            logger.warning("Received %s for unknown request: %s", response_type, response.id)
            return

        future, sensitive_params = request_future

        if response.error:
            error = JsonRpcError(
                response.error.setdefault("code", 0),
                response.error.setdefault("message", ""),
                response.error.setdefault("data", None)
            )
            self._log_error(response, error, sensitive_params)
            future.set_exception(error)
            return

        self._log_response(response, sensitive_params)
        future.set_result(response.result)

    def _handle_notification(self, request):
        method = self._notifications.get(request.method)
        if not method:
            logger.error("Received unknown notification: %s", request.method)
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
                logger.exception("Unexpected exception raised in notification handler")

    def _handle_request(self, request):
        method = self._methods.get(request.method)
        if not method:
            logger.error("Received unknown request: %s", request.method)
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
                    logger.exception("Unexpected exception raised in plugin handler")
                    self._send_error(request.id, UnknownError(str(e)))

            self._task_manager.create_task(handle(), request.method)

    @staticmethod
    def _parse_message(data):
        try:
            jsonrpc_message = json.loads(data, encoding="utf-8")
            if jsonrpc_message.get("jsonrpc") != "2.0":
                raise InvalidRequest()
            del jsonrpc_message["jsonrpc"]
            if "result" in jsonrpc_message.keys() or "error" in jsonrpc_message.keys():
                return Response(**jsonrpc_message)
            else:
                return Request(**jsonrpc_message)

        except json.JSONDecodeError:
            raise ParseError()
        except TypeError:
            raise InvalidRequest()

    def _send(self, data, sensitive=True):
        try:
            line = self._encoder.encode(data)
            data = (line + "\n").encode("utf-8")
            if sensitive:
                logger.debug("Sending %d bytes of data", len(data))
            else:
                logging.debug("Sending data: %s", line)
            self._writer.write(data)
        except TypeError as error:
            logger.error(str(error))

    def _send_response(self, request_id, result):
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }
        self._send(response, sensitive=False)

    def _send_error(self, request_id, error):
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": error.json()
        }

        self._send(response, sensitive=False)

    def _send_request(self, request_id, method, params):
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id,
            "params": params
        }
        self._send(request, sensitive=True)

    def _send_notification(self, method, params):
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        self._send(notification, sensitive=True)

    @staticmethod
    def _log_request(request, sensitive_params):
        params = anonymise_sensitive_params(request.params, sensitive_params)
        if request.id is not None:
            logger.info("Handling request: id=%s, method=%s, params=%s", request.id, request.method, params)
        else:
            logger.info("Handling notification: method=%s, params=%s", request.method, params)

    @staticmethod
    def _log_response(response, sensitive_params):
        result = anonymise_sensitive_params(response.result, sensitive_params)
        logger.info("Handling response: id=%s, result=%s", response.id, result)

    @staticmethod
    def _log_error(response, error, sensitive_params):
        data = anonymise_sensitive_params(error.data, sensitive_params)
        logger.info("Handling error: id=%s, code=%s, description=%s, data=%s",
            response.id, error.code, error.message, data
        )
