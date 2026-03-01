import os
import sys
import time
import pyautogui
import tkinter as tk
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.perception.screen import ScreenObserver
from src.perception.spatial_understanding.spatial_tool import SpatialUnderstandingTool

class UIAgentHUD:
    """A transparent full-screen overlay to show Agent processing live."""
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        
        # Transparent background setup for Windows
        self.root.attributes("-transparentcolor", "white")
        self.root.config(bg="white")
        
        self.sw = self.root.winfo_screenwidth()
        self.sh = self.root.winfo_screenheight()
        self.root.geometry(f"{self.sw}x{self.sh}+0+0")
        
        self.canvas = tk.Canvas(self.root, bg="white", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Status text
        self.text_id = self.canvas.create_text(
            self.sw // 2, 100,
            text="UI Agent: Booting...", 
            fill="#00ff00", font=("Consolas", 36, "bold"), justify=tk.CENTER
        )
        bbox = self.canvas.bbox(self.text_id)
        self.bg_id = self.canvas.create_rectangle(bbox[0]-20, bbox[1]-10, bbox[2]+20, bbox[3]+10, fill="black", outline="black")
        self.canvas.tag_lower(self.bg_id, self.text_id)

    def sleep(self, seconds):
        """Sleeps while keeping the Tkinter window responsive and updating."""
        end_time = time.time() + seconds
        while time.time() < end_time:
            self.root.update()
            time.sleep(0.01)

    def update_text(self, text, color="#00ff00"):
        self.canvas.itemconfig(self.text_id, text=text, fill=color)
        bbox = self.canvas.bbox(self.text_id)
        self.canvas.coords(self.bg_id, bbox[0]-20, bbox[1]-10, bbox[2]+20, bbox[3]+10)
        self.root.update()

    def draw_box(self, x, y, w, h, label="TARGET"):
        self.canvas.create_rectangle(x, y, x+w, y+h, outline="red", width=8)
        
        cx, cy = x + w/2, y + h/2
        self.canvas.create_line(cx-20, cy, cx+20, cy, fill="red", width=3)
        self.canvas.create_line(cx, cy-20, cx, cy+20, fill="red", width=3)
        
        # Label bg
        lbl_id = self.canvas.create_text(x, y-20, text=label, fill="#00ff00", font=("Consolas", 18, "bold"), anchor="sw")
        l_bbox = self.canvas.bbox(lbl_id)
        if l_bbox:
            l_bg = self.canvas.create_rectangle(l_bbox[0]-5, l_bbox[1]-2, l_bbox[2]+5, l_bbox[3]+2, fill="black", outline="black")
            self.canvas.tag_lower(l_bg, lbl_id)
        
        self.root.update()

    def draw_point(self, x, y, label="TARGET"):
        r = 15
        self.canvas.create_oval(x-r, y-r, x+r, y+r, outline="red", width=6)
        self.canvas.create_line(x-r*2, y, x+r*2, y, fill="red", width=3)
        self.canvas.create_line(x, y-r*2, x, y+r*2, fill="red", width=3)
        
        lbl_id = self.canvas.create_text(x, y-30, text=label, fill="#00ff00", font=("Consolas", 18, "bold"), anchor="s")
        l_bbox = self.canvas.bbox(lbl_id)
        if l_bbox:
            l_bg = self.canvas.create_rectangle(l_bbox[0]-5, l_bbox[1]-2, l_bbox[2]+5, l_bbox[3]+2, fill="black", outline="black")
            self.canvas.tag_lower(l_bg, lbl_id)
            
        self.root.update()

    def close(self):
        self.root.destroy()

def main():
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        print("Error: GEMINI_API_KEY not set.")
        return

    hud = UIAgentHUD()
    
    hud.update_text("UI Agent: Launching HUD... Open Telegram now!")
    hud.sleep(3.0)
    
    for i in range(3, 0, -1):
        hud.update_text(f"UI Agent: Taking screen capture in {i}...")
        hud.sleep(1.0)

    hud.update_text("UI Agent: Capturing live screen...", "#00ffff")
    hud.sleep(0.5)
    
    screen_obs = ScreenObserver()
    screenshot_path = screen_obs.capture()
    
    hud.update_text("UI Agent: Analyzing screen with AI models for 'openclaw chat'...", "#ff00ff")
    hud.sleep(0.1)
    
    spatial_tool = SpatialUnderstandingTool(api_key=api_key)
    coords = None
    bbox_data = None
    point_data = None
    
    hud.update_text("UI Agent: Trying 2D Bounding Boxes detection...", "#ffaa00")
    hud.sleep(0.1)
    try:
        res_bbox = spatial_tool.execute(screenshot_path, "openclaw chat", "2d_bounding_boxes", None)
        if res_bbox.get("results"):
            box = res_bbox["results"][0]
            coords = (box['x'] + box['width']/2, box['y'] + box['height']/2)
            bbox_data = box
    except:
        pass

    if not coords:
        hud.update_text("UI Agent: Fallback to Points detection...", "#ffaa00")
        hud.sleep(0.1)
        try:
            res_pt = spatial_tool.execute(screenshot_path, "openclaw chat", "points", None)
            if res_pt.get("results"):
                pt = res_pt["results"][0].get('point', {})
                if 'x' in pt and 'y' in pt:
                    coords = (pt['x'], pt['y'])
                    point_data = pt
        except:
            pass

    if not coords:
        hud.update_text("UI Agent: Critical failure. Target 'openclaw chat' not found on screen.", "#ff0000")
        hud.sleep(4.0)
        hud.close()
        return

    screen_w, screen_h = pyautogui.size()
    target_x = int(coords[0] * screen_w)
    target_y = int(coords[1] * screen_h)
    
    hud.update_text(f"UI Agent: Target locked at ({target_x}, {target_y})!", "#00ff00")
    
    if bbox_data:
        x_px = int(bbox_data['x'] * screen_w)
        y_px = int(bbox_data['y'] * screen_h)
        w_px = int(bbox_data['width'] * screen_w)
        h_px = int(bbox_data['height'] * screen_h)
        hud.draw_box(x_px, y_px, w_px, h_px, "OPENCLAW CHAT")
    else:
        hud.draw_point(target_x, target_y, "OPENCLAW CHAT")

    hud.sleep(2.0)
    
    hud.update_text("UI Agent: Initiating manual override. Moving mouse...", "#ffaa00")
    
    # Custom loop to move mouse while keeping Tkinter updated
    start_x, start_y = pyautogui.position()
    duration = 2.0
    steps = 50
    for i in range(1, steps + 1):
        t = i / steps
        # easeInOutQuad calculation
        ease = 2 * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 2) / 2
        
        cur_x = start_x + (target_x - start_x) * ease
        cur_y = start_y + (target_y - start_y) * ease
        pyautogui.moveTo(cur_x, cur_y)
        hud.sleep(duration / steps)
    
    hud.update_text("UI Agent: Performing Click action!", "#ff0000")
    hud.sleep(0.5)
    pyautogui.click(button='left')
    
    hud.update_text("UI Agent: Actions complete. Shutting down.", "#00ff00")
    hud.sleep(3.0)
    hud.close()

if __name__ == "__main__":
    main()
