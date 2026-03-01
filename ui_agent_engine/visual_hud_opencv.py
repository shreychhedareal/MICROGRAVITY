import os
import sys
import time
import win32gui
import win32con
import tkinter as tk
import ctypes

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.perception.screen import ScreenObserver
from src.perception.vision_analyzer import VisionAnalyzer

class FastOverlayHUD:
    """A high-performance transparent overlay for continuous bounding box rendering."""
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "white")
        self.root.config(bg="white")
        
        # Click-through: To make the window completely ignore mouse clicks
        hwnd = win32gui.GetParent(self.root.winfo_id())
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED)
        
        self.sw = self.root.winfo_screenwidth()
        self.sh = self.root.winfo_screenheight()
        self.root.geometry(f"{self.sw}x{self.sh}+0+0")
        
        self.canvas = tk.Canvas(self.root, bg="white", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

    def clear(self):
        self.canvas.delete("all")

    def draw_elements(self, elements, fps=0.0):
        self.clear()
        
        # Draw HUD stats
        self.canvas.create_text(
            150, 30,
            text=f"UI Labeling System Active (FPS: {fps:.1f})", 
            fill="#00ff00", font=("Consolas", 14, "bold")
        )
        self.canvas.create_text(
            150, 50,
            text=f"Total Extracted Elements: {len(elements)}", 
            fill="#00ff00", font=("Consolas", 12)
        )
        
        for el in elements:
            x, y, w, h = el['x'], el['y'], el['width'], el['height']
            color = el['color']
            label = el['label']
            
            # Reduce clutter: Only draw label for dynamic or large structural things
            # to prevent screen from becoming unreadable text soup
            if w > 20 and h > 20:
                self.canvas.create_rectangle(x, y, x+w, y+h, outline=color, width=2)
                
                # Background for text
                if label != "STRUCTURAL":
                    lbl_id = self.canvas.create_text(x, max(0, y-15), text=label, fill=color, font=("Consolas", 8, "bold"), anchor="nw")
                    
        self.root.update()

    def process_events(self):
        self.root.update()

def main():
    print("Starting OpenCV Live Labeling System...")
    print("WARNING: This will run until you hit Ctrl+C or close this terminal.")
    
    hud = FastOverlayHUD()
    screen_obs = ScreenObserver()
    vision = VisionAnalyzer()
    
    prev_frame = None
    
    try:
        while True:
            start_time = time.time()
            
            # 1. Capture screen quickly via mss -> numpy
            curr_frame = screen_obs.capture_as_cv2()
            
            # 2. Run OpenCV structure & change detection
            elements = vision.detect_ui_elements_fast(curr_frame, prev_frame)
            
            # 3. Update HUD
            fps = 1.0 / (time.time() - start_time)
            hud.draw_elements(elements, fps=fps)
            
            prev_frame = curr_frame
            
            # Tiny sleep to not lock the CPU 100%
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("Shutting down live labeling...")
    finally:
        hud.root.destroy()

if __name__ == "__main__":
    main()
