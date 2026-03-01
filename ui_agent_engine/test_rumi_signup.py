"""
Test script: Open Chrome, navigate to rumi.social, and sign up with Google account.
Uses the UI Agent's modules directly with coordinate logging.
"""
import sys
import os
import time
import subprocess
import json

# Add the 'src' directory to the Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from ui_controller.mouse import MouseController
from ui_controller.keyboard import KeyboardController
from perception.screen import ScreenObserver, WindowObserver
from perception.vision_analyzer import VisionAnalyzer

# --- Coordinate Log ---
coordinate_log = []

def log_coords(step_name, coords, extra_info=""):
    """Logs coordinates for every action."""
    entry = {
        "step": step_name,
        "coords": coords,
        "extra": extra_info,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    coordinate_log.append(entry)
    print(f"  📍 COORDS LOG | Step: {step_name} | Coords: {coords} | {extra_info}")

def save_coord_log():
    """Saves the full coordinate log to a JSON file."""
    log_path = os.path.join("agent_memory", "coord_log_rumi.json")
    os.makedirs("agent_memory", exist_ok=True)
    with open(log_path, "w") as f:
        json.dump(coordinate_log, f, indent=2)
    print(f"\n✅ Coordinate log saved to: {log_path}")

# --- Main Flow ---
def main():
    print("=" * 60)
    print("  UI AGENT TEST: Chrome → rumi.social → Google Sign Up")
    print("=" * 60)

    # Initialize modules
    mouse = MouseController(base_speed=1.0)
    keyboard = KeyboardController(wpm=80)
    screen = ScreenObserver(output_dir='agent_memory/screenshots')
    window_obs = WindowObserver(output_dir='agent_memory/screenshots')
    vision = VisionAnalyzer()

    # =========================================================
    # STEP 1: Open Google Chrome
    # =========================================================
    print("\n--- STEP 1: Opening Google Chrome ---")
    subprocess.Popen(["cmd", "/c", "start", "chrome", "--new-window", "https://rumi.social"], shell=True)
    print("[...] Waiting for Chrome and rumi.social to fully load...")
    time.sleep(10)  # Generous wait for page load
    
    # Smart wait: keep re-capturing until page is no longer "Loading..."
    for attempt in range(5):
        temp_shot = window_obs.capture_window_by_title("Chrome", filename=f"rumi_loading_check_{attempt}.png")
        if temp_shot:
            state_text = vision.extract_ui_state(temp_shot)
            if "loading" not in state_text.lower() or attempt >= 4:
                print(f"[OK] Page appears loaded (attempt {attempt+1})")
                break
            else:
                print(f"[...] Page still loading, waiting 3 more seconds (attempt {attempt+1})...")
                time.sleep(3)
        else:
            time.sleep(3)
    
    print("[OK] Chrome launched with rumi.social")

    # =========================================================
    # STEP 2: Capture & Analyze the Chrome window
    # =========================================================
    print("\n--- STEP 2: Capturing Chrome window ---")
    
    # Try to capture Chrome's window buffer
    chrome_screenshot = window_obs.capture_window_by_title("Chrome", filename="rumi_step2_chrome.png")
    if not chrome_screenshot:
        print("[FALLBACK] Chrome window not found by title, capturing full screen...")
        chrome_screenshot = screen.capture(filename="rumi_step2_fullscreen.png")
    
    # Analyze UI state
    print("\n--- STEP 2b: Analyzing UI state ---")
    ui_state = vision.extract_ui_state(chrome_screenshot)
    print(f"[VLM UI State]:\n{ui_state[:500]}...")
    
    # =========================================================
    # STEP 3: Find and click "Sign Up" or "Sign in with Google" button
    # =========================================================
    print("\n--- STEP 3: Looking for Sign Up / Google Sign In button ---")
    
    # First, let's look for any sign-up related button
    from PIL import Image
    img = Image.open(chrome_screenshot)
    img_w, img_h = img.size
    print(f"[INFO] Screenshot dimensions: {img_w}x{img_h}")

    # Try to find sign-up / login / Google sign-in buttons
    search_targets = [
        "user profile avatar icon in the top right corner",
        "person or user icon in the top navigation bar",
        "circular avatar or profile picture icon in the top right",
        "account icon or login icon in the header",
        "Start Video Chat button",
    ]
    
    found_target = None
    found_coords = None
    
    for target_desc in search_targets:
        print(f"\n  🔍 Searching for: '{target_desc}'")
        bbox_str = vision.find_element_bbox(chrome_screenshot, target_desc)
        print(f"  📦 VLM Response: {bbox_str}")
        
        if "NOT FOUND" not in bbox_str.upper():
            try:
                clean = bbox_str.replace('[', '').replace(']', '').strip()
                ymin, xmin, ymax, xmax = map(int, clean.split(','))
                
                # Convert normalized 0-1000 coords to actual pixels
                px_xmin = int((xmin / 1000) * img_w)
                px_xmax = int((xmax / 1000) * img_w)
                px_ymin = int((ymin / 1000) * img_h)
                px_ymax = int((ymax / 1000) * img_h)
                
                center_x = (px_xmin + px_xmax) // 2
                center_y = (px_ymin + px_ymax) // 2
                
                log_coords(f"Found: {target_desc}", 
                          {"normalized": [ymin, xmin, ymax, xmax],
                           "pixel_box": {"left": px_xmin, "top": px_ymin, "right": px_xmax, "bottom": px_ymax},
                           "center": {"x": center_x, "y": center_y}},
                          f"Image size: {img_w}x{img_h}")
                
                found_target = target_desc
                found_coords = (center_x, center_y)
                print(f"  ✅ FOUND '{target_desc}' at center pixel ({center_x}, {center_y})")
                break
            except Exception as e:
                print(f"  ⚠️ Parse error: {e}")
                continue
    
    if not found_coords:
        print("\n⚠️ Could not find a sign-up button. Saving what we have...")
        save_coord_log()
        return

    # =========================================================
    # STEP 4: Translate to desktop coordinates and click
    # =========================================================
    print(f"\n--- STEP 4: Clicking '{found_target}' ---")
    
    import win32gui
    # Find the Chrome window handle for coordinate translation
    hwnd = None
    for title in window_obs.get_window_titles():
        if "chrome" in title.lower():
            hwnd = win32gui.FindWindow(None, title)
            break
    
    if hwnd:
        client_origin = win32gui.ClientToScreen(hwnd, (0, 0))
        desktop_x = found_coords[0] + client_origin[0]
        desktop_y = found_coords[1] + client_origin[1]
        log_coords("Desktop translation", 
                  {"client_origin": client_origin,
                   "relative": {"x": found_coords[0], "y": found_coords[1]},
                   "absolute": {"x": desktop_x, "y": desktop_y}})
        
        # Bring Chrome to foreground
        import win32con
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.5)
        except Exception as e:
            print(f"  ⚠️ Could not foreground Chrome: {e}")
        
        print(f"  🖱️ Moving to desktop ({desktop_x}, {desktop_y}) and clicking...")
        mouse.move_and_click(desktop_x, desktop_y, human_like=True)
        log_coords("Clicked sign-up button", {"x": desktop_x, "y": desktop_y})
    else:
        print("  ⚠️ Chrome window not found for translation, clicking relative coords...")
        mouse.move_and_click(found_coords[0], found_coords[1], human_like=True)
        log_coords("Clicked sign-up (relative)", {"x": found_coords[0], "y": found_coords[1]})
    
    time.sleep(3)  # Wait for page transition

    # =========================================================
    # STEP 5: Capture after click & look for Google Sign In
    # =========================================================
    print("\n--- STEP 5: Capturing state after click ---")
    after_screenshot = window_obs.capture_window_by_title("Chrome", filename="rumi_step5_after_click.png")
    if not after_screenshot:
        after_screenshot = screen.capture(filename="rumi_step5_fullscreen.png")
    
    ui_state_after = vision.extract_ui_state(after_screenshot)
    print(f"[VLM UI State After Click]:\n{ui_state_after[:500]}...")

    # Look for Google sign-in button on the new page
    img2 = Image.open(after_screenshot)
    img2_w, img2_h = img2.size

    google_targets = [
        "Continue with Google button",
        "Sign in with Google button",
        "Google button or icon",
        "Sign up with Google",
    ]
    
    google_coords = None
    for gt in google_targets:
        print(f"\n  🔍 Searching for: '{gt}'")
        bbox_str = vision.find_element_bbox(after_screenshot, gt)
        print(f"  📦 VLM Response: {bbox_str}")
        
        if "NOT FOUND" not in bbox_str.upper():
            try:
                clean = bbox_str.replace('[', '').replace(']', '').strip()
                ymin, xmin, ymax, xmax = map(int, clean.split(','))
                
                px_xmin = int((xmin / 1000) * img2_w)
                px_xmax = int((xmax / 1000) * img2_w)
                px_ymin = int((ymin / 1000) * img2_h)
                px_ymax = int((ymax / 1000) * img2_h)
                
                center_x = (px_xmin + px_xmax) // 2
                center_y = (px_ymin + px_ymax) // 2
                
                log_coords(f"Found: {gt}",
                          {"normalized": [ymin, xmin, ymax, xmax],
                           "pixel_box": {"left": px_xmin, "top": px_ymin, "right": px_xmax, "bottom": px_ymax},
                           "center": {"x": center_x, "y": center_y}},
                          f"Image size: {img2_w}x{img2_h}")
                
                google_coords = (center_x, center_y)
                print(f"  ✅ FOUND '{gt}' at center pixel ({center_x}, {center_y})")
                break
            except Exception as e:
                print(f"  ⚠️ Parse error: {e}")
                continue
    
    if google_coords and hwnd:
        client_origin = win32gui.ClientToScreen(hwnd, (0, 0))
        desktop_x = google_coords[0] + client_origin[0]
        desktop_y = google_coords[1] + client_origin[1]
        log_coords("Google button desktop coords", {"x": desktop_x, "y": desktop_y})
        
        print(f"  🖱️ Clicking 'Sign in with Google' at ({desktop_x}, {desktop_y})...")
        mouse.move_and_click(desktop_x, desktop_y, human_like=True)
        log_coords("Clicked Google sign-in", {"x": desktop_x, "y": desktop_y})
        time.sleep(4)
        
        # Capture final state
        print("\n--- STEP 6: Capturing final state (Google auth popup) ---")
        final_screenshot = screen.capture(filename="rumi_step6_google_auth.png")
        final_state = vision.extract_ui_state(final_screenshot)
        print(f"[VLM Final State]:\n{final_state[:500]}...")
        log_coords("Final state captured", {"screenshot": final_screenshot})
    else:
        print("  ⚠️ Could not find Google sign-in button on this page.")

    # =========================================================
    # Save coordinate log
    # =========================================================
    save_coord_log()
    
    print("\n" + "=" * 60)
    print("  📋 FULL COORDINATE LOG:")
    print("=" * 60)
    for entry in coordinate_log:
        print(f"  [{entry['timestamp']}] {entry['step']}")
        print(f"    Coords: {json.dumps(entry['coords'], indent=6)}")
        if entry['extra']:
            print(f"    Extra: {entry['extra']}")
        print()

if __name__ == "__main__":
    main()
