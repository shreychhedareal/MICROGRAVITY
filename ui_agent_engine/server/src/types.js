/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { HarmCategory, HarmBlockThreshold } from '@google/generative-ai';

// Detection types supported by the API
export const DETECT_TYPES = {
  '2D_BOUNDING_BOXES': '2d_bounding_boxes',
  'SEGMENTATION_MASKS': 'segmentation_masks', 
  '3D_BOUNDING_BOXES': '3d_bounding_boxes',
  'POINTS': 'points'
};

// Output modes for API responses
export const OUTPUT_MODES = {
  COORDINATES_ONLY: 'coordinates_only',
  IMAGE_ONLY: 'image_only',
  BOTH: 'both'
};

// Default prompt parts (matching client-side exactly)
export const DEFAULT_PROMPT_PARTS = {
  '2d_bounding_boxes': [
    'Show me the positions of',
    'items',
    'as a JSON list. Do not return masks. Limit to 25 items.',
  ],
  'segmentation_masks': [
    `Give the segmentation masks for the`,
    'items',
    `. Output a JSON list of segmentation masks where each entry contains the 2D bounding box in the key "box_2d", the segmentation mask in key "mask", and the text label in the key "label". Use descriptive labels.`,
  ],
  '3d_bounding_boxes': [
    'Output in json. Detect the 3D bounding boxes of ',
    'items',
    ', output no more than 10 items. Return a list where each entry contains the object name in "label" and its 3D bounding box in "box_3d".',
  ],
  'points': [
    'Point to the',
    'items',
    ' with no more than 10 items. The answer should follow the json format: [{"point": <point>, "label": <label1>}, ...]. The points are in [y, x] format normalized to 0-1000.',
  ],
};

// Default prompts (assembled from parts)
export const DEFAULT_PROMPTS = {
  '2d_bounding_boxes': DEFAULT_PROMPT_PARTS['2d_bounding_boxes'].join(' '),
  '3d_bounding_boxes': DEFAULT_PROMPT_PARTS['3d_bounding_boxes'].join(' '),
  'segmentation_masks': DEFAULT_PROMPT_PARTS['segmentation_masks'].join(''),
  'points': DEFAULT_PROMPT_PARTS['points'].join(' '),
};

// Custom 2D prompt generator (matching client logic)
export function generate2DPrompt(targetPrompt = 'items', labelPrompt = '') {
  return `Detect ${targetPrompt}, with no more than 20 items. Output a json list where each entry contains the 2D bounding box in "box_2d" and ${
    labelPrompt || 'a text label'
  } in "label".`;
}

/**
 * Safety settings for the Gemini API.
 * Defines categories of harmful content and the threshold at which to block them.
 * Using BLOCK_NONE to be permissive for this object detection use case.
 */
export const SAFETY_SETTINGS = [
  {
    category: HarmCategory.HARM_CATEGORY_HARASSMENT,
    threshold: HarmBlockThreshold.BLOCK_NONE,
  },
  {
    category: HarmCategory.HARM_CATEGORY_HATE_SPEECH,
    threshold: HarmBlockThreshold.BLOCK_NONE,
  },
  {
    category: HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
    threshold: HarmBlockThreshold.BLOCK_NONE,
  },
  {
    category: HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
    threshold: HarmBlockThreshold.BLOCK_NONE,
  },
];

// Line drawing options for annotations
export const LINE_OPTIONS = {
  size: 8,
  thinning: 0,
  smoothing: 0,
  streamline: 0,
  simulatePressure: false
};

// Colors for visualization (RGB values)
export const COLORS = {
  BOUNDING_BOX: [59, 104, 255], // #3B68FF
  SEGMENTATION: [
    [230, 25, 75],   // Red
    [60, 137, 208],  // Blue
    [60, 180, 75],   // Green
    [255, 225, 25],  // Yellow
    [145, 30, 180],  // Purple
    [66, 212, 244],  // Cyan
    [245, 130, 49],  // Orange
    [240, 50, 230],  // Magenta
    [191, 239, 69],  // Lime
    [70, 153, 144]   // Teal
  ],
  POINT: [255, 0, 0], // Red
  COORDINATES: {
    TOP_LEFT: [220, 38, 127],     // Red
    TOP_RIGHT: [34, 197, 94],     // Green  
    BOTTOM_LEFT: [59, 130, 246],  // Blue
    BOTTOM_RIGHT: [128, 0, 128]
  }
};

// Validation constraints
export const VALIDATION = {
  MAX_IMAGE_SIZE_MB: 10,
  MIN_TEMPERATURE: 0,
  MAX_TEMPERATURE: 1,
  MIN_FOV: 30,
  MAX_FOV: 120,
  MIN_MAX_RESULTS: 1,
  MAX_MAX_RESULTS_2D: 25,
  MAX_MAX_RESULTS_3D: 10,
  MAX_MAX_RESULTS_POINTS: 10,
  MIN_IMAGE_SCALE: 0.1,
  MAX_IMAGE_SCALE: 2.0
};

// Response status codes
export const STATUS_CODES = {
  SUCCESS: 200,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  NOT_FOUND: 404,
  PAYLOAD_TOO_LARGE: 413,
  RATE_LIMITED: 429,
  INTERNAL_ERROR: 500
}; 