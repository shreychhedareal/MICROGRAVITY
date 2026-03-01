/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import express from 'express';
import multer from 'multer';
import GeminiService from './geminiService.js';
import { 
  DETECT_TYPES, 
  OUTPUT_MODES, 
  STATUS_CODES, 
  VALIDATION 
} from './types.js';
import {
  loadImageFromInput,
  validateRequest,
  draw2DBoundingBoxes,
  drawPoints,
  draw3DBoundingBoxes,
  bufferToDataURL,
  drawSegmentationMasks
} from './utils.js';

const router = express.Router();

// Configure multer for file uploads
const upload = multer({
  limits: {
    fileSize: VALIDATION.MAX_IMAGE_SIZE_MB * 1024 * 1024 // Convert MB to bytes
  },
  fileFilter: (req, file, cb) => {
    if (file.mimetype.startsWith('image/')) {
      cb(null, true);
    } else {
      cb(new Error('Only image files are allowed'), false);
    }
  }
});

// Lazily initialize Gemini service
let geminiService = null;
try {
  // process.env is guaranteed to be populated here thanks to the preload script
  if (process.env.GEMINI_API_KEY) {
    geminiService = new GeminiService(process.env.GEMINI_API_KEY);
    console.log('✅ Gemini service initialized successfully.');
  } else {
    throw new Error('GEMINI_API_KEY is not defined in the environment.');
  }
} catch (error) {
  console.error('🔴 Failed to initialize Gemini service:', error.message);
}

/**
 * Health check endpoint
 */
router.get('/health', (req, res) => {
  const health = {
    status: 'ok',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    version: process.env.npm_package_version || '1.0.0',
    geminiServiceReady: !!geminiService
  };

  if (!geminiService) {
    health.status = 'degraded';
    health.warning = 'Gemini service not available - check GEMINI_API_KEY';
  }

  res.status(STATUS_CODES.SUCCESS).json(health);
});

/**
 * Get available models and detection types
 */
router.get('/models', (req, res) => {
  if (!geminiService) {
    return res.status(STATUS_CODES.INTERNAL_ERROR).json({
      success: false,
      error: 'Gemini service not available'
    });
  }

  try {
    const modelsInfo = geminiService.getModelsInfo();
    res.status(STATUS_CODES.SUCCESS).json({
      success: true,
      ...modelsInfo
    });
  } catch (error) {
    res.status(STATUS_CODES.INTERNAL_ERROR).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * Main detection endpoint
 * Supports both JSON and multipart/form-data
 */
router.post('/detect', upload.single('imageFile'), async (req, res) => {
  try {
    // Check if Gemini service is available
    if (!geminiService) {
      return res.status(STATUS_CODES.INTERNAL_ERROR).json({
        success: false,
        error: 'Gemini service not available - check GEMINI_API_KEY configuration'
      });
    }

    // Extract parameters from request
    let params;
    if (req.file) {
      // Handle multipart/form-data
      params = {
        image: req.file.buffer,
        detectType: req.body.detectType,
        prompt: req.body.prompt,
        temperature: req.body.temperature ? parseFloat(req.body.temperature) : 0.5,
        maxResults: req.body.maxResults ? parseInt(req.body.maxResults) : undefined,
        outputMode: req.body.outputMode || OUTPUT_MODES.COORDINATES_ONLY,
        showCoordinates: req.body.showCoordinates !== 'false',
        fov: req.body.fov ? parseFloat(req.body.fov) : 60,
        imageScale: req.body.imageScale ? parseFloat(req.body.imageScale) : 1.0
      };
    } else {
      // Handle JSON request
      params = {
        image: req.body.image,
        detectType: req.body.detectType,
        prompt: req.body.prompt,
        temperature: req.body.temperature || 0.5,
        maxResults: req.body.maxResults,
        outputMode: req.body.outputMode || OUTPUT_MODES.COORDINATES_ONLY,
        showCoordinates: req.body.showCoordinates !== false,
        fov: req.body.fov || 60,
        imageScale: req.body.imageScale || 1.0
      };
    }

    // Validate request parameters
    const validation = validateRequest(params);
    if (!validation.isValid) {
      return res.status(STATUS_CODES.BAD_REQUEST).json({
        success: false,
        error: 'Invalid request parameters',
        details: validation.errors
      });
    }

    // Load image
    let imageBuffer;
    if (req.file) {
      imageBuffer = req.file.buffer;
    } else {
      try {
        imageBuffer = await loadImageFromInput(params.image);
      } catch (error) {
        return res.status(STATUS_CODES.BAD_REQUEST).json({
          success: false,
          error: 'Failed to load image',
          details: error.message
        });
      }
    }

    // Process detection
    const detectionResult = await geminiService.detect({
      imageBuffer,
      detectType: params.detectType,
      prompt: params.prompt,
      temperature: params.temperature,
      maxResults: params.maxResults,
      fov: params.fov
    });

    if (!detectionResult.success) {
      return res.status(STATUS_CODES.INTERNAL_ERROR).json(detectionResult);
    }

    // Prepare response based on output mode
    const response = {
      success: true,
      detectType: detectionResult.detectType,
      metadata: {
        ...detectionResult.metadata,
        outputMode: params.outputMode,
        showCoordinates: params.showCoordinates,
        imageScale: params.imageScale,
        timestamp: new Date().toISOString(),
        resultCount: detectionResult.results.length
      }
    };

    // Add coordinates if requested
    if (params.outputMode === OUTPUT_MODES.COORDINATES_ONLY || params.outputMode === OUTPUT_MODES.BOTH) {
      response.coordinates = detectionResult.results;
    }

    // Add annotated image if requested
    if (params.outputMode === OUTPUT_MODES.IMAGE_ONLY || params.outputMode === OUTPUT_MODES.BOTH) {
      try {
        const annotatedImageBuffer = await generateAnnotatedImage(
          imageBuffer,
          detectionResult.results,
          params.detectType,
          {
            showCoordinates: params.showCoordinates,
            imageScale: params.imageScale,
            fov: params.fov
          }
        );
        response.annotatedImage = bufferToDataURL(annotatedImageBuffer);
      } catch (error) {
        console.error('Failed to generate annotated image:', error);
        response.warning = 'Failed to generate annotated image: ' + error.message;
      }
    }

    res.status(STATUS_CODES.SUCCESS).json(response);

  } catch (error) {
    console.error('Detection endpoint error:', error);
    res.status(STATUS_CODES.INTERNAL_ERROR).json({
      success: false,
      error: 'Internal server error',
      details: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

/**
 * Generate annotated image based on detection type
 * @param {Buffer} imageBuffer - Original image buffer
 * @param {Array} results - Detection results
 * @param {string} detectType - Type of detection
 * @param {Object} options - Drawing options
 * @returns {Promise<Buffer>} Annotated image buffer
 */
async function generateAnnotatedImage(imageBuffer, results, detectType, options = {}) {
  const { showCoordinates = true, imageScale = 1, fov = 60 } = options;

  switch (detectType) {
    case DETECT_TYPES['2D_BOUNDING_BOXES']:
      return await draw2DBoundingBoxes(imageBuffer, results, { showCoordinates, imageScale });
      
    case DETECT_TYPES.POINTS:
      return await drawPoints(imageBuffer, results, { showCoordinates, imageScale });
      
    case DETECT_TYPES['3D_BOUNDING_BOXES']:
      return await draw3DBoundingBoxes(imageBuffer, results, { showCoordinates, imageScale, fov });
      
    case DETECT_TYPES.SEGMENTATION_MASKS:
      return await drawSegmentationMasks(imageBuffer, results, { showCoordinates, imageScale });
      
    default:
      // Default to drawing 2D boxes if type is unknown or not visually representable
      console.warn(`Unsupported detectType for image annotation: ${detectType}. Falling back to 2D boxes.`);
      return await draw2DBoundingBoxes(imageBuffer, results, { showCoordinates, imageScale });
  }
}

/**
 * Error handling middleware
 */
router.use((error, req, res, next) => {
  console.error('Route error:', error);

  if (error instanceof multer.MulterError) {
    if (error.code === 'LIMIT_FILE_SIZE') {
      return res.status(STATUS_CODES.PAYLOAD_TOO_LARGE).json({
        success: false,
        error: `File too large. Maximum size is ${VALIDATION.MAX_IMAGE_SIZE_MB}MB`
      });
    }
    return res.status(STATUS_CODES.BAD_REQUEST).json({
      success: false,
      error: 'File upload error: ' + error.message
    });
  }

  if (error.message === 'Only image files are allowed') {
    return res.status(STATUS_CODES.BAD_REQUEST).json({
      success: false,
      error: 'Only image files are allowed'
    });
  }

  res.status(STATUS_CODES.INTERNAL_ERROR).json({
    success: false,
    error: 'Internal server error',
    details: process.env.NODE_ENV === 'development' ? error.message : undefined
  });
});

export default router; 