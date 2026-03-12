"""
keep_awake.py
Windows 절전 모드 방지 - 5분마다 마우스를 미세하게 움직입니다.
Git-bash 환경에서 실행: python keep_awake.py
종료: Ctrl+C  또는  수동으로 절전 모드 진입 시 자동 종료
"""

import time
import sys
import ctypes
import ctypes.wintypes
import threading

# ── Windows 상수 ──────────────────────────────────────────────
WM_POWERBROADCAST = 0x0218
PBT_APMSUSPEND    = 0x0004
WS_EX_TOOLWINDOW  = 0x00000080
WS_OVERLAPPED     = 0x00000000

# ── 공유 플래그 ────────────────────────────────────────────────
suspend_event = threading.Event()

# ── 마우스 제어 ────────────────────────────────────────────────
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def get_cursor_pos():
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

def move_cursor(x, y):
    ctypes.windll.user32.SetCursorPos(x, y)

def nudge_mouse(offset=5):
    x, y = get_cursor_pos()
    move_cursor(x + offset, y + offset)
    time.sleep(0.1)
    move_cursor(x, y)

# ── 절전 실행 상태 설정 ────────────────────────────────────────
def prevent_sleep():
    ES_CONTINUOUS       = 0x80000000
    ES_SYSTEM_REQUIRED  = 0x00000001
    ES_DISPLAY_REQUIRED = 0x00000002
    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
    )

def restore_sleep():
    ES_CONTINUOUS = 0x80000000
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)

# ── WM_POWERBROADCAST 감지용 숨김 창 스레드 ───────────────────
WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_long,
    ctypes.wintypes.HWND,
    ctypes.c_uint,
    ctypes.wintypes.WPARAM,
    ctypes.wintypes.LPARAM,
)

def _wnd_proc(hwnd, msg, wparam, lparam):
    if msg == WM_POWERBROADCAST and wparam == PBT_APMSUSPEND:
        print(f"\n[{time.strftime('%H:%M:%S')}] ⚡ 절전 모드 감지 → 프로그램을 종료합니다.")
        suspend_event.set()
    return ctypes.windll.user32.DefWindowProcW(hwnd, msg, wparam, lparam)

class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style",         ctypes.c_uint),
        ("lpfnWndProc",   WNDPROC),
        ("cbClsExtra",    ctypes.c_int),
        ("cbWndExtra",    ctypes.c_int),
        ("hInstance",     ctypes.wintypes.HINSTANCE),
        ("hIcon",         ctypes.wintypes.HICON),
        ("hCursor",       ctypes.wintypes.HANDLE),
        ("hbrBackground", ctypes.wintypes.HBRUSH),
        ("lpszMenuName",  ctypes.wintypes.LPCWSTR),
        ("lpszClassName", ctypes.wintypes.LPCWSTR),
    ]

def _setup_win32_api():
    """CreateWindowExW / RegisterClassW 에 명시적 argtypes 지정 (64비트 오버플로우 방지)"""
    user32 = ctypes.windll.user32

    user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
    user32.RegisterClassW.restype  = ctypes.c_uint16

    user32.CreateWindowExW.argtypes = [
        ctypes.wintypes.DWORD,    # dwExStyle
        ctypes.wintypes.LPCWSTR,  # lpClassName
        ctypes.wintypes.LPCWSTR,  # lpWindowName
        ctypes.wintypes.DWORD,    # dwStyle
        ctypes.c_int,             # X
        ctypes.c_int,             # Y
        ctypes.c_int,             # nWidth
        ctypes.c_int,             # nHeight
        ctypes.wintypes.HWND,     # hWndParent
        ctypes.wintypes.HMENU,    # hMenu
        ctypes.wintypes.HINSTANCE,# hInstance
        ctypes.wintypes.LPVOID,   # lpParam
    ]
    user32.CreateWindowExW.restype = ctypes.wintypes.HWND

    user32.DefWindowProcW.argtypes = [
        ctypes.wintypes.HWND,
        ctypes.c_uint,
        ctypes.wintypes.WPARAM,
        ctypes.wintypes.LPARAM,
    ]
    user32.DefWindowProcW.restype = ctypes.c_long

    user32.PeekMessageW.argtypes = [
        ctypes.POINTER(ctypes.wintypes.MSG),
        ctypes.wintypes.HWND,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_uint,
    ]
    user32.PeekMessageW.restype = ctypes.wintypes.BOOL

def _run_message_loop():
    _setup_win32_api()
    user32    = ctypes.windll.user32
    hInstance = ctypes.windll.kernel32.GetModuleHandleW(None)
    class_name = "KeepAwakePowerWatcher"

    wnd_proc_cb = WNDPROC(_wnd_proc)   # 콜백을 변수로 유지 (GC 방지)

    wc = WNDCLASSW()
    wc.lpfnWndProc   = wnd_proc_cb
    wc.hInstance     = hInstance
    wc.lpszClassName = class_name
    user32.RegisterClassW(ctypes.byref(wc))

    hwnd = user32.CreateWindowExW(
        WS_EX_TOOLWINDOW, class_name, "KeepAwake",
        WS_OVERLAPPED,
        0, 0, 0, 0,
        None, None, hInstance, None,
    )

    msg = ctypes.wintypes.MSG()
    while not suspend_event.is_set():
        if user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        else:
            time.sleep(0.05)

    user32.DestroyWindow(hwnd)

# ── 메인 ──────────────────────────────────────────────────────
INTERVAL_MINUTES = 5
INTERVAL_SECONDS = INTERVAL_MINUTES * 60

def main():
    prevent_sleep()

    watcher = threading.Thread(target=_run_message_loop, daemon=True)
    watcher.start()

    print("=" * 50)
    print("  💤 절전 방지 프로그램 시작")
    print(f"  ⏱  마우스 이동 간격 : {INTERVAL_MINUTES}분")
    print("  🛑 종료 방법        : Ctrl+C  또는  수동 절전")
    print("=" * 50)

    count = 0
    try:
        while not suspend_event.is_set():
            count += 1
            x, y = get_cursor_pos()
            nudge_mouse(offset=5)
            print(f"[{time.strftime('%H:%M:%S')}] #{count:04d} 마우스 이동 완료 "
                  f"(현재 위치: {x}, {y}) | 다음: {INTERVAL_MINUTES}분 후")

            for _ in range(INTERVAL_SECONDS):
                if suspend_event.is_set():
                    break
                time.sleep(1)

    except KeyboardInterrupt:
        print("\n[종료] Ctrl+C 감지.")

    finally:
        restore_sleep()
        print("[종료] 절전 설정 복원 완료. 프로그램을 종료합니다.")
        sys.exit(0)

if __name__ == "__main__":
    main()
