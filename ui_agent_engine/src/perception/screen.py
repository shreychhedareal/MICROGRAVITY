import mss
import mss.tools
from PIL import Image
import os
import time
from typing import Optional, Tuple, List
import ctypes
import win32gui
import win32ui
import win32con

class WindowObserver:
    """
    Captures specific application windows (even if they are in the background)
    using the Windows Graphics Device Interface (GDI) and PrintWindow API.
    """
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def get_window_titles(self) -> List[str]:
        """Returns a list of all visible window titles."""
        titles = []
        def enum_windows_proc(hwnd, lParam):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                titles.append(win32gui.GetWindowText(hwnd))
            return True
        win32gui.EnumWindows(enum_windows_proc, None)
        return titles

    def capture_window_by_title(self, window_title: str, filename: Optional[str] = None) -> Optional[str]:
        """
        Takes a screenshot of the specified window's image buffer.
        """
        # Ensure Windows knows we are DPI aware 
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except:
            pass

        hwnd = win32gui.FindWindow(None, window_title)
        actual_title = window_title
        
        if not hwnd:
            for title in self.get_window_titles():
                if window_title.lower() in title.lower():
                    hwnd = win32gui.FindWindow(None, title)
                    actual_title = title
                    break
            
            if not hwnd:
                print(f"[WindowObserver] Error: Window '{window_title}' not found.")
                return None

        # Check if minimized and restore temporarily if needed for correct buffer size
        if win32gui.IsIconic(hwnd):
           win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
           time.sleep(0.1)

        if filename is None:
            filename = f"window_{int(time.time()*1000)}.png"
        filepath = os.path.join(self.output_dir, filename)

        # Get client rect for the actual internal UI area
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        width = right - left
        height = bottom - top

        if width <= 0 or height <= 0:
            print(f"[WindowObserver] Error: Window '{actual_title}' has invalid dimensions.")
            return None

        # To capture obscured windows perfectly on Windows 10/11, we must use PrintWindow
        # with the PW_RENDERFULLCONTENT flag (3), which forces the DWM to compose it.
        # Direct BitBlt often yields black screens for obscured hardware-accelerated apps like Chrome.
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()

        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
        saveDC.SelectObject(saveBitMap)

        # PW_RENDERFULLCONTENT = 3
        # PW_CLIENTONLY = 1
        result = ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3 | 1) # Full content + Client only

        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)

        if len(bmpstr) > 0 and result != 0:
             im = Image.frombuffer(
                 'RGB',
                 (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                 bmpstr, 'raw', 'BGRX', 0, 1)
             im.save(filepath)
             print(f"[WindowObserver] Successfully captured full background window buffer '{actual_title}' to {filepath}")
        else:
             print(f"[WindowObserver] Error: PrintWindow failed or returned empty buffer for '{actual_title}'.")
             filepath = None

        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)

        return filepath

class ScreenObserver:
    """
    Handles fast screenshot capture using mss.
    """
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.sct = mss.mss()
        
    def capture(self, filename: Optional[str] = None, region: Optional[Tuple[int, int, int, int]] = None) -> str:
        """
        Captures the screen or a specific region.
        Region is defined as (left, top, width, height).
        Returns the path to the saved image.
        """
        if filename is None:
            filename = f"screenshot_{int(time.time()*1000)}.png"
            
        filepath = os.path.join(self.output_dir, filename)
        
        monitor = self.sct.monitors[1] # Primary monitor usually
        if region:
            monitor = {
                "left": monitor["left"] + region[0],
                "top": monitor["top"] + region[1],
                "width": region[2],
                "height": region[3]
            }

        try:
            screenshot = self.sct.grab(monitor)
            mss.tools.to_png(screenshot.rgb, screenshot.size, output=filepath)
            print(f"[ScreenObserver] Successfully captured screenshot to {filepath}")
            return filepath
        except Exception as e:
            print(f"[ScreenObserver] Error during screen capture: {e}")
            return None
        
    def capture_as_pil(self, region: Optional[Tuple[int, int, int, int]] = None) -> Image.Image:
        """
        Captures the screen and returns a PIL Image object directly (useful for in-memory processing).
        """
        monitor = self.sct.monitors[1]
        if region:
            monitor = {
                "left": monitor["left"] + region[0],
                "top": monitor["top"] + region[1],
                "width": region[2],
                "height": region[3]
            }
            
        screenshot = self.sct.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        return img

    def capture_as_cv2(self, region: Optional[Tuple[int, int, int, int]] = None):
        """
        Captures the screen and returns a numpy array (BGR format for OpenCV).
        """
        import numpy as np
        import cv2
        monitor = self.sct.monitors[1]
        if region:
            monitor = {
                "left": monitor["left"] + region[0],
                "top": monitor["top"] + region[1],
                "width": region[2],
                "height": region[3]
            }
        screenshot = self.sct.grab(monitor)
        # mss returns BGRA, convert to BGR for opencv
        img = np.array(screenshot)
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)