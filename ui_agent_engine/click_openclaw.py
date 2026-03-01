import os
import sys
import time
import pyautogui
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.perception.screen import ScreenObserver
from src.perception.spatial_understanding.spatial_tool import SpatialUnderstandingTool
from src.ui_controller.mouse import MouseController

def main():
    if len(sys.argv) < 2:
        print("Usage: python click_element.py <search_query>")
        return
        
    search_query = sys.argv[1]
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
    mouse = MouseController()

    print(f"Analyzing screen with Gemini for '{search_query}'...")
    try:
        coords = None
        
        print(f"Trying 'points' detection for '{search_query}'...")
        res_pt = spatial_tool.execute(screenshot_path, search_query, "points", None)
        if res_pt.get("results"):
            pt = res_pt["results"][0].get('point', {})
            if 'x' in pt and 'y' in pt:
                coords = (pt['x'], pt['y'])
                print(f"Detected point: {res_pt['results'][0]}")
                
        if not coords:
            print(f"Trying '2d_bounding_boxes' detection for '{search_query}'...")
            res_bbox = spatial_tool.execute(screenshot_path, search_query, "2d_bounding_boxes", None)
            if res_bbox.get("results"):
                box = res_bbox["results"][0]
                # Use center of bounding box
                coords = (box['x'] + box['width']/2, box['y'] + box['height']/2)
                print(f"Detected bounding box: {box}")

        if not coords:
            print(f"Could not find '{search_query}' on the screen.")
            return

        screen_w, screen_h = pyautogui.size()
        target_x = int(coords[0] * screen_w)
        target_y = int(coords[1] * screen_h)

        print(f"Normalized coords: {coords}")
        print(f"Absolute screen coords for click: ({target_x}, {target_y})")

        print("Moving mouse and clicking...")
        mouse.move_and_click(target_x, target_y)
        print("Click performed successfully!")
        
    except Exception as e:
        print(f"Action failed: {e}")

if __name__ == "__main__":
    print("Will run in 3 seconds. Please ensure the target is visible on screen.")
    time.sleep(3)
    main()
