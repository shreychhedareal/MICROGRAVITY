import io
import base64
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from typing import List, Dict, Any, Union
from .types import Colors, DetectTypes
from .math3d import project_all_3d_bounding_boxes

def process_image(image_input: Union[str, bytes], max_size: int = 640) -> Dict[str, Any]:
    """Load, resize, and process image for Gemini. Returns Base64."""
    if isinstance(image_input, str):
        # Assume it's a file path
        img = Image.open(image_input)
    else:
        # Assume it's bytes
        img = Image.open(io.BytesIO(image_input))
        
    original_width, original_height = img.size
    
    # Calculate scale to fit within max_size
    scale = min(max_size / original_width, max_size / original_height)
    new_width = int(original_width * scale)
    new_height = int(original_height * scale)
    
    # Resize using Resampling.LANCZOS for good quality downscaling
    img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Convert to base64
    buffered = io.BytesIO()
    img_resized.save(buffered, format="PNG")
    img_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    mime_type = "image/png"
    
    return {
        "base64_data": img_b64,
        "mime_type": mime_type,
        "original_width": original_width,
        "original_height": original_height,
        "width": new_width,
        "height": new_height,
        "pil_image": img_resized
    }

def format_2d_boxes(parsed_response: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    formatted = []
    for item in parsed_response:
        if "box_2d" in item:
            ymin, xmin, ymax, xmax = item["box_2d"]
            # Normalize to 0-1
            formatted.append({
                "x": xmin / 1000.0,
                "y": ymin / 1000.0,
                "width": (xmax - xmin) / 1000.0,
                "height": (ymax - ymin) / 1000.0,
                "label": item.get("label", "")
            })
    return formatted

def format_3d_boxes(parsed_response: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    formatted = []
    for item in parsed_response:
        if "box_3d" in item:
            box = item["box_3d"]
            center = box[0:3]
            size = box[3:6]
            # Convert rotation to radians
            import math
            rpy = [x * math.pi / 180.0 for x in box[6:9]]
            formatted.append({
                "center": center,
                "size": size,
                "rpy": rpy,
                "label": item.get("label", "")
            })
    return formatted

def format_points(parsed_response: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    formatted = []
    for item in parsed_response:
        if "point" in item:
            y, x = item["point"]
            formatted.append({
                "point": {
                    "x": x / 1000.0,
                    "y": y / 1000.0
                },
                "label": item.get("label", "")
            })
    return formatted

def draw_2d_boxes(img: Image.Image, boxes: List[Dict[str, Any]], show_coordinates: bool = True) -> Image.Image:
    """Draws 2D bounding boxes on a PIL image."""
    draw = ImageDraw.Draw(img)
    width, height = img.size
    
    for box in boxes:
        x = box["x"] * width
        y = box["y"] * height
        w = box["width"] * width
        h = box["height"] * height
        label = box.get("label", "")
        
        # Bounding Box
        draw.rectangle([x, y, x + w, y + h], outline=Colors.BOUNDING_BOX, width=2)
        
        # Label with background
        if label:
            # Simple text bounds estimation (Pillow doesn't have great getsize anymore)
            text_bbox = draw.textbbox((0, 0), label)
            text_w = text_bbox[2] - text_bbox[0]
            text_h = text_bbox[3] - text_bbox[1]
            draw.rectangle([x, max(0, y - text_h - 4), x + text_w + 4, y], fill=Colors.BOUNDING_BOX)
            draw.text((x + 2, max(0, y - text_h - 2)), label, fill=(255, 255, 255))
            
        if show_coordinates:
             # Basic top-left coordinate text logic
             coord_text = f"({box['x']:.2f}, {box['y']:.2f})"
             draw.text((x, y + h + 2), coord_text, fill=Colors.COORDINATES_TOP_LEFT)
             
    return img

def draw_points(img: Image.Image, points: List[Dict[str, Any]], show_coordinates: bool = True) -> Image.Image:
    draw = ImageDraw.Draw(img)
    width, height = img.size
    
    for p in points:
        x = p["point"]["x"] * width
        y = p["point"]["y"] * height
        label = p.get("label", "")
        
        r = 6
        draw.ellipse([x - r, y - r, x + r, y + r], fill=Colors.POINT)
        draw.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(255, 255, 255))
        
        if label:
            draw.text((x + 10, y - 10), label, fill=Colors.POINT)
            
    return img

def draw_3d_boxes(img: Image.Image, boxes: List[Dict[str, Any]], fov: float = 60.0, show_coordinates: bool = True) -> Image.Image:
    draw = ImageDraw.Draw(img)
    width, height = img.size
    
    # We re-created project_all_3d_bounding_boxes in math3d
    projections = project_all_3d_bounding_boxes(boxes, width, height, fov)
    
    # Draw Lines
    for line in projections["lines"]:
        start = line["start"]
        end = line["end"]
        draw.line([start[0], start[1], end[0], end[1]], fill=Colors.BOUNDING_BOX, width=2)
        
    # Draw Labels
    for label_info in projections["labels"]:
        l_text = label_info["label"]
        pos = label_info["pos"]
        draw.text((pos[0], pos[1]), l_text, fill=(255,255,255), stroke_width=2, stroke_fill=Colors.BOUNDING_BOX)
        
    return img
