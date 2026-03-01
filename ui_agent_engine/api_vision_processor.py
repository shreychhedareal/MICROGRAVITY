import os
import sys
import json
import base64
import cv2
import numpy as np
import io
import time
from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import types

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from src.perception.screen import ScreenObserver

class APIVisionProcessor:
    def __init__(self):
        load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing.")
            
        self.client = genai.Client()
        # Recommend Pro or 1.5/2.5 Flash for complex "Set of Marks" parsing
        self.model_name = "gemini-2.5-flash"

    def get_structural_proposals(self, image_bgr):
        """Use OpenCV heuristics to get bounding boxes for all structural elements."""
        elements = []
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        screen_h, screen_w = gray.shape
        
        # 1. Edge Detection & Thresholding (Catch both outlines and solid icons)
        edges = cv2.Canny(gray, 30, 150)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        combined_features = cv2.bitwise_or(edges, thresh)
        
        # 2. Multi-scale Morphology
        # Very slight horizontal kernel to group letters into single words, but NOT merge adjacent words or icons
        kernel_word = cv2.getStructuringElement(cv2.MORPH_RECT, (6, 2))
        combined_mask = cv2.morphologyEx(combined_features, cv2.MORPH_CLOSE, kernel_word)
        
        # 3. Find Contours with hierarchy
        contours, _ = cv2.findContours(combined_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        boxes = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            area = w * h
            
            # Meaningful structural items: Lowered to extreme minimums to catch tiny text and icons
            if w >= 6 and h >= 6 and area >= 36 and area < (screen_w * screen_h * 0.95):
                boxes.append([x, y, w, h])

        # 4. Filter Redundant Boxes (Keep Nested, Remove identical)
        final_boxes = []
        boxes = sorted(boxes, key=lambda b: b[2]*b[3]) # Sort by area to keep tightest boxes naturally favored
        
        for b in boxes:
            bx, by, bw, bh = b
            b_area = bw * bh
            is_redundant = False
            for fb in final_boxes:
                fx, fy, fw, fh = fb
                f_area = fw * fh
                
                # Intersection
                ix = max(bx, fx)
                iy = max(by, fy)
                iw = min(bx+bw, fx+fw) - ix
                ih = min(by+bh, fy+fh) - iy
                
                if iw > 0 and ih > 0:
                    inter_area = iw * ih
                    # If this box is nearly identical (85%+ overlap in both directions)
                    if (inter_area / b_area > 0.85) and (inter_area / f_area > 0.85):
                        is_redundant = True
                        break
            
            if not is_redundant:
                final_boxes.append(b)
                
        # Cap bounding boxes to a much higher number for extreme granularity
        if len(final_boxes) > 800:
            final_boxes = sorted(final_boxes, key=lambda b: b[2]*b[3], reverse=True)[:800]
        
        element_id = 1
        for fb in final_boxes:
            x, y, w, h = fb
            elements.append({
                'id': element_id,
                'x': x, 'y': y, 'width': w, 'height': h
            })
            element_id += 1
                
        return elements

    def draw_set_of_marks(self, image_bgr, elements):
        """Draws red bounding boxes and numerical IDs on the image."""
        annotated = image_bgr.copy()
        for el in elements:
            x, y, w, h = el['x'], el['y'], el['width'], el['height']
            eid = el['id']
            
            # Use smaller text and thinner boxes to prevent overlapping massive numbers on tiny icons
            font_scale = 0.4
            thickness = 1
            text = f"[{eid}]"
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
            
            # bounding box
            cv2.rectangle(annotated, (x, y), (x+w, y+h), (0, 0, 255), 1)
            
            # label background
            cv2.rectangle(annotated, (x, y - th - 2), (x + tw + 2, y), (0, 0, 255), -1)
            # label text
            cv2.putText(annotated, text, (x + 1, y - 2), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness)
            
        return annotated

    def draw_semantic_labels(self, image_bgr, labeled_elements):
        """Draws the final VLM text labels (e.g. 'Opera') instead of numbers."""
        annotated = image_bgr.copy()
        for el in labeled_elements:
            coords = el['coordinates']
            x, y, w, h = coords['x'], coords['y'], coords['width'], coords['height']
            label_text = f"{el['label']} ({el.get('description', '')})"
            
            # Use smaller text and thinner boxes for granular items
            font_scale = 0.4
            thickness = 1
            (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
            
            # bounding box
            cv2.rectangle(annotated, (x, y), (x+w, y+h), (0, 255, 0), 1)
            
            # label background (Green for semantic)
            cv2.rectangle(annotated, (x, y - th - 2), (x + tw + 2, y), (0, 200, 0), -1)
            # label text
            cv2.putText(annotated, label_text, (x + 1, y - 2), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness)
            
        return annotated

    def ask_vlm_for_semantics(self, annotated_bgr, elements):
        """Sends the annotated image to Gemini API to label the numbered boxes."""
        print(f"[API] Sending Set of Marks ({len(elements)} elements) to Gemini...")
        
        # Convert to PIL for the API
        rgb_image = cv2.cvtColor(annotated_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_image)
        
        # Strict prompt to force JSON mapping
        prompt = f"""
I have provided an image with various UI elements highlighted by red bounding boxes. 
Inside the top-left corner of every red box, there is a numeric ID drawn in red text with a black background.

CRITICAL INSTRUCTION: You MUST physically read the number drawn on the image for each box. Do NOT simply guess numbers sequentially (1, 2, 3...). Look at the box, read the number drawn on it, and use THAT number as the ID.

There are EXACTLY {len(elements)} items highlighted in this image.

Please act as a comprehensive UI Labeling System. For EVERY visible ID inside a red box:
1. Identify what semantic element it contains (e.g., 'Google Chrome Icon', 'Search Box', 'Network Status Icon', 'Text: public').
2. Provide a short description of its purpose or what it represents.

You MUST return your response as a valid JSON array of objects mapping ALL {len(elements)} IDs exactly. Do not write markdown blocks or conversational text.
Example format:
[
  {{"id": 1, "label": "Google Chrome Icon", "description": "Web browser to access the internet"}},
  {{"id": 2, "label": "Text: URL Address Bar", "description": "Input field to type web addresses or search terms"}}
]
"""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[pil_img, prompt],
                config=types.GenerateContentConfig(temperature=0.0)
            )
            
            text = response.text.strip()
            
            # Clean JSON markdown if necessary
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
                
            labels = json.loads(text)
            
            # Merge labels with original coordinates
            mapping = {}
            for l in labels:
                mapping[l['id']] = {
                    'label': l.get('label', 'Unknown'),
                    'description': l.get('description', 'No description provided')
                }
                
            final_elements = []
            for el in elements:
                el_data = mapping.get(el['id'], {'label': 'Unknown/Unlabeled', 'description': 'N/A'})
                final_elements.append({
                    "id": el['id'],
                    "label": el_data['label'],
                    "description": el_data['description'],
                    "coordinates": {
                        "x": el['x'], 
                        "y": el['y'], 
                        "width": el['width'], 
                        "height": el['height']
                    }
                })
            
            return final_elements
            
        except Exception as e:
            print(f"[API ERROR] VLM Semantic Labeling failed: {e}")
            if hasattr(response, 'text'):
                print(f"Raw Output: {response.text}")
            return []

def main():
    print("==================================================")
    print(" Starting API-Based Static GUI Labeling Pipeline")
    print("==================================================")
    
    # Use UIMemoryAgent for path management
    from src.agent_core.ui_memory_agent import UIMemoryAgent
    from pathlib import Path
    workspace_path = Path(os.path.abspath(os.path.dirname(__file__)))
    memory = UIMemoryAgent(workspace_path)
    
    # Unified Redirection to Short-Term Track
    diag_dir = memory.short_term_dir / "diagnostics"
    diag_dir.mkdir(parents=True, exist_ok=True)
    
    # Inject diag_dir into ScreenObserver
    screen_obs = ScreenObserver(output_dir=str(diag_dir))
    
    processor = APIVisionProcessor()
    
    print("1. Capturing static screen...")
    # Capture screen directly to cv2 BGR array
    img_bgr = screen_obs.capture_as_cv2()
    
    print("2. OpenCV generating structural bound proposals...")
    proposals = processor.get_structural_proposals(img_bgr)
    print(f"   Found {len(proposals)} distinct structural elements.")
    
    # Unified Redirection to Short-Term Track
    diag_dir = memory.short_term_dir / "diagnostics"
    out_dir = memory.short_term_dir / "predicted_outputs"
    
    diag_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = int(time.time())
    
    raw_path = str(diag_dir / f"capture_{timestamp}.png")
    cv2.imwrite(raw_path, img_bgr)
    print(f"   Saved raw capture to '{raw_path}'")
    
    print("3. Drawing full Set of Marks and saving for debug...")
    annotated_img = processor.draw_set_of_marks(img_bgr, proposals)
    ann_path = str(diag_dir / f"annotated_{timestamp}.png")
    cv2.imwrite(ann_path, annotated_img)
    print(f"   Saved fully annotated capture to '{ann_path}'")
    
    print("4. Asking VLM for Semantic Labels (Batched for accuracy)...")
    final_labeled_ui = []
    
    # Process in batches to prevent VLM from skipping items or hallucinating
    batch_size = 40
    for i in range(0, len(proposals), batch_size):
        batch = proposals[i:i+batch_size]
        print(f"   -> Processing Batch {i//batch_size + 1}/{(len(proposals)+batch_size-1)//batch_size} ({len(batch)} items)...")
        
        # Draw ONLY this batch onto a fresh baseline copy of the image
        batch_img = processor.draw_set_of_marks(img_bgr, batch)
        
        # Send strictly this sub-annotated scene to Gemini
        batch_labels = processor.ask_vlm_for_semantics(batch_img, batch)
        final_labeled_ui.extend(batch_labels)
    
    print(f"\n--- Final Structured GUI Map ({len(final_labeled_ui)} elements) ---")
    
    # Save the map to disk for the agent to use
    json_path = str(out_dir / f"gui_map_{timestamp}.json")
    with open(json_path, "w") as f:
        json.dump(final_labeled_ui, f, indent=2)
    print(f"\n✅ Saved GUI Map to '{json_path}'")
    
    # Save a human-readable text version of the map
    txt_path = str(out_dir / f"gui_map_{timestamp}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("=== GUI Elements Map ===\n\n")
        max_id_len = len(str(len(final_labeled_ui)))
        for el in final_labeled_ui:
            f.write(f"ID:          {el['id']}\n")
            f.write(f"Label:       {el['label']}\n")
            f.write(f"Description: {el['description']}\n")
            c = el['coordinates']
            f.write(f"Coordinates: x={c['x']}, y={c['y']}, width={c['width']}, height={c['height']}\n")
            f.write("-" * 50 + "\n")
    print(f"✅ Saved Human-Readable Text Map to '{txt_path}'")
    
    print("5. Drawing Final Semantic Text Labels onto Screen...")
    semantic_img = processor.draw_semantic_labels(img_bgr, final_labeled_ui)
    semantic_path = str(diag_dir / f"semantic_labels_{timestamp}.png")
    cv2.imwrite(semantic_path, semantic_img)
    print(f"   Saved text-labeled capture to '{semantic_path}'")

if __name__ == "__main__":
    main()
