import os
import sys
import ctypes
import ctypes.wintypes as wt
import webbrowser

def run_win_tray(on_exit_sync, app_url="http://localhost:8080"):
    WM_USER = 0x0400
    TRAY_MSG = WM_USER + 20
    NIM_ADD = 0
    NIM_DELETE = 2
    NIM_SETVERSION = 4
    NIF_MESSAGE = 1
    NIF_ICON = 2
    NIF_TIP = 4
    NIF_INFO = 0x10
    NIIF_INFO = 1
    NOTIFYICON_VERSION_4 = 4
    WM_DESTROY = 2
    WM_RBUTTONUP = 0x0205
    WM_LBUTTONDBLCLK = 0x0203
    MF_SEPARATOR = 0x0800
    MF_STRING = 0
    IDM_ABRIR = 1001
    IDM_FECHAR = 1002

    shell32 = ctypes.windll.shell32
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    LRESULT = ctypes.c_ssize_t
    WPARAM_T = ctypes.c_size_t
    LPARAM_T = ctypes.c_ssize_t
    user32.DefWindowProcW.restype = LRESULT
    user32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, WPARAM_T, LPARAM_T]
    user32.CreateWindowExW.restype = wt.HWND
    user32.CreateWindowExW.argtypes = [wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.HWND, wt.HMENU, wt.HINSTANCE, wt.LPVOID]
    user32.TrackPopupMenu.restype = wt.BOOL
    user32.TrackPopupMenu.argtypes = [wt.HMENU, wt.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.HWND, wt.LPRECT]
    user32.GetMessageW.restype = wt.BOOL
    user32.GetMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT]
    WNDPROCTYPE = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, WPARAM_T, LPARAM_T)

    class WNDCLASSEXW(ctypes.Structure):
        _fields_ = [("cbSize", wt.UINT), ("style", wt.UINT), ("lpfnWndProc", WNDPROCTYPE), ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int), ("hInstance", wt.HINSTANCE), ("hIcon", wt.HICON), ("hCursor", wt.HANDLE), ("hbrBackground", wt.HBRUSH), ("lpszMenuName", wt.LPCWSTR), ("lpszClassName", wt.LPCWSTR), ("hIconSm", wt.HICON)]

    class NOTIFYICONDATAW(ctypes.Structure):
        _fields_ = [("cbSize", wt.DWORD), ("hWnd", wt.HWND), ("uID", wt.UINT), ("uFlags", wt.UINT), ("uCallbackMessage", wt.UINT), ("hIcon", wt.HICON), ("szTip", ctypes.c_wchar * 128), ("dwState", wt.DWORD), ("dwStateMask", wt.DWORD), ("szInfo", ctypes.c_wchar * 256), ("uVersion", wt.UINT), ("szInfoTitle", ctypes.c_wchar * 64), ("dwInfoFlags", wt.DWORD), ("guidItem", ctypes.c_byte * 16), ("hBalloonIcon", wt.HICON)]

    def _make_hicon():
        try:
            from PIL import Image, ImageDraw
            import io as _io
            img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse([1, 1, 30, 30], fill=(21, 101, 192, 255))
            draw.text((7, 9), "CF", fill=(255, 255, 255, 255))
            buf = _io.BytesIO()
            img.save(buf, format="ICO", sizes=[(32, 32)])
            data = buf.getvalue()
            hicon = user32.CreateIconFromResourceEx(ctypes.cast(ctypes.c_char_p(data[22:]), ctypes.POINTER(ctypes.c_byte)), len(data) - 22, 1, 0x00030000, 32, 32, 0)
            if hicon: return hicon
        except Exception:
            pass
        return shell32.ExtractIconW(0, sys.executable, 0)

    def _del_tray(hwnd):
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = hwnd
        nid.uID = 1
        shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))

    def wnd_proc(hwnd, msg, wparam, lparam):
        event = lparam & 0xFFFF
        if msg == TRAY_MSG:
            if event in (WM_RBUTTONUP, WM_LBUTTONDBLCLK):
                hmenu = user32.CreatePopupMenu()
                user32.AppendMenuW(hmenu, MF_STRING, IDM_ABRIR, "Abrir no Navegador")
                user32.AppendMenuW(hmenu, MF_SEPARATOR, 0, None)
                user32.AppendMenuW(hmenu, MF_STRING, IDM_FECHAR, "Fechar Aplicacao")
                pt = wt.POINT()
                user32.GetCursorPos(ctypes.byref(pt))
                user32.SetForegroundWindow(hwnd)
                cmd = user32.TrackPopupMenu(hmenu, 0x0100, pt.x, pt.y, 0, hwnd, None)
                user32.PostMessageW(hwnd, 0, 0, 0)
                user32.DestroyMenu(hmenu)
                if cmd == IDM_ABRIR or event == WM_LBUTTONDBLCLK: webbrowser.open(app_url)
                elif cmd == IDM_FECHAR:
                    _del_tray(hwnd)
                    on_exit_sync()
                    os._exit(0)
        elif msg == WM_DESTROY:
            _del_tray(hwnd)
            user32.PostQuitMessage(0)
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    wc = WNDCLASSEXW()
    wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
    wc.lpfnWndProc = WNDPROCTYPE(wnd_proc)
    wc.hInstance = kernel32.GetModuleHandleW(None)
    wc.lpszClassName = "CFTrayClass"
    user32.RegisterClassExW(ctypes.byref(wc))
    hwnd = user32.CreateWindowExW(0, "CFTrayClass", "CF_Hidden", 0, 0, 0, 0, 0, None, None, wc.hInstance, None)
    hicon = _make_hicon()
    nid = NOTIFYICONDATAW()
    nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
    nid.hWnd = hwnd
    nid.uID = 1
    nid.uFlags = NIF_ICON | NIF_MESSAGE | NIF_TIP | NIF_INFO
    nid.uCallbackMessage = TRAY_MSG
    nid.hIcon = hicon
    nid.szTip = "Controle Financeiro"
    nid.szInfo = "App rodando. Clique direito para abrir ou fechar."
    nid.szInfoTitle = "Controle Financeiro"
    nid.dwInfoFlags = NIIF_INFO
    shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
    nid.uVersion = NOTIFYICON_VERSION_4
    shell32.Shell_NotifyIconW(NIM_SETVERSION, ctypes.byref(nid))
    msg_loop = wt.MSG()
    while user32.GetMessageW(ctypes.byref(msg_loop), None, 0, 0) != 0:
        user32.TranslateMessage(ctypes.byref(msg_loop))
        user32.DispatchMessageW(ctypes.byref(msg_loop))