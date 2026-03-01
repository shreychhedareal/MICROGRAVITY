import os
import sys

# Add parent to path for relative import execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.perception.spatial_understanding.spatial_tool import SpatialUnderstandingTool

def main():
    # Make sure we have an API key, we will pull from env
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Please set GEMINI_API_KEY to test the spatial logic.")
        return

    # Create dummy image to test with
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (600, 400), color=(73, 109, 137))
    d = ImageDraw.Draw(img)
    # Draw a "button"
    d.rectangle([200, 150, 400, 250], fill=(255, 0, 0))
    d.text((250, 200), "Hello World", fill=(255,255,255))
    test_image_path = "test_image.jpg"
    img.save(test_image_path)

    tool = SpatialUnderstandingTool(api_key=api_key)
    
    print("Testing 2D Bounding Boxes...")
    try:
        res_2d = tool.execute(test_image_path, "red rectangle", "2d_bounding_boxes", "output_2d.jpg")
        print("2D Result:", res_2d["results"])
    except Exception as e:
        print("2D Test Failed:", e)

    print("\nTesting Points...")
    try:
        res_pt = tool.execute(test_image_path, "red rectangle", "points", "output_points.jpg")
        print("Points Result:", res_pt["results"])
    except Exception as e:
        print("Points Test Failed:", e)
        
    # Clean up test files
    try:
        os.remove(test_image_path)
    except:
        pass

if __name__ == "__main__":
    main()
