import os
import sys
import time
import pyautogui
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.perception.screen import ScreenObserver
from src.perception.spatial_understanding.spatial_tool import SpatialUnderstandingTool

def main():
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        print("Error: GEMINI_API_KEY not set.")
        return

    print("Capturing live screen...")
    screen_obs = ScreenObserver()
    screenshot_path = screen_obs.capture()
    print(f"Screenshot saved to {screenshot_path}")

    spatial_tool = SpatialUnderstandingTool(api_key=api_key)

    print("Analyzing screen with Gemini for 'openclaw chat'...")
    try:
        coords = None
        
        print("Trying 'points' detection for 'openclaw chat'...")
        res_pt = spatial_tool.execute(screenshot_path, "openclaw chat", "points", None)
        if res_pt.get("results"):
            pt = res_pt["results"][0].get('point', {})
            if 'x' in pt and 'y' in pt:
                coords = (pt['x'], pt['y'])
                
        if not coords:
            print("Trying '2d_bounding_boxes' detection for 'openclaw chat'...")
            res_bbox = spatial_tool.execute(screenshot_path, "openclaw chat", "2d_bounding_boxes", None)
            if res_bbox.get("results"):
                box = res_bbox["results"][0]
                coords = (box['x'] + box['width']/2, box['y'] + box['height']/2)

        if not coords:
            print("Fallback: Trying point detection for just 'openclaw'...")
            res_pt_fb = spatial_tool.execute(screenshot_path, "openclaw", "points", None)
            if res_pt_fb.get("results"):
                pt = res_pt_fb["results"][0].get('point', {})
                if 'x' in pt and 'y' in pt:
                    coords = (pt['x'], pt['y'])

        if not coords:
            print("Could not find 'openclaw chat' on the screen.")
            return

        screen_w, screen_h = pyautogui.size()
        target_x = int(coords[0] * screen_w)
        target_y = int(coords[1] * screen_h)

        print(f"Detected coordinates. Goal: ({target_x}, {target_y})")
        
        # Make the movement highly visible!
        print("Starting slow visible movement to the target in 1 second...")
        time.sleep(1)
        
        # Get current mouse position
        start_x, start_y = pyautogui.position()
        print(f"Moving from ({start_x}, {start_y}) to ({target_x}, {target_y}) over 3.0 seconds...")
        
        # Use native PyAutoGUI to ensure it's a smooth, visible slide
        pyautogui.moveTo(target_x, target_y, duration=3.0, tween=pyautogui.easeInOutQuad)
        
        print("Cursor is at target! Clicking now...")
        time.sleep(0.5)
        pyautogui.click(button='left')
        print("Click performed successfully!")
        
    except Exception as e:
        print(f"Action failed: {e}")

if __name__ == "__main__":
    print("=====================================================")
    print("WARNING: Script will start in exactly 10 SECONDS.")
    print("1. Switch to the Telegram window NOW.")
    print("2. Make sure 'openclaw chat' is visible.")
    print("3. Take your hands off the mouse and watch the cursor.")
    print("=====================================================")
    for i in range(10, 0, -1):
        print(f"Starting in {i}...")
        time.sleep(1)
    print("GO!")
    main()
