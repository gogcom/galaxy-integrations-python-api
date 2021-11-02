from galaxy.api.jsonrpc import ApplicationError, UnknownError

assert UnknownError


class AuthenticationRequired(ApplicationError):
    def __init__(self, message="Authentication required", data=None):
        super().__init__(1, message, data)


class BackendNotAvailable(ApplicationError):
    def __init__(self, message="Backend not available", data=None):
        super().__init__(2, message, data)


class BackendTimeout(ApplicationError):
    def __init__(self, message="Backend timed out", data=None):
        super().__init__(3, message, data)


class BackendError(ApplicationError):
    def __init__(self, message="Backend error", data=None):
        super().__init__(4, message, data)


class TooManyRequests(ApplicationError):
    def __init__(self, message="Too many requests. Try again later", data=None):
        super().__init__(5, message, data)


class UnknownBackendResponse(ApplicationError):
    def __init__(self, message="Backend responded in unknown way", data=None):
        super().__init__(6, message, data)


class InvalidCredentials(ApplicationError):
    def __init__(self, message="Invalid credentials", data=None):
        super().__init__(100, message, data)


class NetworkError(ApplicationError):
    def __init__(self, message="Network error", data=None):
        super().__init__(101, message, data)


class ProtocolError(ApplicationError):
    def __init__(self, message="Protocol error", data=None):
        super().__init__(103, message, data)


class TemporaryBlocked(ApplicationError):
    def __init__(self, message="Temporary blocked", data=None):
        super().__init__(104, message, data)


class Banned(ApplicationError):
    def __init__(self, message="Banned", data=None):
        super().__init__(105, message, data)


class AccessDenied(ApplicationError):
    def __init__(self, message="Access denied", data=None):
        super().__init__(106, message, data)


class FailedParsingManifest(ApplicationError):
    def __init__(self, message="Failed parsing manifest", data=None):
        super().__init__(200, message, data)


class TooManyMessagesSent(ApplicationError):
    def __init__(self, message="Too many messages sent", data=None):
        super().__init__(300, message, data)


class IncoherentLastMessage(ApplicationError):
    def __init__(self, message="Different last message id on backend", data=None):
        super().__init__(400, message, data)


class MessageNotFound(ApplicationError):
    def __init__(self, message="Message not found", data=None):
        super().__init__(500, message, data)


class ImportInProgress(ApplicationError):
    def __init__(self, message="Import already in progress", data=None):
        super().__init__(600, message, data)
