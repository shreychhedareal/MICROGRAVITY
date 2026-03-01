/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import sharp from 'sharp';
import axios from 'axios';
import { Canvas, loadImage } from 'skia-canvas';
import { COLORS, VALIDATION, generate2DPrompt, DEFAULT_PROMPTS, DEFAULT_PROMPT_PARTS } from './types.js';
import { projectAll3DBoundingBoxes, validate3DBoundingBox, calculate3DBoxVertices } from './math3d.js';
import { addCalibrationScale, generateCoordinateReference } from './calibration.js';

/**
 * Load image from URL or base64 string
 * @param {string} imageInput - URL or base64 string
 * @returns {Promise<Buffer>} Image buffer
 */
export async function loadImageFromInput(imageInput) {
  try {
    if (imageInput.startsWith('data:image/')) {
      // Handle base64 encoded image
      const base64Data = imageInput.split(',')[1];
      return Buffer.from(base64Data, 'base64');
    } else if (imageInput.startsWith('http://') || imageInput.startsWith('https://')) {
      // Handle URL
      const response = await axios.get(imageInput, {
        responseType: 'arraybuffer',
        timeout: 10000,
        maxContentLength: VALIDATION.MAX_IMAGE_SIZE_MB * 1024 * 1024
      });
      return Buffer.from(response.data);
    } else {
      throw new Error('Invalid image input. Must be a URL or base64 encoded string.');
    }
  } catch (error) {
    throw new Error(`Failed to load image: ${error.message}`);
  }
}

/**
 * Process and resize image
 * @param {Buffer} imageBuffer - Input image buffer
 * @param {number} maxSize - Maximum dimension size
 * @returns {Promise<{buffer: Buffer, width: number, height: number}>}
 */
export async function processImage(imageBuffer, maxSize = 640) {
  try {
    const image = sharp(imageBuffer);
    const metadata = await image.metadata();
    
    const scale = Math.min(maxSize / metadata.width, maxSize / metadata.height);
    const newWidth = Math.round(metadata.width * scale);
    const newHeight = Math.round(metadata.height * scale);
    
    const processedBuffer = await image
      .resize(newWidth, newHeight)
      .png()
      .toBuffer();
    
    return {
      buffer: processedBuffer,
      width: newWidth,
      height: newHeight,
      originalWidth: metadata.width,
      originalHeight: metadata.height
    };
  } catch (error) {
    throw new Error(`Failed to process image: ${error.message}`);
  }
}

/**
 * Convert image buffer to base64 data URL
 * @param {Buffer} buffer - Image buffer
 * @param {string} mimeType - MIME type (default: image/png)
 * @returns {string} Base64 data URL
 */
export function bufferToDataURL(buffer, mimeType = 'image/png') {
  const base64 = buffer.toString('base64');
  return `data:${mimeType};base64,${base64}`;
}

/**
 * Format 2D bounding box coordinates from AI response
 * @param {Array} parsedResponse - AI response
 * @returns {Array} Formatted bounding boxes
 */
export function format2DBoundingBoxes(parsedResponse) {
  return parsedResponse.map(box => {
    const [ymin, xmin, ymax, xmax] = box.box_2d;
    return {
      x: xmin / 1000,
      y: ymin / 1000,
      width: (xmax - xmin) / 1000,
      height: (ymax - ymin) / 1000,
      label: box.label
    };
  });
}

/**
 * Format 3D bounding box coordinates from AI response
 * @param {Array} parsedResponse - AI response
 * @returns {Array} Formatted 3D bounding boxes
 */
export function format3DBoundingBoxes(parsedResponse) {
  return parsedResponse.map(box => {
    const center = box.box_3d.slice(0, 3);
    const size = box.box_3d.slice(3, 6);
    const rpy = box.box_3d.slice(6).map(x => (x * Math.PI) / 180);
    return {
      center,
      size,
      rpy,
      label: box.label
    };
  });
}

/**
 * Format points from AI response
 * @param {Array} parsedResponse - AI response
 * @returns {Array} Formatted points
 */
export function formatPoints(parsedResponse) {
  return parsedResponse.map(point => ({
    point: {
      x: point.point[1] / 1000,
      y: point.point[0] / 1000
    },
    label: point.label
  }));
}

/**
 * Format segmentation masks from AI response
 * @param {Array} parsedResponse - AI response
 * @returns {Array} Formatted segmentation masks
 */
export function formatSegmentationMasks(parsedResponse) {
  return parsedResponse.map(box => {
    const [ymin, xmin, ymax, xmax] = box.box_2d;
    return {
      x: xmin / 1000,
      y: ymin / 1000,
      width: (xmax - xmin) / 1000,
      height: (ymax - ymin) / 1000,
      label: box.label,
      imageData: box.mask
    };
  }).sort((a, b) => (b.width * b.height) - (a.width * a.height));
}

/**
 * Draw 2D bounding boxes on image
 * @param {Buffer} imageBuffer - Input image buffer
 * @param {Array} boundingBoxes - Array of bounding boxes
 * @param {Object} options - Drawing options
 * @returns {Promise<Buffer>} Image buffer with annotations
 */
export async function draw2DBoundingBoxes(imageBuffer, boundingBoxes, options = {}) {
  const { showCoordinates = true, imageScale = 1 } = options;
  
  const image = await loadImage(imageBuffer);
  const canvas = new Canvas(image.width * imageScale, image.height * imageScale);
  const ctx = canvas.getContext('2d');
  
  // Draw original image
  ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
  
  // Draw bounding boxes
  boundingBoxes.forEach((box, index) => {
    const x = box.x * canvas.width;
    const y = box.y * canvas.height;
    const width = box.width * canvas.width;
    const height = box.height * canvas.height;
    
    // Draw bounding box
    ctx.strokeStyle = `rgb(${COLORS.BOUNDING_BOX.join(',')})`;
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, width, height);
    
    // Draw label
    ctx.fillStyle = `rgb(${COLORS.BOUNDING_BOX.join(',')})`;
    ctx.font = '14px Arial';
    const labelWidth = ctx.measureText(box.label).width;
    ctx.fillRect(x, y - 20, labelWidth + 8, 20);
    ctx.fillStyle = 'white';
    ctx.fillText(box.label, x + 4, y - 6);
    
    // Draw coordinates if enabled
    if (showCoordinates) {
      const fontSize = Math.max(8, 12 * imageScale);
      ctx.font = `${fontSize}px monospace`;
      
      // Top-left coordinate
      ctx.fillStyle = `rgb(${COLORS.COORDINATES.TOP_LEFT.join(',')})`;
      ctx.fillRect(x - 2, y - 2, 80, 12);
      ctx.fillStyle = 'white';
      ctx.fillText(`TL: (${box.x.toFixed(3)}, ${box.y.toFixed(3)})`, x, y + 8);
      
      // Top-right coordinate
      ctx.fillStyle = `rgb(${COLORS.COORDINATES.TOP_RIGHT.join(',')})`;
      ctx.fillRect(x + width - 78, y - 2, 80, 12);
      ctx.fillStyle = 'white';
      ctx.fillText(`TR: (${(box.x + box.width).toFixed(3)}, ${box.y.toFixed(3)})`, x + width - 76, y + 8);
      
      // Bottom-left coordinate
      ctx.fillStyle = `rgb(${COLORS.COORDINATES.BOTTOM_LEFT.join(',')})`;
      ctx.fillRect(x - 2, y + height - 10, 80, 12);
      ctx.fillStyle = 'white';
      ctx.fillText(`BL: (${box.x.toFixed(3)}, ${(box.y + box.height).toFixed(3)})`, x, y + height + 2);
      
      // Bottom-right coordinate
      ctx.fillStyle = `rgb(${COLORS.COORDINATES.BOTTOM_RIGHT.join(',')})`;
      ctx.fillRect(x + width - 78, y + height - 10, 80, 12);
      ctx.fillStyle = 'white';
      ctx.fillText(`BR: (${(box.x + box.width).toFixed(3)}, ${(box.y + box.height).toFixed(3)})`, x + width - 76, y + height + 2);
    }
  });
  
  return canvas.toBuffer('image/png');
}

/**
 * Draw points on image
 * @param {Buffer} imageBuffer - Input image buffer
 * @param {Array} points - Array of points
 * @param {Object} options - Drawing options
 * @returns {Promise<Buffer>} Image buffer with annotations
 */
export async function drawPoints(imageBuffer, points, options = {}) {
  const { showCoordinates = true, imageScale = 1 } = options;
  
  const image = await loadImage(imageBuffer);
  const canvas = new Canvas(image.width * imageScale, image.height * imageScale);
  const ctx = canvas.getContext('2d');
  
  // Draw original image
  ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
  
  // Draw points
  points.forEach((point, index) => {
    const x = point.point.x * canvas.width;
    const y = point.point.y * canvas.height;
    
    // Draw point circle
    ctx.fillStyle = `rgb(${COLORS.POINT.join(',')})`;
    ctx.beginPath();
    ctx.arc(x, y, 6 * imageScale, 0, 2 * Math.PI);
    ctx.fill();
    
    // Draw white center
    ctx.fillStyle = 'white';
    ctx.beginPath();
    ctx.arc(x, y, 2 * imageScale, 0, 2 * Math.PI);
    ctx.fill();
    
    // Draw label
    ctx.fillStyle = `rgb(${COLORS.POINT.join(',')})`;
    ctx.font = `${14 * imageScale}px Arial`;
    const labelWidth = ctx.measureText(point.label).width;
    ctx.fillRect(x + 10, y - 20, labelWidth + 8, 20);
    ctx.fillStyle = 'white';
    ctx.fillText(point.label, x + 14, y - 6);
    
    // Draw coordinates if enabled
    if (showCoordinates) {
      const fontSize = Math.max(8, 10 * imageScale);
      ctx.font = `${fontSize}px monospace`;
      ctx.fillStyle = 'black';
      ctx.fillRect(x + 10, y + 5, 100, 15);
      ctx.fillStyle = 'white';
      ctx.fillText(`(${point.point.x.toFixed(3)}, ${point.point.y.toFixed(3)})`, x + 12, y + 16);
    }
  });
  
  return canvas.toBuffer('image/png');
}

/**
 * Calculate 3D bounding box projection (full implementation matching client)
 * @param {Array} boundingBoxes3D - Array of 3D bounding boxes
 * @param {number} fov - Field of view
 * @param {number} width - Image width
 * @param {number} height - Image height
 * @returns {Array} Projected lines and labels
 */
export function project3DBoundingBoxes(boundingBoxes3D, fov, width, height) {
  // Use the full 3D math implementation
  return projectAll3DBoundingBoxes(boundingBoxes3D, width, height, fov);
}

/**
 * Draw 3D bounding boxes on image
 * @param {Buffer} imageBuffer - Input image buffer
 * @param {Array} boundingBoxes3D - Array of 3D bounding boxes
 * @param {Object} options - Drawing options
 * @returns {Promise<Buffer>} Image buffer with annotations
 */
export async function draw3DBoundingBoxes(imageBuffer, boundingBoxes3D, options = {}) {
  const { showCoordinates = true, imageScale = 1, fov = 60 } = options;
  
  const image = await loadImage(imageBuffer);
  const canvas = new Canvas(image.width * imageScale, image.height * imageScale);
  const ctx = canvas.getContext('2d');
  
  // Draw original image
  ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
  
  const { lines, labels } = project3DBoundingBoxes(boundingBoxes3D, fov, canvas.width, canvas.height);
  
  // Draw wireframe lines
  ctx.strokeStyle = `rgb(${COLORS.BOUNDING_BOX.join(',')})`;
  ctx.lineWidth = 2 * imageScale;
  
  lines.forEach(line => {
    ctx.beginPath();
    ctx.moveTo(line.start[0] * imageScale, line.start[1] * imageScale);
    ctx.lineTo(line.end[0] * imageScale, line.end[1] * imageScale);
    ctx.stroke();
  });
  
  // Draw labels
  labels.forEach((label, index) => {
    const x = label.pos[0] * imageScale;
    const y = label.pos[1] * imageScale;
    
    // Draw label background
    ctx.fillStyle = `rgb(${COLORS.BOUNDING_BOX.join(',')})`;
    ctx.font = `${12 * imageScale}px Arial`;
    const labelWidth = ctx.measureText(label.label).width;
    ctx.fillRect(x - labelWidth/2, y - 15, labelWidth + 8, 20);
    ctx.fillStyle = 'white';
    ctx.fillText(label.label, x - labelWidth/2 + 4, y - 2);
    
    // Draw coordinates if enabled
    if (showCoordinates) {
      const coordText = `3D: (${label.center.map(c => c.toFixed(2)).join(', ')})`;
      const fontSize = Math.max(8, 10 * imageScale);
      ctx.font = `${fontSize}px monospace`;
      ctx.fillStyle = 'rgba(0,0,0,0.75)';
      const coordWidth = ctx.measureText(coordText).width;
      ctx.fillRect(x - coordWidth/2, y + 10, coordWidth + 4, 15);
      ctx.fillStyle = 'white';
      ctx.fillText(coordText, x - coordWidth/2 + 2, y + 22);
    }
  });
  
  return canvas.toBuffer('image/png');
}

/**
 * Validate API request parameters
 * @param {Object} params - Request parameters
 * @returns {Object} Validation result
 */
export function validateRequest(params) {
  const errors = [];
  
  // Validate required fields
  if (!params.image) {
    errors.push('image parameter is required');
  }
  
  if (!params.detectType) {
    errors.push('detectType parameter is required');
  }
  
  // Validate detectType
  const validDetectTypes = ['2d_bounding_boxes', 'segmentation_masks', '3d_bounding_boxes', 'points'];
  if (params.detectType && !validDetectTypes.includes(params.detectType)) {
    errors.push(`detectType must be one of: ${validDetectTypes.join(', ')}`);
  }
  
  // Validate outputMode
  const validOutputModes = ['coordinates_only', 'image_only', 'both'];
  if (params.outputMode && !validOutputModes.includes(params.outputMode)) {
    errors.push(`outputMode must be one of: ${validOutputModes.join(', ')}`);
  }
  
  // Validate temperature
  if (params.temperature !== undefined) {
    const temp = parseFloat(params.temperature);
    if (isNaN(temp) || temp < VALIDATION.MIN_TEMPERATURE || temp > VALIDATION.MAX_TEMPERATURE) {
      errors.push(`temperature must be between ${VALIDATION.MIN_TEMPERATURE} and ${VALIDATION.MAX_TEMPERATURE}`);
    }
  }
  
  // Validate fov
  if (params.fov !== undefined) {
    const fov = parseFloat(params.fov);
    if (isNaN(fov) || fov < VALIDATION.MIN_FOV || fov > VALIDATION.MAX_FOV) {
      errors.push(`fov must be between ${VALIDATION.MIN_FOV} and ${VALIDATION.MAX_FOV}`);
    }
  }
  
  // Validate imageScale
  if (params.imageScale !== undefined) {
    const scale = parseFloat(params.imageScale);
    if (isNaN(scale) || scale < VALIDATION.MIN_IMAGE_SCALE || scale > VALIDATION.MAX_IMAGE_SCALE) {
      errors.push(`imageScale must be between ${VALIDATION.MIN_IMAGE_SCALE} and ${VALIDATION.MAX_IMAGE_SCALE}`);
    }
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
}

/**
 * Generates the full instructional prompt for the Gemini API.
 * This function takes a detection type and a target (e.g., "cars") and
 * builds the complete prompt that instructs the model to perform a specific
 * spatial understanding task and return structured JSON.
 * @param {string} detectType - The type of detection to perform (e.g., '2d_bounding_boxes').
 * @param {string} targetPrompt - The specific items to detect (e.g., "cars", "pumpkins").
 * @returns {string} The complete, final prompt for the API call.
 */
export function generatePrompt(detectType, targetPrompt) {
  // Use the provided prompt as the target, or default to 'items' if none is provided.
  const finalTargetPrompt = (targetPrompt && targetPrompt.trim()) ? targetPrompt.trim() : 'items';

  // For 2D boxes, the prompt structure is a bit different, use the dedicated generator.
  if (detectType === '2d_bounding_boxes') {
    // The client-side allows a separate label prompt, the server API doesn't yet.
    // For now, we'll use a default label instruction.
    return generate2DPrompt(finalTargetPrompt, 'a text label');
  }

  const promptParts = DEFAULT_PROMPT_PARTS[detectType];
  if (!promptParts) {
    // Fallback to a generic 2D prompt if the type is unknown
    console.warn(`Unknown detectType "${detectType}" in generatePrompt. Falling back to 2D prompt.`);
    return generate2DPrompt(finalTargetPrompt, 'a text label');
  }

  // Assemble the prompt from parts, injecting the user's target.
  const newPromptParts = [...promptParts];
  newPromptParts[1] = finalTargetPrompt;

  // Join with the correct separator (no space for segmentation masks, space for others)
  const separator = detectType === 'segmentation_masks' ? '' : ' ';
  return newPromptParts.join(separator);
}

/**
 * Add calibration scale to image if requested
 * @param {Buffer} imageBuffer - Input image buffer
 * @param {boolean} showCalibration - Whether to show calibration
 * @param {Object} options - Calibration options
 * @returns {Promise<Buffer>} Image buffer with optional calibration
 */
export async function addCalibrationIfRequested(imageBuffer, showCalibration, options = {}) {
  if (!showCalibration) {
    return imageBuffer;
  }
  
  return addCalibrationScale(imageBuffer, {
    showGrid: true,
    showScale: true,
    scaleOpacity: 0.8,
    gridOpacity: 0.2,
    ...options
  });
}

/**
 * Generate comprehensive coordinate data for response
 * @param {Array} coordinates - Detection coordinates
 * @param {string} detectType - Type of detection
 * @param {number} imageWidth - Original image width
 * @param {number} imageHeight - Original image height
 * @returns {Object} Enhanced coordinate data
 */
export function generateCoordinateData(coordinates, detectType, imageWidth, imageHeight) {
  const coordinateReference = generateCoordinateReference(imageWidth, imageHeight);
  
  const enhancedCoordinates = coordinates.map((coord, index) => {
    let enhanced = { ...coord, index };
    
    switch (detectType) {
      case '2d_bounding_boxes':
      case 'segmentation_masks':
        enhanced.corners = {
          topLeft: { x: coord.x, y: coord.y },
          topRight: { x: coord.x + coord.width, y: coord.y },
          bottomLeft: { x: coord.x, y: coord.y + coord.height },
          bottomRight: { x: coord.x + coord.width, y: coord.y + coord.height }
        };
        enhanced.center = {
          x: coord.x + coord.width / 2,
          y: coord.y + coord.height / 2
        };
        enhanced.area = coord.width * coord.height;
        enhanced.pixelCoordinates = {
          x: Math.round(coord.x * imageWidth),
          y: Math.round(coord.y * imageHeight),
          width: Math.round(coord.width * imageWidth),
          height: Math.round(coord.height * imageHeight)
        };
        break;
        
      case 'points':
        enhanced.pixelCoordinates = {
          x: Math.round(coord.point.x * imageWidth),
          y: Math.round(coord.point.y * imageHeight)
        };
        break;
        
      case '3d_bounding_boxes':
        if (validate3DBoundingBox(coord)) {
          enhanced.vertices = calculate3DBoxVertices(coord);
          enhanced.volume = coord.size[0] * coord.size[1] * coord.size[2];
          enhanced.orientation = {
            roll: coord.rpy[0] * 180 / Math.PI,
            pitch: coord.rpy[1] * 180 / Math.PI, 
            yaw: coord.rpy[2] * 180 / Math.PI
          };
        }
        break;
    }
    
    return enhanced;
  });
  
  return {
    coordinates: enhancedCoordinates,
    coordinateSystem: coordinateReference,
    summary: {
      totalCount: coordinates.length,
      detectType,
      imageSize: { width: imageWidth, height: imageHeight }
    }
  };
}

/**
 * Draw segmentation masks on image
 * @param {Buffer} imageBuffer - Input image buffer
 * @param {Array} masks - Array of segmentation masks
 * @param {Object} options - Drawing options
 * @returns {Promise<Buffer>} Image buffer with annotations
 */
export async function drawSegmentationMasks(imageBuffer, masks, options = {}) {
  const { showCoordinates = true, imageScale = 1 } = options;
  
  const image = await loadImage(imageBuffer);
  const canvas = new Canvas(image.width * imageScale, image.height * imageScale);
  const ctx = canvas.getContext('2d');
  
  // Draw original image
  ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
  
  // Draw masks and bounding boxes
  for (const [index, mask] of masks.entries()) {
    const x = mask.x * canvas.width;
    const y = mask.y * canvas.height;
    const width = mask.width * canvas.width;
    const height = mask.height * canvas.height;
    
    // Draw bounding box
    ctx.strokeStyle = `rgb(${COLORS.BOUNDING_BOX.join(',')})`;
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, width, height);
    
    // Draw mask if available
    if (mask.imageData) {
      try {
        const maskImage = await loadImage(mask.imageData);
        ctx.globalAlpha = 0.5;
        ctx.drawImage(maskImage, x, y, width, height);
        ctx.globalAlpha = 1.0;
      } catch (error) {
        console.warn('Failed to draw mask:', error.message);
      }
    }
    
    // Draw label
    ctx.fillStyle = `rgb(${COLORS.BOUNDING_BOX.join(',')})`;
    ctx.font = '14px Arial';
    const labelWidth = ctx.measureText(mask.label).width;
    ctx.fillRect(x, y - 20, labelWidth + 8, 20);
    ctx.fillStyle = 'white';
    ctx.fillText(mask.label, x + 4, y - 6);
    
    // Draw coordinates if enabled
    if (showCoordinates) {
      const fontSize = Math.max(8, 12 * imageScale);
      ctx.font = `${fontSize}px monospace`;
      
      // Similar coordinate display as 2D bounding boxes
      const coords = [
        { pos: [x - 2, y - 2], text: `TL: (${mask.x.toFixed(3)}, ${mask.y.toFixed(3)})`, color: COLORS.COORDINATES.TOP_LEFT },
        { pos: [x + width - 78, y - 2], text: `TR: (${(mask.x + mask.width).toFixed(3)}, ${mask.y.toFixed(3)})`, color: COLORS.COORDINATES.TOP_RIGHT },
        { pos: [x - 2, y + height - 10], text: `BL: (${mask.x.toFixed(3)}, ${(mask.y + mask.height).toFixed(3)})`, color: COLORS.COORDINATES.BOTTOM_LEFT },
        { pos: [x + width - 78, y + height - 10], text: `BR: (${(mask.x + mask.width).toFixed(3)}, ${(mask.y + mask.height).toFixed(3)})`, color: COLORS.COORDINATES.BOTTOM_RIGHT }
      ];
      
      coords.forEach(coord => {
        ctx.fillStyle = `rgb(${coord.color.join(',')})`;
        ctx.fillRect(coord.pos[0], coord.pos[1], 80, 12);
        ctx.fillStyle = 'white';
        ctx.fillText(coord.text, coord.pos[0] + 2, coord.pos[1] + 10);
      });
    }
  }
  
  return canvas.toBuffer('image/png');
} 