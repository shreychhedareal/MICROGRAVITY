import os
from .types import DetectTypes
from .gemini_service import GeminiSpatialService
from .utils import draw_2d_boxes, draw_3d_boxes, draw_points

class SpatialUnderstandingTool:
    """
    The UI Agent Tool that exposes intelligent spatial querying.
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        self.service = GeminiSpatialService(self.api_key)
        
    def execute(self, image_path: str, target_prompt: str, detect_type_str: str = "2d_bounding_boxes", output_image_path: str = None) -> dict:
        """
        Executes a spatial bounding box/point search on an image.
        
        Args:
           image_path: Path to the absolute image.
           target_prompt: What object to search for (e.g. 'cars', 'red buttons').
           detect_type_str: '2d_bounding_boxes', '3d_bounding_boxes', 'points', or 'segmentation_masks'.
           output_image_path: Optional path to save an annotated visual of the search result.
        """
        
        if detect_type_str == "2d_bounding_boxes":
            d_type = DetectTypes.BOUNDING_BOX_2D
        elif detect_type_str == "3d_bounding_boxes":
            d_type = DetectTypes.BOUNDING_BOX_3D
        elif detect_type_str == "points":
            d_type = DetectTypes.POINTS
        elif detect_type_str == "segmentation_masks":
            d_type = DetectTypes.SEGMENTATION_MASKS
        else:
            raise ValueError(f"Unknown detection type {detect_type_str}")
            
        with open(image_path, "rb") as f:
            image_bytes = f.read()
            
        res = self.service.detect(image_bytes, d_type, target_prompt)
        
        if res.get("success") and output_image_path and "pil_image" in res:
            img = res["pil_image"]
            # Draw on image
            if d_type == DetectTypes.BOUNDING_BOX_2D or d_type == DetectTypes.SEGMENTATION_MASKS:
                img = draw_2d_boxes(img, res["results"])
            elif d_type == DetectTypes.BOUNDING_BOX_3D:
                 img = draw_3d_boxes(img, res["results"])
            elif d_type == DetectTypes.POINTS:
                 img = draw_points(img, res["results"])
                 
            img.save(output_image_path)
            
        # Clean up heavy data before returning to LM
        if "pil_image" in res:
             del res["pil_image"]
             
        return res
