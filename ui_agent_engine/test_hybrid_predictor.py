import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from perception.vision_analyzer import VisionAnalyzer
from planning.action_predictor import ActionPredictor
from perception.screen import ScreenObserver

def test_hybrid_predictor():
    print("Initializing Vision & Predictor...")
    vision = VisionAnalyzer()
    predictor = ActionPredictor(vision)
    screen_obs = ScreenObserver()
    
    # Bootstrap using the UIAgent logic (copying it here for the standalone test)
    print("Bootstrapping Static Map...")
    import glob
    json_dir = os.path.join("agent_memory", "predicted_outputs")
    img_dir = os.path.join("agent_memory", "raw_screenshots")
    json_files = glob.glob(os.path.join(json_dir, "gui_map_*.json"))
    
    if json_files:
        latest_json = max(json_files, key=os.path.getctime)
        filename = os.path.basename(latest_json)
        timestamp = filename.replace("gui_map_", "").replace(".json", "")
        raw_image = os.path.join(img_dir, f"capture_{timestamp}.png")
        if os.path.exists(raw_image):
            predictor.load_static_map(latest_json, raw_image)
    
    # 1. Take a fresh screenshot
    print("\nTaking fresh live screenshot...")
    live_screen = screen_obs.capture()
    
    print("\nKeys in Memory:")
    keys = list(predictor.memory.keys())
    
    with open("hybrid_keys.txt", "w") as f:
        f.write("\n".join(keys))
        
    print(f"Wrote {len(keys)} keys to hybrid_keys.txt")
    
    # Just grab the first one to test!
    if keys:
        target_label = keys[0]
    else:
        target_label = "google chrome application icon"
    
    action = {
        "action": "click",
        "target": target_label
    }
    
    print(f"\nTesting Prediction for '{target_label}'...")
    start_time = time.time()
    params = predictor.predict_action_parameters(action, live_screen)
    end_time = time.time()
    
    # Write cleanly to a log file instead of terminal to avoid VLM \r issues
    with open("hybrid_test_results.txt", "w") as f:
        f.write("--- TEST RESULTS ---\n")
        f.write(f"Target: {target_label}\n")
        f.write(f"Resolved Coordinates: {params}\n")
        f.write(f"Execution Time: {(end_time - start_time)*1000:.2f} ms\n")
        
    print(f"Test complete. Wrote to hybrid_test_results.txt. took {(end_time - start_time)*1000:.2f} ms")

if __name__ == '__main__':
    test_hybrid_predictor()
