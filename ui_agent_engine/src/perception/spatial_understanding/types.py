from enum import Enum
from typing import Dict, List, Any

class DetectTypes(str, Enum):
    BOUNDING_BOX_2D = "2d_bounding_boxes"
    SEGMENTATION_MASKS = "segmentation_masks"
    BOUNDING_BOX_3D = "3d_bounding_boxes"
    POINTS = "points"

class OutputModes(str, Enum):
    COORDINATES_ONLY = "coordinates_only"
    IMAGE_ONLY = "image_only"
    BOTH = "both"

DEFAULT_PROMPT_PARTS: Dict[str, List[str]] = {
    DetectTypes.BOUNDING_BOX_2D: [
        'Show me the positions of',
        'items',
        'as a JSON list. Do not return masks. Limit to 25 items.',
    ],
    DetectTypes.SEGMENTATION_MASKS: [
        'Give the segmentation masks for the',
        'items',
        '. Output a JSON list of segmentation masks where each entry contains the 2D bounding box in the key "box_2d", the segmentation mask in key "mask", and the text label in the key "label". Use descriptive labels.',
    ],
    DetectTypes.BOUNDING_BOX_3D: [
        'Output in json. Detect the 3D bounding boxes of ',
        'items',
        ', output no more than 10 items. Return a list where each entry contains the object name in "label" and its 3D bounding box in "box_3d".',
    ],
    DetectTypes.POINTS: [
        'Point to the',
        'items',
        ' with no more than 10 items. The answer should follow the json format: [{"point": <point>, "label": <label1>}, ...]. The points are in [y, x] format normalized to 0-1000.',
    ],
}

def generate_2d_prompt(target_prompt: str = 'items', label_prompt: str = '') -> str:
    """Generates a custom prompt for 2D bounding boxes."""
    label_instruction = label_prompt if label_prompt else 'a text label'
    return f'Detect {target_prompt}, with no more than 20 items. Output a json list where each entry contains the 2D bounding box in "box_2d" and {label_instruction} in "label".'

def generate_prompt(detect_type: DetectTypes, target_prompt: str) -> str:
    """
    Generates the full instructional prompt for the Gemini API.
    """
    final_target = target_prompt.strip() if target_prompt and target_prompt.strip() else 'items'

    if detect_type == DetectTypes.BOUNDING_BOX_2D:
        return generate_2d_prompt(final_target, 'a text label')

    prompt_parts = DEFAULT_PROMPT_PARTS.get(detect_type)
    if not prompt_parts:
        # Fallback to 2D
        return generate_2d_prompt(final_target, 'a text label')

    new_prompt_parts = list(prompt_parts)
    new_prompt_parts[1] = final_target

    separator = '' if detect_type == DetectTypes.SEGMENTATION_MASKS else ' '
    return separator.join(new_prompt_parts)

class Colors:
    BOUNDING_BOX = (59, 104, 255) # RGB
    POINT = (255, 0, 0)
    COORDINATES_TOP_LEFT = (220, 38, 127)
    COORDINATES_TOP_RIGHT = (34, 197, 94)
    COORDINATES_BOTTOM_LEFT = (59, 130, 246)
    COORDINATES_BOTTOM_RIGHT = (128, 0, 128)

class Validation:
    MAX_IMAGE_SIZE_MB = 10
    MIN_TEMPERATURE = 0.0
    MAX_TEMPERATURE = 1.0
    MIN_FOV = 30
    MAX_FOV = 120
    MIN_MAX_RESULTS = 1
    MAX_MAX_RESULTS_2D = 25
    MAX_MAX_RESULTS_3D = 10
    MAX_MAX_RESULTS_POINTS = 10
    MIN_IMAGE_SCALE = 0.1
    MAX_IMAGE_SCALE = 2.0
    MAX_OUTPUT_TOKENS = 8192
