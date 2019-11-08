import sys


if sys.platform == "win32":
    import logging
    import ctypes
    from ctypes.wintypes import LONG, HKEY, LPCWSTR, DWORD, BOOL, HANDLE, LPVOID

    LPSECURITY_ATTRIBUTES = LPVOID

    RegOpenKeyEx = ctypes.windll.advapi32.RegOpenKeyExW
    RegOpenKeyEx.restype = LONG
    RegOpenKeyEx.argtypes = [HKEY, LPCWSTR, DWORD, DWORD, ctypes.POINTER(HKEY)]

    RegCloseKey = ctypes.windll.advapi32.RegCloseKey
    RegCloseKey.restype = LONG
    RegCloseKey.argtypes = [HKEY]

    RegNotifyChangeKeyValue = ctypes.windll.advapi32.RegNotifyChangeKeyValue
    RegNotifyChangeKeyValue.restype = LONG
    RegNotifyChangeKeyValue.argtypes = [HKEY, BOOL, DWORD, HANDLE, BOOL]

    CloseHandle = ctypes.windll.kernel32.CloseHandle
    CloseHandle.restype = BOOL
    CloseHandle.argtypes = [HANDLE]

    CreateEvent = ctypes.windll.kernel32.CreateEventW
    CreateEvent.restype = BOOL
    CreateEvent.argtypes = [LPSECURITY_ATTRIBUTES, BOOL, BOOL, LPCWSTR]

    WaitForSingleObject = ctypes.windll.kernel32.WaitForSingleObject
    WaitForSingleObject.restype = DWORD
    WaitForSingleObject.argtypes = [HANDLE, DWORD]

    ERROR_SUCCESS = 0x00000000

    KEY_READ = 0x00020019
    KEY_QUERY_VALUE = 0x00000001

    REG_NOTIFY_CHANGE_NAME = 0x00000001
    REG_NOTIFY_CHANGE_LAST_SET = 0x00000004

    WAIT_OBJECT_0 = 0x00000000
    WAIT_TIMEOUT = 0x00000102

class RegistryMonitor:

    def __init__(self, root, subkey):
        self._root = root
        self._subkey = subkey
        self._event = CreateEvent(None, False, False, None)

        self._key = None
        self._open_key()
        if self._key:
            self._set_key_update_notification()

    def close(self):
        CloseHandle(self._event)
        if self._key:
            RegCloseKey(self._key)
            self._key = None

    def is_updated(self):
        wait_result = WaitForSingleObject(self._event, 0)

        # previously watched
        if wait_result == WAIT_OBJECT_0:
            self._set_key_update_notification()
            return True

        # no changes or no key before
        if wait_result != WAIT_TIMEOUT:
            # unexpected error
            logging.warning("Unexpected WaitForSingleObject result %s", wait_result)
            return False

        if self._key is None:
            self._open_key()

        if self._key is not None:
            self._set_key_update_notification()

        return False

    def _set_key_update_notification(self):
        filter_ = REG_NOTIFY_CHANGE_NAME | REG_NOTIFY_CHANGE_LAST_SET
        status = RegNotifyChangeKeyValue(self._key, True, filter_, self._event, True)
        if status != ERROR_SUCCESS:
            # key was deleted
            RegCloseKey(self._key)
            self._key = None

    def _open_key(self):
        access = KEY_QUERY_VALUE | KEY_READ
        self._key = HKEY()
        rc = RegOpenKeyEx(self._root, self._subkey, 0, access, ctypes.byref(self._key))
        if rc != ERROR_SUCCESS:
            self._key = None
