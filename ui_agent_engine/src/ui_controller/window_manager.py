import win32gui
import win32con
import time
from typing import Optional, List, Tuple

class WindowManager:
    """
    Handles OS-level window management tasks such as move, resize, minimize, and maximize.
    Provides a programmatic bridge for human-like window manipulation.
    """
    def __init__(self):
        pass

    def get_hwnd_by_title(self, partial_title: str) -> Optional[int]:
        """Finds a window handle by partial title match."""
        hwnd_list = []
        def enum_handler(hwnd, lparam):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if partial_title.lower() in title.lower():
                    hwnd_list.append(hwnd)
            return True
        
        win32gui.EnumWindows(enum_handler, None)
        return hwnd_list[0] if hwnd_list else None

    def minimize(self, hwnd: int) -> bool:
        """Minimizes the specified window (Shrink)."""
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            return True
        except Exception as e:
            print(f"[WindowManager] Error minimizing window {hwnd}: {e}")
            return False

    def maximize(self, hwnd: int) -> bool:
        """Maximizes the specified window (Expand)."""
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            return True
        except Exception as e:
            print(f"[WindowManager] Error maximizing window {hwnd}: {e}")
            return False

    def restore(self, hwnd: int) -> bool:
        """Restores a minimized/maximized window to its normal state."""
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            return True
        except Exception as e:
            print(f"[WindowManager] Error restoring window {hwnd}: {e}")
            return False

    def resize(self, hwnd: int, width: int, height: int, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Resizes the specified window. Optionally moves it."""
        try:
            curr_rect = win32gui.GetWindowRect(hwnd)
            new_x = x if x is not None else curr_rect[0]
            new_y = y if y is not None else curr_rect[1]
            win32gui.MoveWindow(hwnd, new_x, new_y, width, height, True)
            return True
        except Exception as e:
            print(f"[WindowManager] Error resizing window {hwnd}: {e}")
            return False

    def get_window_rect(self, hwnd: int) -> Optional[Tuple[int, int, int, int]]:
        """Returns the window bounds as (x, y, width, height)."""
        try:
            rect = win32gui.GetWindowRect(hwnd)
            return (rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])
        except Exception as e:
            print(f"[WindowManager] Error getting rect for window {hwnd}: {e}")
            return None

    def focus_window(self, hwnd: int) -> bool:
        """Brings the window to the foreground."""
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.3)  # Human-like focus delay
            return True
        except Exception as e:
            print(f"[WindowManager] Error focusing window {hwnd}: {e}")
            return False
