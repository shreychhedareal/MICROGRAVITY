import os
from dotenv import load_dotenv
from PIL import Image
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

class VisionAnalyzer:
    """
    Acts as the hook bridging visual capture and a Vision-Language Model (VLM).
    Uses the modern google-genai SDK for Gemini 1.5/2.5 Flash spatial understanding.
    """
    def __init__(self, model_name: str = "gemini-3-flash-preview"):
        self.model_name = model_name
        self.is_ready = True
        
        # Initialize Google GenAI client (picks up GEMINI_API_KEY from environment)
        self.client = genai.Client()

    def find_element_bbox(self, image_path: str, element_description: str) -> str:
        """
        Uses the new SpatialUnderstandingTool to find the element.
        To maintain backward compatibility with ActionPredictor, we convert the
        normalized [x, y, width, height] back to the [ymin, xmin, ymax, xmax] 0-1000 format.
        """
        print(f"[VLM] Finding bounding box for '{element_description}' in {image_path} using Spatial Tool")
        
        try:
            # Lazy import to avoid circular dependencies if any
            from .spatial_understanding.spatial_tool import SpatialUnderstandingTool
            
            # The tool pulls GEMINI_API_KEY from environment automatically
            spatial_tool = SpatialUnderstandingTool()
            
            # Get 2d bounding boxes
            res = spatial_tool.execute(image_path, element_description, "2d_bounding_boxes")
            
            if res.get("success") and res.get("results"):
                # Take the first best match
                box = res["results"][0]
                
                # Spatial tool returns normalized 0.0-1.0 coords: x, y, width, height
                xmin = int(box["x"] * 1000)
                ymin = int(box["y"] * 1000)
                xmax = int((box["x"] + box["width"]) * 1000)
                ymax = int((box["y"] + box["height"]) * 1000)
                
                # Ensure bounds
                xmin, ymin = max(0, xmin), max(0, ymin)
                xmax, ymax = min(1000, xmax), min(1000, ymax)
                
                return f"[{ymin}, {xmin}, {ymax}, {xmax}]"
            else:
                return "NOT FOUND"
                
        except Exception as e:
            print(f"[VLM ERROR] Failed to find bounding box via Spatial Tool: {e}")
            return "NOT FOUND"

    def extract_ui_state(self, image_path: str) -> str:
        """
        Uses VLM to extract a structured representation of the current screen state.
        This helps the agent understand what windows/buttons are currently visible.
        """
        print(f"[VLM] Extracting complete UI state from {image_path}")
        try:
            img = Image.open(image_path)
            prompt = "Describe the UI state of this screen. What windows, applications, and important elements are visible? Provide a structured summary."
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[img, prompt]
            )
            return response.text
        except Exception as e:
            print(f"[VLM ERROR] Failed to extract UI state: {e}")
            return ""
        
    def visual_diff(self, image_path1: str, image_path2: str, action_context: dict = None) -> bool:
        """
        Checks if two screen states are meaningfully different relative to the intended action.
        """
        print(f"[VLM] Evaluating Semantic Success: {image_path1} -> {image_path2}")
        try:
            img1 = Image.open(image_path1)
            img2 = Image.open(image_path2)
            
            action_type = action_context.get('action', 'unknown') if action_context else 'unknown'
            target = action_context.get('target', action_context.get('text', 'unknown')) if action_context else 'unknown'
            intent = action_context.get('description', 'A meaningful UI state change.') if action_context else 'A meaningful UI state change.'
            
            prompt = f"""
You are evaluating the success of a UI automation action.
Action taken: {action_type} 
Target: {target}
Expected Consequence: {intent}

Look at the Before image and After image. 
Did the action successfully achieve its expected consequence? 
Pay close attention to edge cases: if clicking an icon only opened a taskbar thumbnail preview instead of focusing the app window, that is a FAILURE.
Simply answer YES or NO.
"""
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt, img1, img2]
            )
            
            answer = response.text.strip().upper()
            print(f"[VLM Semantic Eval] Response: {answer}")
            return "YES" in answer
        except Exception as e:
            print(f"[VLM ERROR] Failed to compare images: {e}")
            return True # Fallback to Assuming state changed

    def detect_ui_elements_fast(self, current_frame, previous_frame=None):
        """
        Uses fast OpenCV heuristics (Contours, Edge Detection, Frame Differencing)
        to identify UI elements and dynamic regions in real-time.
        current_frame: numpy array (BGR)
        previous_frame: optional numpy array (BGR) for comparative analysis
        Returns: list of dicts: {'x','y','w','h', 'label', 'color'}
        """
        import cv2
        import numpy as np

        elements = []
        gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        
        # 1. Comparative / Dynamic Region Detection
        if previous_frame is not None:
            prev_gray = cv2.cvtColor(previous_frame, cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(gray, prev_gray)
            _, diff_thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            
            # Morphological close to group local changes
            kernel_dyn = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
            diff_closed = cv2.morphologyEx(diff_thresh, cv2.MORPH_CLOSE, kernel_dyn)
            
            contours_dyn, _ = cv2.findContours(diff_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in contours_dyn:
                x, y, w, h = cv2.boundingRect(c)
                if w * h > 100: # Ignore tiny noise
                    elements.append({'x': x, 'y': y, 'width': w, 'height': h, 'label': 'DYNAMIC', 'color': 'red'})
        
        # 2. Heuristic Structural Detection (Text blocks, Icons, Buttons)
        # Edge detection 
        edges = cv2.Canny(gray, 50, 150)
        
        # Dilate to connect text and form coherent blocks
        kernel_struct = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 5)) 
        closed_edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_struct)
        
        contours_struct, _ = cv2.findContours(closed_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        screen_h, screen_w = gray.shape
        
        for c in contours_struct:
            x, y, w, h = cv2.boundingRect(c)
            area = w * h
            
            # Filter out extreme noise or full screen contours
            if area < 50 or area > (screen_w * screen_h * 0.9):
                continue
                
            aspect_ratio = w / float(h)
            
            # Classification Heuristics
            label = "STRUCTURAL"
            color = "purple"
            
            if y > screen_h - 60 and w > screen_w * 0.8:
                label = "TASKBAR"
                color = "yellow"
            elif 0.8 < aspect_ratio < 1.2 and 100 < area < 5000:
                label = "ICON/AVATAR"
                color = "blue"
            elif aspect_ratio > 3.0 and h > 10 and h < 80:
                label = "TEXT BOX/ROW"
                color = "green"
            elif area > 50000:
                label = "PANEL/IMAGE"
                color = "purple"
            
            elements.append({'x': x, 'y': y, 'width': w, 'height': h, 'label': label, 'color': color})
            
        return elements
