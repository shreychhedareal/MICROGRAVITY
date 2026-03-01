/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * Calibration Scale Module
 * Draws coordinate grids and calibration scales on images
 * Matches the client-side CalibrationScale component functionality
 */

import { Canvas, loadImage } from 'skia-canvas';

/**
 * Generate tick marks for calibration scale
 * @param {number} maxValue - Maximum value (width or height)
 * @returns {Array<Object>} Array of tick objects with position, type, and label
 */
export function generateTicks(maxValue) {
  const ticks = [];
  
  // Create ticks every 0.05 (minor), 0.1 (middle), 0.2 (major)
  for (let i = 0; i <= 20; i++) {
    const value = i / 20; // 0 to 1 in 0.05 increments
    const isMajor = i % 4 === 0; // Every 0.2 is major
    const isMiddle = i % 2 === 0; // Every 0.1 is middle
    
    ticks.push({
      value,
      position: value * maxValue,
      isMajor,
      isMiddle,
      label: isMajor ? value.toFixed(1) : ''
    });
  }
  
  return ticks;
}

/**
 * Draw calibration scale on canvas context
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {number} width - Canvas width
 * @param {number} height - Canvas height
 * @param {Object} options - Drawing options
 */
export function drawCalibrationScale(ctx, width, height, options = {}) {
  const {
    showGrid = true,
    showScale = true,
    scaleOpacity = 0.8,
    gridOpacity = 0.2,
    fontSize = 10,
    fontFamily = 'Arial',
    scaleHeight = 24,
    scaleWidth = 24
  } = options;
  
  if (!showScale && !showGrid) return;
  
  const horizontalTicks = generateTicks(width);
  const verticalTicks = generateTicks(height);
  
  // Save context state
  ctx.save();
  
  if (showScale) {
    // Draw horizontal scale (top edge)
    drawHorizontalScale(ctx, width, height, horizontalTicks, {
      scaleOpacity,
      fontSize,
      fontFamily,
      scaleHeight
    });
    
    // Draw vertical scale (left edge)
    drawVerticalScale(ctx, width, height, verticalTicks, {
      scaleOpacity,
      fontSize,
      fontFamily,
      scaleWidth
    });
    
    // Draw corner markers
    drawCornerMarkers(ctx, width, height, { fontSize });
  }
  
  if (showGrid) {
    // Draw grid lines
    drawGridLines(ctx, width, height, horizontalTicks, verticalTicks, {
      gridOpacity
    });
  }
  
  // Restore context state
  ctx.restore();
}

/**
 * Draw horizontal scale at top of image
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {number} width - Canvas width
 * @param {number} height - Canvas height
 * @param {Array<Object>} ticks - Tick marks
 * @param {Object} options - Drawing options
 */
function drawHorizontalScale(ctx, width, height, ticks, options) {
  const { scaleOpacity, fontSize, fontFamily, scaleHeight } = options;
  
  // Draw background gradient
  const gradient = ctx.createLinearGradient(0, 0, 0, scaleHeight);
  gradient.addColorStop(0, `rgba(0, 0, 0, ${scaleOpacity})`);
  gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
  
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, scaleHeight);
  
  // Draw tick marks and labels
  ctx.strokeStyle = `rgba(255, 255, 255, ${scaleOpacity * 1.1})`;
  ctx.fillStyle = `rgba(255, 255, 255, ${scaleOpacity * 1.1})`;
  ctx.font = `${fontSize}px ${fontFamily}`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  
  ticks.forEach(tick => {
    const x = tick.position;
    const y1 = tick.isMajor ? 0 : tick.isMiddle ? 2 : 4;
    const y2 = tick.isMajor ? 12 : tick.isMiddle ? 8 : 6;
    
    // Draw tick mark
    ctx.lineWidth = tick.isMajor ? 2 : 1;
    ctx.beginPath();
    ctx.moveTo(x, y1);
    ctx.lineTo(x, y2);
    ctx.stroke();
    
    // Draw label
    if (tick.label) {
      ctx.fillText(tick.label, x, 18);
    }
  });
  
  // Draw scale label
  ctx.font = `${fontSize - 2}px ${fontFamily}`;
  ctx.textAlign = 'right';
  ctx.fillText('Width (0→1)', width - 5, 12);
}

/**
 * Draw vertical scale at left of image
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {number} width - Canvas width
 * @param {number} height - Canvas height
 * @param {Array<Object>} ticks - Tick marks
 * @param {Object} options - Drawing options
 */
function drawVerticalScale(ctx, width, height, ticks, options) {
  const { scaleOpacity, fontSize, fontFamily, scaleWidth } = options;
  
  // Draw background gradient
  const gradient = ctx.createLinearGradient(0, 0, scaleWidth, 0);
  gradient.addColorStop(0, `rgba(0, 0, 0, ${scaleOpacity})`);
  gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
  
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, scaleWidth, height);
  
  // Draw tick marks and labels
  ctx.strokeStyle = `rgba(255, 255, 255, ${scaleOpacity * 1.1})`;
  ctx.fillStyle = `rgba(255, 255, 255, ${scaleOpacity * 1.1})`;
  ctx.font = `${fontSize}px ${fontFamily}`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  
  ticks.forEach(tick => {
    const y = tick.position;
    const x1 = tick.isMajor ? 0 : tick.isMiddle ? 2 : 4;
    const x2 = tick.isMajor ? 12 : tick.isMiddle ? 8 : 6;
    
    // Draw tick mark
    ctx.lineWidth = tick.isMajor ? 2 : 1;
    ctx.beginPath();
    ctx.moveTo(x1, y);
    ctx.lineTo(x2, y);
    ctx.stroke();
    
    // Draw label (rotated)
    if (tick.label) {
      ctx.save();
      ctx.translate(16, y);
      ctx.rotate(-Math.PI / 2);
      ctx.fillText(tick.label, 0, 0);
      ctx.restore();
    }
  });
  
  // Draw scale label (rotated)
  ctx.save();
  ctx.translate(12, 15);
  ctx.rotate(-Math.PI / 2);
  ctx.font = `${fontSize - 2}px ${fontFamily}`;
  ctx.textAlign = 'center';
  ctx.fillText('Height (0→1)', 0, 0);
  ctx.restore();
}

/**
 * Draw corner markers
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {number} width - Canvas width
 * @param {number} height - Canvas height
 * @param {Object} options - Drawing options
 */
function drawCornerMarkers(ctx, width, height, options) {
  const { fontSize } = options;
  const markerSize = Math.max(32, fontSize * 2.4);
  
  // Top-left corner (origin)
  ctx.fillStyle = 'rgba(255, 235, 59, 0.8)'; // Yellow
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(markerSize, 0);
  ctx.lineTo(0, markerSize);
  ctx.closePath();
  ctx.fill();
  
  ctx.fillStyle = 'rgba(0, 0, 0, 0.9)';
  ctx.font = `bold ${fontSize}px Arial`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('0,0', markerSize / 2 - 2, markerSize / 2 - 2);
  
  // Bottom-right corner
  ctx.fillStyle = 'rgba(244, 67, 54, 0.8)'; // Red
  ctx.beginPath();
  ctx.moveTo(width, height);
  ctx.lineTo(width - markerSize, height);
  ctx.lineTo(width, height - markerSize);
  ctx.closePath();
  ctx.fill();
  
  ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
  ctx.fillText('1,1', width - markerSize / 2 + 2, height - markerSize / 2 + 2);
}

/**
 * Draw grid lines
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {number} width - Canvas width
 * @param {number} height - Canvas height
 * @param {Array<Object>} horizontalTicks - Horizontal tick marks
 * @param {Array<Object>} verticalTicks - Vertical tick marks
 * @param {Object} options - Drawing options
 */
function drawGridLines(ctx, width, height, horizontalTicks, verticalTicks, options) {
  const { gridOpacity } = options;
  
  ctx.strokeStyle = `rgba(255, 255, 255, ${gridOpacity})`;
  ctx.lineWidth = 0.5;
  ctx.setLineDash([2, 4]);
  
  // Vertical grid lines
  horizontalTicks
    .filter(tick => tick.isMajor && tick.value > 0 && tick.value < 1)
    .forEach(tick => {
      ctx.beginPath();
      ctx.moveTo(tick.position, 0);
      ctx.lineTo(tick.position, height);
      ctx.stroke();
    });
  
  // Horizontal grid lines
  verticalTicks
    .filter(tick => tick.isMajor && tick.value > 0 && tick.value < 1)
    .forEach(tick => {
      ctx.beginPath();
      ctx.moveTo(0, tick.position);
      ctx.lineTo(width, tick.position);
      ctx.stroke();
    });
  
  // Reset line dash
  ctx.setLineDash([]);
}

/**
 * Add calibration scale overlay to image buffer
 * @param {Buffer} imageBuffer - Input image buffer
 * @param {Object} options - Calibration options
 * @returns {Promise<Buffer>} Image buffer with calibration overlay
 */
export async function addCalibrationScale(imageBuffer, options = {}) {
  const image = await loadImage(imageBuffer);
  const canvas = new Canvas(image.width, image.height);
  const ctx = canvas.getContext('2d');
  
  // Draw original image
  ctx.drawImage(image, 0, 0);
  
  // Add calibration scale
  drawCalibrationScale(ctx, image.width, image.height, options);
  
  return canvas.toBuffer('image/png');
}

/**
 * Generate coordinate reference data
 * @param {number} width - Image width
 * @param {number} height - Image height
 * @returns {Object} Coordinate reference information
 */
export function generateCoordinateReference(width, height) {
  return {
    coordinateSystem: 'normalized',
    origin: { x: 0, y: 0, position: 'top-left' },
    scale: { x: width, y: height },
    bounds: {
      minX: 0, maxX: 1,
      minY: 0, maxY: 1
    },
    pixelToNormalized: (pixelX, pixelY) => ({
      x: pixelX / width,
      y: pixelY / height
    }),
    normalizedToPixel: (normX, normY) => ({
      x: Math.round(normX * width),
      y: Math.round(normY * height)
    }),
    majorTicks: generateTicks(1).filter(t => t.isMajor),
    minorTicks: generateTicks(1).filter(t => !t.isMajor)
  };
} 