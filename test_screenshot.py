import os
from ui_agent_prototype.perception import PerceptionEngine

def main():
    print("Initializing Perception Engine to capture screenshot...")
    
    # We will save the image to the current root director
    perception = PerceptionEngine(output_dir=".") 
    
    # Capture the screenshot
    image_path = perception.capture_screenshot()
    
    if image_path:
        print(f"Screenshot successfully captured and saved at: {os.path.abspath(image_path)}")
    else:
        print("Failed to capture screenshot.")

if __name__ == "__main__":
    main()
