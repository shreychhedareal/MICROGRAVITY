import json
import logging
from typing import Dict, Any
from google import genai
from google.genai import types

from .types import DetectTypes, generate_prompt, Validation
from .utils import (
    process_image, 
    format_2d_boxes, 
    format_3d_boxes, 
    format_points
)

# Use aligning model names
MODEL_2_FLASH = "gemini-3-flash-preview"
MODEL_2_5_FLASH = "gemini-3-flash-preview"

class GeminiSpatialService:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Gemini API key is required")
        self.client = genai.Client(api_key=api_key)

    def detect(self, image_data: bytes, detect_type: DetectTypes, target_prompt: str, temperature: float = 0.5) -> Dict[str, Any]:
        try:
            processed_data = process_image(image_data)
            final_prompt = generate_prompt(detect_type, target_prompt)
            
            # Select model: Segmentation uses 2.5 Flash, others 2.0 Flash
            model_name = MODEL_2_5_FLASH if detect_type == DetectTypes.SEGMENTATION_MASKS else MODEL_2_FLASH
            
            gen_config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=Validation.MAX_OUTPUT_TOKENS,
            )
            
            if detect_type == DetectTypes.SEGMENTATION_MASKS:
                 # equivalent to thinkingBudget=0 if it was available or simple text config
                 pass
            
            # Sending directly bytes to Gemini via Part
            response = self.client.models.generate_content(
                model=model_name,
                contents=[
                    types.Part.from_bytes(data=image_data, mime_type="image/jpeg"),
                    final_prompt
                ],
                config=gen_config
            )
            
            text_result = response.text
            
            # Robust JSON extraction
            json_str = text_result
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "[" in json_str and "]" in json_str:
                json_str = json_str[json_str.find("["):json_str.rfind("]") + 1]
                
            try:
                parsed = json.loads(json_str)
            except json.JSONDecodeError as e:
                return {"success": False, "error": "Failed to parse JSON response from Gemini", "details": str(e), "raw": text_result}
                
            # Formatting results
            if detect_type == DetectTypes.BOUNDING_BOX_2D:
                results = format_2d_boxes(parsed)
            elif detect_type == DetectTypes.BOUNDING_BOX_3D:
                results = format_3d_boxes(parsed)
            elif detect_type == DetectTypes.POINTS:
                results = format_points(parsed)
            elif detect_type == DetectTypes.SEGMENTATION_MASKS:
                 # Fallback logic for basic coords over true image mask parsing in python (simplified for UI agent usage)
                 results = format_2d_boxes(parsed)
            else:
                results = []
                
            return {
                "success": True,
                "detect_type": detect_type.value,
                "results": results,
                "metadata": {
                    "model": model_name,
                    "prompt": final_prompt,
                    "temperature": temperature
                },
                "pil_image": processed_data["pil_image"]
            }
        except Exception as e:
            logging.error(f"Error in Gemini inference: {e}")
            return {"success": False, "error": str(e)}
