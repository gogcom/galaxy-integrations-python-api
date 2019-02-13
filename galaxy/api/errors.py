from galaxy.api.jsonrpc import ApplicationError

class UnknownError(ApplicationError):
    def __init__(self, data=None):
        super().__init__(0, "Unknown error", data)

class InvalidCredentials(ApplicationError):
    def __init__(self, data=None):
        super().__init__(100, "Invalid credentials", data)

class NetworkError(ApplicationError):
    def __init__(self, data=None):
        super().__init__(101, "Network error", data)

class LoggedInElsewhere(ApplicationError):
    def __init__(self, data=None):
        super().__init__(102, "Logged in elsewhere", data)

class ProtocolError(ApplicationError):
    def __init__(self, data=None):
        super().__init__(103, "Protocol error", data)

class BackendNotAvailable(ApplicationError):
    def __init__(self, data=None):
        super().__init__(104, "Backend not available", data)

class BackendTimeout(ApplicationError):
    def __init__(self, data=None):
        super().__init__(105, "Backend timed out", data)

class BackendError(ApplicationError):
    def __init__(self, data=None):
        super().__init__(106, "Backend error", data)

class TemporaryBlocked(ApplicationError):
    def __init__(self, data=None):
        super().__init__(107, "Temporary blocked", data)

class Banned(ApplicationError):
    def __init__(self, data=None):
        super().__init__(108, "Banned", data)

class AccessDenied(ApplicationError):
    def __init__(self, data=None):
        super().__init__(109, "Access denied", data)

class ParentalControlBlock(ApplicationError):
    def __init__(self, data=None):
        super().__init__(110, "Parental control block", data)

class DeviceBlocked(ApplicationError):
    def __init__(self, data=None):
        super().__init__(111, "Device blocked", data)

class RegionBlocked(ApplicationError):
    def __init__(self, data=None):
        super().__init__(112, "Region blocked", data)

class FailedParsingManifest(ApplicationError):
    def __init__(self, data=None):
        super().__init__(200, "Failed parsing manifest", data)

class TooManyMessagesSent(ApplicationError):
    def __init__(self, data=None):
        super().__init__(300, "Too many messages sent", data)

class IncoherentLastMessage(ApplicationError):
    def __init__(self, data=None):
        super().__init__(400, "Different last message id on backend", data)

class MessageNotFound(ApplicationError):
    def __init__(self, data=None):
        super().__init__(500, "Message not found", data)
