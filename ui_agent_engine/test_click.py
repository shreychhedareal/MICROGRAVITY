import pyautogui
import time

x = 849
y = 745

print(f"Moving mouse to ({x}, {y}) in 2 seconds...")
time.sleep(2)
pyautogui.click(x, y)
print("Click executed.")
