"""Native process basenames only. No shell startup, arguments or token access."""


def names():
    import ctypes
    from ctypes import wintypes as W
    class Entry(ctypes.Structure):
        _fields_=[('dwSize',W.DWORD),('cntUsage',W.DWORD),('th32ProcessID',W.DWORD),
                  ('th32DefaultHeapID',ctypes.c_size_t),('th32ModuleID',W.DWORD),
                  ('cntThreads',W.DWORD),('th32ParentProcessID',W.DWORD),
                  ('pcPriClassBase',W.LONG),('dwFlags',W.DWORD),('szExeFile',W.WCHAR*260)]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes=[W.DWORD,W.DWORD];kernel.CreateToolhelp32Snapshot.restype=W.HANDLE
    kernel.Process32FirstW.argtypes=[W.HANDLE,ctypes.POINTER(Entry)];kernel.Process32FirstW.restype=W.BOOL
    kernel.Process32NextW.argtypes=[W.HANDLE,ctypes.POINTER(Entry)];kernel.Process32NextW.restype=W.BOOL
    kernel.CloseHandle.argtypes=[W.HANDLE]
    handle=kernel.CreateToolhelp32Snapshot(2,0)
    if handle==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
    try:
        entry=Entry();entry.dwSize=ctypes.sizeof(entry)
        if not kernel.Process32FirstW(handle,ctypes.byref(entry)):raise ctypes.WinError(ctypes.get_last_error())
        result=[]
        while True:
            result.append(entry.szExeFile)
            if len(result)>16384:raise ValueError('Process snapshot exceeds safety bound')
            if not kernel.Process32NextW(handle,ctypes.byref(entry)):
                if ctypes.get_last_error()!=18:raise ctypes.WinError(ctypes.get_last_error())
                return result
    finally:kernel.CloseHandle(handle)
