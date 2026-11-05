"""Windows job ownership: closing the parent kills remaining engine processes."""
import ctypes
from ctypes import wintypes as W


class Job:
    def __init__(self):
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, W.LPCWSTR]
        kernel.CreateJobObjectW.restype = W.HANDLE
        kernel.SetInformationJobObject.argtypes = [W.HANDLE, ctypes.c_int, ctypes.c_void_p, W.DWORD]
        kernel.AssignProcessToJobObject.argtypes = [W.HANDLE, W.HANDLE]
        kernel.CloseHandle.argtypes = [W.HANDLE]
        class Basic(ctypes.Structure):
            _fields_ = [('process_time', ctypes.c_int64), ('job_time', ctypes.c_int64),
                ('flags', W.DWORD), ('min_working_set', ctypes.c_size_t),
                ('max_working_set', ctypes.c_size_t), ('active_processes', W.DWORD),
                ('affinity', ctypes.c_size_t), ('priority', W.DWORD), ('scheduling', W.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in ['read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes']]
        class Extended(ctypes.Structure):
            _fields_ = [('basic', Basic), ('io', IO), ('process_memory', ctypes.c_size_t),
                ('job_memory', ctypes.c_size_t), ('peak_process_memory', ctypes.c_size_t), ('peak_job_memory', ctypes.c_size_t)]
        self.kernel = kernel
        self.handle = kernel.CreateJobObjectW(None, None)
        if not self.handle: raise ctypes.WinError(ctypes.get_last_error())
        limits = Extended()
        limits.basic.flags = 0x2000 # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            error = ctypes.get_last_error(); self.close(); raise ctypes.WinError(error)

    def assign(self, child):
        if not self.kernel.AssignProcessToJobObject(self.handle, W.HANDLE(int(child._handle))):
            error = ctypes.get_last_error()
            child.kill(); child.wait(timeout=5)
            raise ctypes.WinError(error)

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None
