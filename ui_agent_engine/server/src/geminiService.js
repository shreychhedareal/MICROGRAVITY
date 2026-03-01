/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { GoogleGenerativeAI, HarmCategory, HarmBlockThreshold } from '@google/generative-ai';
import { 
  DETECT_TYPES, 
  DEFAULT_PROMPTS, 
  SAFETY_SETTINGS,
  VALIDATION 
} from './types.js';
import {
  format2DBoundingBoxes,
  format3DBoundingBoxes,
  formatPoints,
  formatSegmentationMasks,
  processImage,
  bufferToDataURL,
  generatePrompt
} from './utils.js';

// Align model names with the client-side implementation
const MODEL_2_FLASH = 'gemini-2.0-flash';
const MODEL_2_5_FLASH = 'gemini-2.5-flash';

class GeminiService {
  constructor(apiKey) {
    if (!apiKey) {
      throw new Error('Gemini API key is required');
    }
    this.genAI = new GoogleGenerativeAI(apiKey);
    this.models = {};
    // All tasks except for segmentation use 2.0 Flash.
    this.models[DETECT_TYPES['2D_BOUNDING_BOXES']] = this.genAI.getGenerativeModel({ model: MODEL_2_FLASH, safetySettings: SAFETY_SETTINGS });
    this.models[DETECT_TYPES['3D_BOUNDING_BOXES']] = this.genAI.getGenerativeModel({ model: MODEL_2_FLASH, safetySettings: SAFETY_SETTINGS });
    this.models[DETECT_TYPES.POINTS] = this.genAI.getGenerativeModel({ model: MODEL_2_FLASH, safetySettings: SAFETY_SETTINGS });
    // Segmentation uses 2.5 Flash.
    this.models[DETECT_TYPES.SEGMENTATION_MASKS] = this.genAI.getGenerativeModel({ model: MODEL_2_5_FLASH, safetySettings: SAFETY_SETTINGS });
  }

  /**
   * Process detection request
   * @param {Object} params - Detection parameters
   * @returns {Promise<Object>} Detection results
   */
  async detect(params) {
    const {
      imageBuffer,
      detectType,
      prompt,
      temperature = 0.5,
      maxResults,
      fov = 60
    } = params;

    try {
      // Process image for AI
      const processedImage = await processImage(imageBuffer, 640);
      const imageDataURL = bufferToDataURL(processedImage.buffer);
      
      // Build the full instructional prompt, correctly using the 'prompt' parameter as the target.
      const finalPrompt = this.buildPrompt(detectType, prompt);
      
      // Process detection with Gemini
      const model = this.models[detectType];
      if (!model) {
        return { success: false, error: `Unsupported detection type: ${detectType}` };
      }
      
      const generationConfig = {
        temperature,
        maxOutputTokens: VALIDATION.MAX_OUTPUT_TOKENS,
      };

      // Disable thinking when using 2.5 Flash (for segmentation), matching client behavior
      if (detectType === DETECT_TYPES.SEGMENTATION_MASKS) {
        generationConfig.thinkingConfig = { thinkingBudget: 0 };
      }

      const request = {
        contents: [
          {role: 'user', parts: [
            {
              inlineData: {
                data: processedImage.buffer.toString('base64'),
                mimeType: 'image/png',
              },
            },
            {text: finalPrompt},
          ]}
        ],
        generationConfig: generationConfig
      };
      
      const result = await model.generateContentStream(request);

      // Aggregate the response from the stream
      let fullResponse = '';
      for await (const chunk of result.stream) {
        fullResponse += chunk.text();
      }
      
      let jsonString = fullResponse;

      // More robust cleanup: find the start and end of the JSON block.
      // Handles cases where the model returns markdown or conversational text.
      if (jsonString.includes('```json')) {
        jsonString = jsonString.split('```json')[1].split('```')[0];
      } else {
        const startIndex = jsonString.indexOf('[');
        const endIndex = jsonString.lastIndexOf(']');
        if (startIndex !== -1 && endIndex !== -1) {
          jsonString = jsonString.substring(startIndex, endIndex + 1);
        }
      }

      try {
        const parsedResponse = JSON.parse(jsonString);
        const results = this.formatResults(detectType, parsedResponse);

        return {
          success: true,
          detectType,
          results,
          metadata: {
            originalImageDimensions: {
              width: processedImage.originalWidth,
              height: processedImage.originalHeight
            },
            processedImageDimensions: {
              width: processedImage.width,
              height: processedImage.height
            },
            model: model.model,
            temperature: generationConfig.temperature,
            prompt: finalPrompt
          }
        };
      } catch (parseError) {
        console.error('🔴 Failed to parse JSON from Gemini response:', parseError.message);
        console.error('Raw response was:', fullResponse);
        return { 
          success: false, 
          error: 'Failed to parse JSON response from AI',
          details: `The model returned a non-JSON response. Raw text: "${fullResponse.substring(0, 100)}..."` 
        };
      }
    } catch (error) {
      console.error(`🔴 Error during Gemini API call for ${detectType}:`, error);
      return { success: false, error: 'Error processing request with Gemini', details: error.message };
    }
  }

  /**
   * Builds the full instructional prompt for the Gemini API.
   * @param {string} detectType - The type of detection to perform.
   * @param {string} targetPrompt - The specific objects to detect (e.g., "cars", "people").
   * @returns {string} The complete prompt string.
   */
  buildPrompt(detectType, targetPrompt) {
    // This now correctly uses the API's 'prompt' as the target for detection.
    return generatePrompt(detectType, targetPrompt);
  }

  /**
   * Format AI results based on detection type
   * @param {string} detectType - Type of detection
   * @param {Array} parsedResponse - Parsed AI response
   * @returns {Array} Formatted results
   */
  formatResults(detectType, parsedResponse) {
    switch (detectType) {
      case DETECT_TYPES['2D_BOUNDING_BOXES']:
        return format2DBoundingBoxes(parsedResponse);
        
      case DETECT_TYPES['3D_BOUNDING_BOXES']:
        return format3DBoundingBoxes(parsedResponse);
        
      case DETECT_TYPES.POINTS:
        return formatPoints(parsedResponse);
        
      case DETECT_TYPES.SEGMENTATION_MASKS:
        return formatSegmentationMasks(parsedResponse);
        
      default:
        throw new Error(`Unsupported detection type: ${detectType}`);
    }
  }

  /**
   * Get available models and their capabilities
   * @returns {Object} Available models info
   */
  getModelsInfo() {
    return {
      models: {
        'gemini-2.0-flash': {
          supportedTypes: [
            DETECT_TYPES['2D_BOUNDING_BOXES'],
            DETECT_TYPES['3D_BOUNDING_BOXES'],
            DETECT_TYPES.POINTS
          ],
          description: 'Fast and accurate for most detection tasks'
        },
        'gemini-2.5-flash': {
          supportedTypes: [
            DETECT_TYPES.SEGMENTATION_MASKS
          ],
          description: 'Specialized for segmentation tasks'
        }
      },
      detectTypes: {
        [DETECT_TYPES['2D_BOUNDING_BOXES']]: {
          description: '2D bounding boxes around objects',
          maxResults: VALIDATION.MAX_MAX_RESULTS_2D,
          outputFormat: {
            x: 'number (0-1, relative to image width)',
            y: 'number (0-1, relative to image height)', 
            width: 'number (0-1, relative to image width)',
            height: 'number (0-1, relative to image height)',
            label: 'string (object description)'
          }
        },
        [DETECT_TYPES['3D_BOUNDING_BOXES']]: {
          description: '3D bounding boxes with position, size and rotation',
          maxResults: VALIDATION.MAX_MAX_RESULTS_3D,
          outputFormat: {
            center: 'array [x, y, z] (3D position)',
            size: 'array [width, height, depth] (3D dimensions)',
            rpy: 'array [roll, pitch, yaw] (rotation in radians)',
            label: 'string (object description)'
          }
        },
        [DETECT_TYPES.POINTS]: {
          description: 'Point locations of objects',
          maxResults: VALIDATION.MAX_MAX_RESULTS_POINTS,
          outputFormat: {
            point: {
              x: 'number (0-1, relative to image width)',
              y: 'number (0-1, relative to image height)'
            },
            label: 'string (object description)'
          }
        },
        [DETECT_TYPES.SEGMENTATION_MASKS]: {
          description: 'Segmentation masks with bounding boxes',
          maxResults: VALIDATION.MAX_MAX_RESULTS_2D,
          outputFormat: {
            x: 'number (0-1, relative to image width)',
            y: 'number (0-1, relative to image height)',
            width: 'number (0-1, relative to image width)',
            height: 'number (0-1, relative to image height)',
            label: 'string (object description)',
            imageData: 'string (mask data)'
          }
        }
      }
    };
  }
}

export default GeminiService; 