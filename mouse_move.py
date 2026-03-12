import pyautogui
import time

while True:
    pyautogui.moveRel(1, 0)   # 마우스 오른쪽으로 1px
    pyautogui.moveRel(-1, 0)  # 다시 원위치
    print("keep alive")
    time.sleep(300)  # 5분
