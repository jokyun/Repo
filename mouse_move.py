"""
keep_awake.py
Windows 절전 모드 방지 - 5분마다 마우스를 미세하게 움직입니다.
Git-bash 환경에서 실행: python keep_awake.py
종료: Ctrl+C
"""

import time
import sys
import ctypes
import ctypes.wintypes

# pyautogui 없이 ctypes로 직접 마우스 제어 (외부 라이브러리 불필요)

# Windows API 구조체
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def get_cursor_pos():
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

def move_cursor(x, y):
    ctypes.windll.user32.SetCursorPos(x, y)

def nudge_mouse(offset=5):
    """현재 위치에서 살짝 움직였다가 원래 자리로 복귀"""
    x, y = get_cursor_pos()
    move_cursor(x + offset, y + offset)
    time.sleep(0.1)
    move_cursor(x, y)

def prevent_sleep():
    """Windows가 절전/화면보호기로 진입하지 못하도록 ES 플래그 설정"""
    ES_CONTINUOUS       = 0x80000000
    ES_SYSTEM_REQUIRED  = 0x00000001
    ES_DISPLAY_REQUIRED = 0x00000002
    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
    )

def restore_sleep():
    """종료 시 절전 설정 복원"""
    ES_CONTINUOUS = 0x80000000
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)

INTERVAL_MINUTES = 5
INTERVAL_SECONDS = INTERVAL_MINUTES * 60

def main():
    prevent_sleep()
    print("=" * 45)
    print("  💤 절전 방지 프로그램 시작")
    print(f"  ⏱  마우스 이동 간격: {INTERVAL_MINUTES}분")
    print("  🛑 종료하려면 Ctrl+C 를 누르세요")
    print("=" * 45)

    count = 0
    try:
        while True:
            count += 1
            x, y = get_cursor_pos()
            nudge_mouse(offset=5)
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] #{count:04d} 마우스 이동 완료 "
                  f"(현재 위치: {x}, {y}) | 다음: {INTERVAL_MINUTES}분 후")
            time.sleep(INTERVAL_SECONDS)

    except KeyboardInterrupt:
        restore_sleep()
        print("\n[종료] 절전 방지 해제 완료. 프로그램을 종료합니다.")
        sys.exit(0)

if __name__ == "__main__":
    main()
