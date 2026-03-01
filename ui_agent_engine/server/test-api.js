/**
 * Test script for Spatial Understanding API
 * Run with: node test-api.js
 */

import fetch from 'node-fetch';
import fs from 'fs';
import path from 'path';

const API_BASE_URL = 'http://localhost:3001/api';

// Test image (small base64 encoded test image)
const TEST_IMAGE_BASE64 = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';

async function testHealthEndpoint() {
  console.log('🔍 Testing health endpoint...');
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    const data = await response.json();
    console.log('✅ Health check:', data.status);
    console.log('   Gemini service ready:', data.geminiServiceReady);
    return data.geminiServiceReady;
  } catch (error) {
    console.error('❌ Health check failed:', error.message);
    return false;
  }
}

async function testModelsEndpoint() {
  console.log('\n🔍 Testing models endpoint...');
  try {
    const response = await fetch(`${API_BASE_URL}/models`);
    const data = await response.json();
    console.log('✅ Available detection types:');
    Object.keys(data.detectTypes).forEach(type => {
      console.log(`   - ${type}: ${data.detectTypes[type].description}`);
    });
  } catch (error) {
    console.error('❌ Models endpoint failed:', error.message);
  }
}

async function test2DBoundingBoxes() {
  console.log('\n🔍 Testing 2D bounding boxes detection...');
  try {
    const response = await fetch(`${API_BASE_URL}/detect`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        image: TEST_IMAGE_BASE64,
        detectType: '2d_bounding_boxes',
        outputMode: 'coordinates_only',
        maxResults: 5
      })
    });

    const data = await response.json();
    if (data.success) {
      console.log('✅ 2D bounding boxes detected:', data.coordinates?.length || 0);
      if (data.coordinates?.length > 0) {
        console.log('   First result:', data.coordinates[0]);
      }
    } else {
      console.log('⚠️  2D detection response:', data.error);
    }
  } catch (error) {
    console.error('❌ 2D bounding boxes test failed:', error.message);
  }
}

async function testPointsDetection() {
  console.log('\n🔍 Testing points detection...');
  try {
    const response = await fetch(`${API_BASE_URL}/detect`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        image: TEST_IMAGE_BASE64,
        detectType: 'points',
        outputMode: 'coordinates_only',
        prompt: 'Find interesting points in this image',
        maxResults: 3
      })
    });

    const data = await response.json();
    if (data.success) {
      console.log('✅ Points detected:', data.coordinates?.length || 0);
      if (data.coordinates?.length > 0) {
        console.log('   First point:', data.coordinates[0]);
      }
    } else {
      console.log('⚠️  Points detection response:', data.error);
    }
  } catch (error) {
    console.error('❌ Points detection test failed:', error.message);
  }
}

async function test3DBoundingBoxes() {
  console.log('\n🔍 Testing 3D bounding boxes detection...');
  try {
    const response = await fetch(`${API_BASE_URL}/detect`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        image: TEST_IMAGE_BASE64,
        detectType: '3d_bounding_boxes',
        outputMode: 'coordinates_only',
        fov: 60,
        maxResults: 5
      })
    });

    const data = await response.json();
    if (data.success) {
      console.log('✅ 3D bounding boxes detected:', data.coordinates?.length || 0);
      if (data.coordinates?.length > 0) {
        console.log('   First 3D box:', data.coordinates[0]);
      }
    } else {
      console.log('⚠️  3D detection response:', data.error);
    }
  } catch (error) {
    console.error('❌ 3D bounding boxes test failed:', error.message);
  }
}

async function testWithImageOutput() {
  console.log('\n🔍 Testing with image output...');
  try {
    const response = await fetch(`${API_BASE_URL}/detect`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        image: TEST_IMAGE_BASE64,
        detectType: '2d_bounding_boxes',
        outputMode: 'both',
        showCoordinates: true,
        imageScale: 1.0
      })
    });

    const data = await response.json();
    if (data.success) {
      console.log('✅ Detection with image output completed');
      console.log('   Coordinates:', data.coordinates?.length || 0);
      console.log('   Annotated image:', data.annotatedImage ? 'Generated' : 'Not generated');
      
      // Save annotated image if available
      if (data.annotatedImage) {
        const base64Data = data.annotatedImage.replace(/^data:image\/\w+;base64,/, '');
        fs.writeFileSync('test-output.png', base64Data, 'base64');
        console.log('   Saved annotated image as test-output.png');
      }
    } else {
      console.log('⚠️  Image output test response:', data.error);
    }
  } catch (error) {
    console.error('❌ Image output test failed:', error.message);
  }
}

async function testRateLimiting() {
  console.log('\n🔍 Testing rate limiting (making 5 rapid requests)...');
  const promises = [];
  
  for (let i = 0; i < 5; i++) {
    promises.push(
      fetch(`${API_BASE_URL}/health`)
        .then(res => ({ status: res.status, index: i }))
        .catch(err => ({ error: err.message, index: i }))
    );
  }
  
  const results = await Promise.all(promises);
  const successful = results.filter(r => r.status === 200).length;
  const rateLimited = results.filter(r => r.status === 429).length;
  
  console.log(`✅ Rate limiting test: ${successful} successful, ${rateLimited} rate limited`);
}

async function runAllTests() {
  console.log('🚀 Starting API tests...\n');
  
  // Test health first
  const isHealthy = await testHealthEndpoint();
  
  if (!isHealthy) {
    console.log('\n❌ Server is not healthy. Make sure:');
    console.log('   1. Server is running on http://localhost:3001');
    console.log('   2. GEMINI_API_KEY is set in environment variables');
    console.log('   3. All dependencies are installed');
    return;
  }
  
  // Run other tests
  await testModelsEndpoint();
  await test2DBoundingBoxes();
  await testPointsDetection();
  await test3DBoundingBoxes();
  await testWithImageOutput();
  await testRateLimiting();
  
  console.log('\n🎉 All tests completed!');
  console.log('\nNote: Some tests may show warnings if the test image is too simple');
  console.log('for meaningful object detection. Try with real images for better results.');
}

// Run tests if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  runAllTests().catch(console.error);
} 