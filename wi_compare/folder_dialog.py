"""Diálogo nativo de Windows para elegir una carpeta (no un archivo)."""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path


def pick_folder(
    title: str = "Selecciona una carpeta",
    initial: str = "",
    x=None,
    y=None,
) -> str:
    xx, yy = _as_int(x), _as_int(y)
    if sys.platform == "win32":
        path = _run_sta(lambda: _pick_win_ifiledialog(title, initial, xx, yy))
        if path:
            return path
        path = _pick_win_powershell(title, initial, xx, yy)
        if path:
            return path
    return _pick_tk(title, initial, xx, yy)


def _as_int(value) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _run_sta(fn):
    box: dict = {"value": ""}

    def worker() -> None:
        try:
            box["value"] = fn() or ""
        except Exception:
            box["value"] = ""

    thread = threading.Thread(target=worker, name="FolderPickerSTA", daemon=True)
    thread.start()
    thread.join(timeout=300)
    return str(box.get("value") or "")


def _pick_win_ifiledialog(title: str, initial: str, x: int | None, y: int | None) -> str:
    import ctypes
    from ctypes import HRESULT, POINTER, Structure, byref, c_void_p, c_wchar_p
    from ctypes.wintypes import DWORD, HWND, LPCWSTR, LPWSTR, ULONG

    ole32 = ctypes.windll.ole32
    shell32 = ctypes.windll.shell32

    class GUID(Structure):
        _fields_ = [
            ("Data1", DWORD),
            ("Data2", ctypes.c_ushort),
            ("Data3", ctypes.c_ushort),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    ole32.IIDFromString.argtypes = [c_wchar_p, POINTER(GUID)]
    ole32.IIDFromString.restype = HRESULT
    ole32.CoInitializeEx.argtypes = [c_void_p, DWORD]
    ole32.CoInitializeEx.restype = HRESULT
    ole32.CoCreateInstance.argtypes = [
        POINTER(GUID),
        c_void_p,
        DWORD,
        POINTER(GUID),
        POINTER(c_void_p),
    ]
    ole32.CoCreateInstance.restype = HRESULT
    ole32.CoTaskMemFree.argtypes = [c_void_p]
    ole32.CoTaskMemFree.restype = None
    shell32.SHCreateItemFromParsingName.argtypes = [
        LPCWSTR,
        c_void_p,
        POINTER(GUID),
        POINTER(c_void_p),
    ]
    shell32.SHCreateItemFromParsingName.restype = HRESULT

    def guid(text: str) -> GUID:
        value = GUID()
        ole32.IIDFromString(c_wchar_p(text), byref(value))
        return value

    COINIT_APARTMENTTHREADED = 0x2
    CLSCTX_INPROC_SERVER = 1
    FOS_PICKFOLDERS = 0x20
    FOS_FORCEFILESYSTEM = 0x40
    SIGDN_FILESYSPATH = 0x80058000

    owner = _owner_hwnd(x, y)
    stop_nudge = threading.Event()
    nudger = threading.Thread(
        target=_nudge_dialog,
        args=(title, x, y, stop_nudge),
        name="FolderPickerNudge",
        daemon=True,
    )
    ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)
    try:
        clsid = guid("{DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7}")
        iid_dialog = guid("{D57C7288-D4AD-4768-BE02-9D969532D960}")
        iid_item = guid("{43826D1E-E718-42EE-BC55-A1E261C37BFE}")

        dialog = c_void_p()
        hr = ole32.CoCreateInstance(
            byref(clsid),
            None,
            CLSCTX_INPROC_SERVER,
            byref(iid_dialog),
            byref(dialog),
        )
        if int(hr) != 0 or not dialog:
            return ""

        def method(index: int, restype, *argtypes):
            vtbl = ctypes.cast(dialog, POINTER(POINTER(c_void_p))).contents
            proto = ctypes.WINFUNCTYPE(restype, c_void_p, *argtypes)
            func = proto(vtbl[index])
            return lambda *args: func(dialog, *args)

        release = method(2, ULONG)
        show = method(3, HRESULT, HWND)
        set_options = method(9, HRESULT, DWORD)
        get_options = method(10, HRESULT, POINTER(DWORD))
        set_folder = method(12, HRESULT, c_void_p)
        set_title = method(17, HRESULT, LPCWSTR)
        get_result = method(20, HRESULT, POINTER(c_void_p))

        opts = DWORD(0)
        get_options(byref(opts))
        set_options(opts.value | FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM)
        if title:
            set_title(title)

        if initial and Path(initial).is_dir():
            item = c_void_p()
            created = shell32.SHCreateItemFromParsingName(
                LPCWSTR(str(Path(initial))),
                None,
                byref(iid_item),
                byref(item),
            )
            if int(created) == 0 and item:
                set_folder(item)

        nudger.start()
        shown = int(show(owner or None)) & 0xFFFFFFFF
        path = ""
        if shown == 0:
            shell_item = c_void_p()
            if int(get_result(byref(shell_item))) == 0 and shell_item:
                item_vtbl = ctypes.cast(shell_item, POINTER(POINTER(c_void_p))).contents
                get_name = ctypes.WINFUNCTYPE(HRESULT, c_void_p, DWORD, POINTER(LPWSTR))(
                    item_vtbl[5]
                )
                release_item = ctypes.WINFUNCTYPE(ULONG, c_void_p)(item_vtbl[2])
                ppsz = LPWSTR()
                if int(get_name(shell_item, SIGDN_FILESYSPATH, byref(ppsz))) == 0 and ppsz:
                    path = ppsz.value or ""
                    ole32.CoTaskMemFree(ppsz)
                release_item(shell_item)

        release()
        return path
    finally:
        stop_nudge.set()
        _destroy_hwnd(owner)
        ole32.CoUninitialize()


def _click_point(x: int | None, y: int | None):
    import ctypes
    from ctypes import byref
    from ctypes.wintypes import POINT

    user32 = ctypes.windll.user32
    user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
    user32.GetCursorPos.restype = ctypes.c_bool
    pt = POINT()
    if x is not None and y is not None:
        pt.x, pt.y = int(x), int(y)
    else:
        user32.GetCursorPos(byref(pt))
    return pt


def _owner_hwnd(x: int | None, y: int | None):
    import ctypes
    from ctypes.wintypes import DWORD, HWND, LPCWSTR, POINT

    user32 = ctypes.windll.user32
    pt = _click_point(x, y)
    work = _work_area_at(pt)
    cx = (work[0] + work[2]) // 2
    cy = (work[1] + work[3]) // 2

    WS_POPUP = 0x80000000
    WS_VISIBLE = 0x10000000
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_TOPMOST = 0x00000008
    HWND_TOPMOST = HWND(-1)
    SWP_NOACTIVATE = 0x0010
    SWP_SHOWWINDOW = 0x0040

    user32.CreateWindowExW.argtypes = [
        DWORD,
        LPCWSTR,
        LPCWSTR,
        DWORD,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        HWND,
        HWND,
        HWND,
        ctypes.c_void_p,
    ]
    user32.CreateWindowExW.restype = HWND
    hwnd = user32.CreateWindowExW(
        WS_EX_TOOLWINDOW | WS_EX_TOPMOST,
        "STATIC",
        "",
        WS_POPUP | WS_VISIBLE,
        cx,
        cy,
        1,
        1,
        None,
        None,
        None,
        None,
    )
    if hwnd:
        user32.SetWindowPos(
            hwnd,
            HWND_TOPMOST,
            cx,
            cy,
            1,
            1,
            SWP_SHOWWINDOW | SWP_NOACTIVATE,
        )
        user32.SetForegroundWindow(hwnd)
    return hwnd


def _destroy_hwnd(hwnd) -> None:
    if not hwnd:
        return
    try:
        import ctypes

        ctypes.windll.user32.DestroyWindow(hwnd)
    except Exception:
        return


def _work_area_at(pt) -> tuple[int, int, int, int]:
    import ctypes
    from ctypes import Structure, byref, sizeof
    from ctypes.wintypes import DWORD, HWND, POINT, RECT

    class MONITORINFO(Structure):
        _fields_ = [
            ("cbSize", DWORD),
            ("rcMonitor", RECT),
            ("rcWork", RECT),
            ("dwFlags", DWORD),
        ]

    user32 = ctypes.windll.user32
    user32.MonitorFromPoint.argtypes = [POINT, DWORD]
    user32.MonitorFromPoint.restype = HWND
    user32.GetMonitorInfoW.argtypes = [HWND, ctypes.POINTER(MONITORINFO)]
    user32.GetMonitorInfoW.restype = ctypes.c_bool
    monitor = user32.MonitorFromPoint(pt, 2)
    info = MONITORINFO()
    info.cbSize = sizeof(MONITORINFO)
    if monitor and user32.GetMonitorInfoW(monitor, byref(info)):
        r = info.rcWork
        return int(r.left), int(r.top), int(r.right), int(r.bottom)
    return 0, 0, 800, 600


def _center_hwnd_on_point(hwnd, x: int | None, y: int | None) -> bool:
    import ctypes
    from ctypes import byref
    from ctypes.wintypes import HWND, RECT

    user32 = ctypes.windll.user32
    wr = RECT()
    if not user32.GetWindowRect(hwnd, byref(wr)):
        return False
    width = int(wr.right - wr.left)
    height = int(wr.bottom - wr.top)
    if width < 80 or height < 80:
        return False
    pt = _click_point(x, y)
    left, top, right, bottom = _work_area_at(pt)
    nx = left + max(0, (right - left - width) // 2)
    ny = top + max(0, (bottom - top - height) // 2)
    SWP_NOSIZE = 0x0001
    SWP_NOZORDER = 0x0004
    user32.SetWindowPos.argtypes = [
        HWND,
        HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint,
    ]
    user32.SetWindowPos(hwnd, None, nx, ny, 0, 0, SWP_NOSIZE | SWP_NOZORDER)
    return True


def _nudge_dialog(title: str, x: int | None, y: int | None, stop: threading.Event) -> None:
    import ctypes
    from ctypes import byref
    from ctypes.wintypes import HWND, LPCWSTR, RECT

    user32 = ctypes.windll.user32
    user32.FindWindowW.argtypes = [LPCWSTR, LPCWSTR]
    user32.FindWindowW.restype = HWND
    user32.IsWindowVisible.argtypes = [HWND]
    user32.IsWindowVisible.restype = ctypes.c_bool
    user32.GetClassNameW.argtypes = [HWND, LPCWSTR, ctypes.c_int]
    user32.GetWindowRect.argtypes = [HWND, ctypes.POINTER(RECT)]

    titles = [t for t in (title, "Seleccionar carpeta", "Select Folder") if t]
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, HWND, ctypes.c_void_p)
    moved = False

    def candidates() -> list:
        found: list = []
        for text in titles:
            hwnd = user32.FindWindowW("#32770", text) or user32.FindWindowW(None, text)
            if hwnd:
                found.append(hwnd)

        def enum_proc(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, buf, 256)
            if buf.value != "#32770":
                return True
            wr = RECT()
            if user32.GetWindowRect(hwnd, byref(wr)) and int(wr.right - wr.left) >= 80:
                found.append(hwnd)
            return True

        user32.EnumWindows(WNDENUMPROC(enum_proc), 0)
        return found

    for _ in range(80):
        if stop.is_set():
            return
        for hwnd in candidates():
            if _center_hwnd_on_point(hwnd, x, y):
                if moved:
                    return
                moved = True
                break
        time.sleep(0.03)


def _pick_win_powershell(title: str, initial: str, x: int | None = None, y: int | None = None) -> str:
    safe_title = title.replace("'", "''")
    safe_initial = initial.replace("'", "''")
    xx = 0 if x is None else int(x)
    yy = 0 if y is None else int(y)
    lines = [
        "Add-Type -AssemblyName System.Windows.Forms",
        "[System.Windows.Forms.Application]::EnableVisualStyles()",
        "$owner = New-Object System.Windows.Forms.Form",
        "$owner.StartPosition = 'Manual'",
        f"$owner.Location = New-Object System.Drawing.Point({xx}, {yy})",
        "$owner.Size = New-Object System.Drawing.Size(1, 1)",
        "$owner.ShowInTaskbar = $false",
        "$owner.FormBorderStyle = 'None'",
        "$owner.Opacity = 0",
        "$owner.Show()",
        "$d = New-Object System.Windows.Forms.FolderBrowserDialog",
        f"$d.Description = '{safe_title}'",
        "$d.ShowNewFolderButton = $false",
        "try { $d.AutoUpgradeEnabled = $true } catch {}",
        "try { $d.UseDescriptionForTitle = $true } catch {}",
    ]
    if initial and Path(initial).is_dir():
        lines.append(f"$d.SelectedPath = '{safe_initial}'")
    lines.append("try { if ($d.ShowDialog($owner) -eq 'OK') { Write-Output $d.SelectedPath } } finally { $owner.Dispose() }")
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-STA", "-Command", "; ".join(lines)],
            capture_output=True,
            text=True,
            timeout=300,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (completed.stdout or "").strip()


def _pick_tk(title: str, initial: str, x: int | None = None, y: int | None = None) -> str:
    try:
        import tkinter
        from tkinter import filedialog

        root = tkinter.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", 1)
        if x is not None and y is not None:
            root.geometry(f"+{int(x)}+{int(y)}")
        kwargs = {"title": title, "mustexist": True}
        if initial and Path(initial).is_dir():
            kwargs["initialdir"] = initial
        path = filedialog.askdirectory(**kwargs) or ""
        root.destroy()
        return path
    except Exception:
        return ""
