import sys
from dataclasses import dataclass
from typing import Iterable, NewType, Optional, List, cast


ProcessId = NewType("ProcessId", int)


@dataclass
class ProcessInfo:
    pid: ProcessId
    binary_path: Optional[str]


if sys.platform == "win32":
    from ctypes import byref, sizeof, windll, create_unicode_buffer, FormatError, WinError
    from ctypes.wintypes import DWORD


    def pids() -> Iterable[ProcessId]:
        _PROC_ID_T = DWORD
        list_size = 4096

        def try_get_pids(list_size: int) -> List[ProcessId]:
            result_size = DWORD()
            proc_id_list = (_PROC_ID_T * list_size)()

            if not windll.psapi.EnumProcesses(byref(proc_id_list), sizeof(proc_id_list), byref(result_size)):
                raise WinError(descr="Failed to get process ID list: %s" % FormatError())  # type: ignore

            return cast(List[ProcessId], proc_id_list[:int(result_size.value / sizeof(_PROC_ID_T()))])

        while True:
            proc_ids = try_get_pids(list_size)
            if len(proc_ids) < list_size:
                return proc_ids

            list_size *= 2


    def get_process_info(pid: ProcessId) -> Optional[ProcessInfo]:
        _PROC_QUERY_LIMITED_INFORMATION = 0x1000

        process_info = ProcessInfo(pid=pid, binary_path=None)

        h_process = windll.kernel32.OpenProcess(_PROC_QUERY_LIMITED_INFORMATION, False, pid)
        if not h_process:
            return process_info

        try:
            def get_exe_path() -> Optional[str]:
                _MAX_PATH = 260
                _WIN32_PATH_FORMAT = 0x0000

                exe_path_buffer = create_unicode_buffer(_MAX_PATH)
                exe_path_len = DWORD(len(exe_path_buffer))

                return cast(str, exe_path_buffer[:exe_path_len.value]) if windll.kernel32.QueryFullProcessImageNameW(
                    h_process, _WIN32_PATH_FORMAT, exe_path_buffer, byref(exe_path_len)
                ) else None

            process_info.binary_path = get_exe_path()
        finally:
            windll.kernel32.CloseHandle(h_process)
            return process_info
else:
    import psutil


    def pids() -> Iterable[ProcessId]:
        for pid in psutil.pids():
            yield pid


    def get_process_info(pid: ProcessId) -> Optional[ProcessInfo]:
        process_info = ProcessInfo(pid=pid, binary_path=None)
        try:
            process_info.binary_path = psutil.Process(pid=pid).as_dict(attrs=["exe"])["exe"]
        except psutil.NoSuchProcess:
            pass
        finally:
            return process_info


def process_iter() -> Iterable[Optional[ProcessInfo]]:
    for pid in pids():
        yield get_process_info(pid)
