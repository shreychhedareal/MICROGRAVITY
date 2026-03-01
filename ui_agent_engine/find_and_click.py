import json
import sys
import pyautogui
import time

def main():
    if len(sys.argv) < 2:
        print("Usage: python find_and_click.py <search_term> [json_file]")
        return

    search_term = sys.argv[1].lower()
    json_file = sys.argv[2] if len(sys.argv) > 2 else "agent_memory/predicted_outputs/gui_map_1772138097.json"

    with open(json_file, "r") as f:
        data = json.load(f)

    matches = [e for e in data if search_term in e.get("label", "").lower()]

    if not matches:
        print(f"No element matching '{search_term}' found in the GUI map.")
        return

    # Pick the best match (smallest bounding box = most precise icon)
    best = min(matches, key=lambda e: e["coordinates"]["width"] * e["coordinates"]["height"])

    coords = best["coordinates"]
    center_x = coords["x"] + coords["width"] // 2
    center_y = coords["y"] + coords["height"] // 2

    print(f"Found: {best['label']}")
    print(f"Description: {best.get('description', 'N/A')}")
    print(f"Bounding Box: x={coords['x']}, y={coords['y']}, w={coords['width']}, h={coords['height']}")
    print(f"Center click target: ({center_x}, {center_y})")
    print("Clicking in 2 seconds...")
    time.sleep(2)
    pyautogui.click(center_x, center_y)
    print("Click executed!")

if __name__ == "__main__":
    main()
