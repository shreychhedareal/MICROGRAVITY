import win32gui
import win32con
import time
from PIL import ImageGrab
import os

def focus_and_capture(title_contains):
    def callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title_contains.lower() in title.lower():
                windows.append((hwnd, title))
                
    windows = []
    win32gui.EnumWindows(callback, windows)
    
    if not windows:
        print(f"No window found containing: {title_contains}")
        return
        
    hwnd, title = windows[0]
    print(f"Focusing: {title}")
    
    # Restore and bring to front
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)
    
    time.sleep(2) # Wait for animation
    
    # Capture the specific window or the foreground
    img = ImageGrab.grab()
    path = os.path.join(os.getcwd(), "cmd_proof.png")
    img.save(path)
    print(f"Saved proof to {path}")

if __name__ == "__main__":
    focus_and_capture("Command Prompt") # Standard title
    focus_and_capture("cmd.exe") # Fallback
