import pytest
import galaxy.api.errors as errors
import galaxy.api.jsonrpc as jsonrpc


@pytest.mark.parametrize("data", [
    {"key1": "value", "key2": "value2"},
    {},
    {"key1": ["list", "of", "things"], "key2": None},
    {"key1": ("tuple", Exception)},
])
def test_valid_error_data(data):
    test_message = "Test error message"
    test_code = 1
    err_obj = jsonrpc.JsonRpcError(code=test_code, message=test_message, data=data)
    data.update({"internal_type": "JsonRpcError"})
    expected_json = {"code": 1, "data": data, "message": "Test error message"}
    assert err_obj.json() == expected_json


def test_error_default_data():
    test_message = "Test error message"
    test_code = 1
    err_obj = jsonrpc.JsonRpcError(code=test_code, message=test_message)
    expected_json = {"code": test_code, "data": {"internal_type": "JsonRpcError"}, "message": test_message}
    assert err_obj.json() == expected_json


@pytest.mark.parametrize("data", [
    123,
    ["not", "a", "mapping"],
    "nor is this"
])
def test_invalid_error_data(data):
    test_message = "Test error message"
    test_code = 1
    with pytest.raises(TypeError):
        jsonrpc.JsonRpcError(code=test_code, message=test_message, data=data)


def test_error_override_internal_type():
    test_message = "Test error message"
    test_code = 1
    test_data = {"internal_type": "SomeUserProvidedType", "details": "some more data"}
    err_obj = jsonrpc.JsonRpcError(code=test_code, message=test_message, data=test_data)
    expected_json = {"code": test_code, "data": {"details": "some more data", "internal_type": "JsonRpcError"}, "message": test_message}
    assert err_obj.json() == expected_json


@pytest.mark.parametrize("error, expected_error_msg", [
    (errors.AuthenticationRequired, "Authentication required"),
    (errors.BackendNotAvailable, "Backend not available"),
    (errors.BackendTimeout, "Backend timed out"),
    (errors.BackendError, "Backend error"),
    (errors.UnknownBackendResponse, "Backend responded in unknown way"),
    (errors.TooManyRequests, "Too many requests. Try again later"),
    (errors.InvalidCredentials, "Invalid credentials"),
    (errors.NetworkError, "Network error"),
    (errors.ProtocolError, "Protocol error"),
    (errors.TemporaryBlocked, "Temporary blocked"),
    (errors.Banned, "Banned"),
    (errors.AccessDenied, "Access denied"),
    (errors.FailedParsingManifest, "Failed parsing manifest"),
    (errors.TooManyMessagesSent, "Too many messages sent"),
    (errors.IncoherentLastMessage, "Different last message id on backend"),
    (errors.MessageNotFound, "Message not found"),
    (errors.ImportInProgress, "Import already in progress"),
    (jsonrpc.UnknownError, "Unknown error"),
    (jsonrpc.ParseError, "Parse error"),
    (jsonrpc.InvalidRequest, "Invalid Request"),
    (jsonrpc.MethodNotFound, "Method not found"),
    (jsonrpc.InvalidParams, "Invalid params"),
    (jsonrpc.Timeout, "Method timed out"),
    (jsonrpc.Aborted, "Method aborted"),
])
def test_error_default_message(error, expected_error_msg):
    error_json = error().json()

    assert error_json["message"] == expected_error_msg


@pytest.mark.parametrize("error", [
    errors.AuthenticationRequired,
    errors.BackendNotAvailable,
    errors.BackendTimeout,
    errors.BackendError,
    errors.UnknownBackendResponse,
    errors.TooManyRequests,
    errors.InvalidCredentials,
    errors.NetworkError,
    errors.ProtocolError,
    errors.TemporaryBlocked,
    errors.Banned,
    errors.AccessDenied,
    errors.FailedParsingManifest,
    errors.TooManyMessagesSent,
    errors.IncoherentLastMessage,
    errors.MessageNotFound,
    errors.ImportInProgress,
    jsonrpc.UnknownError,
    jsonrpc.ParseError,
    jsonrpc.InvalidRequest,
    jsonrpc.MethodNotFound,
    jsonrpc.InvalidParams,
    jsonrpc.Timeout,
    jsonrpc.Aborted,
])
def test_set_error_custom_message(error):
    custom_message = "test message"

    error_json = error(custom_message).json()

    assert error_json["message"] == custom_message


@pytest.mark.parametrize("error", [
    errors.AuthenticationRequired,
    errors.BackendNotAvailable,
    errors.BackendTimeout,
    errors.BackendError,
    errors.UnknownBackendResponse,
    errors.TooManyRequests,
    errors.InvalidCredentials,
    errors.NetworkError,
    errors.ProtocolError,
    errors.TemporaryBlocked,
    errors.Banned,
    errors.AccessDenied,
    errors.FailedParsingManifest,
    errors.TooManyMessagesSent,
    errors.IncoherentLastMessage,
    errors.MessageNotFound,
    errors.ImportInProgress,
    jsonrpc.UnknownError,
    jsonrpc.ParseError,
    jsonrpc.InvalidRequest,
    jsonrpc.MethodNotFound,
    jsonrpc.InvalidParams,
    jsonrpc.Timeout,
    jsonrpc.Aborted,
])
def test_set_arbitrary_error_message(error):
    arbitrary_messages = [[], {}, (), 1, None]

    for msg in arbitrary_messages:
        error_json = error(msg).json()
        assert error_json["message"] == str(msg)
