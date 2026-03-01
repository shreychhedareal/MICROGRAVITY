# 🚀 Quick Start Guide

## Prerequisites

1. **Node.js** (v18 or higher)
2. **Google Gemini API Key** - Get yours at [Google AI Studio](https://aistudio.google.com/app/apikey)

## Setup Instructions

### 1. Install Dependencies
```bash
cd server
npm install
```

### 2. Configure Environment Variables
Run the interactive setup script:
```bash
npm run setup
```

This will:
- Prompt you for your Gemini API key
- Configure server settings
- Create a `.env` file with your configuration

**OR** manually create a `.env` file:
```bash
cp env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 3. Start the Server
```bash
npm start
```

The server will start on `http://localhost:3001`

## 🎯 Testing the API

### Option 1: Use the Test UI (Recommended)
1. Open your browser to: `http://localhost:3001/test-ui.html`
2. Upload an image or use one of the example images
3. Select detection type (2D/3D bounding boxes, points, segmentation)
4. Configure parameters and click "Detect Objects"

### Option 2: Use the Test Script
```bash
npm test
```

### Option 3: Manual API Testing

#### Health Check
```bash
curl http://localhost:3001/api/health
```

#### Detection with Base64 Image
```bash
curl -X POST http://localhost:3001/api/detect \
  -H "Content-Type: application/json" \
  -d '{
    "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD...",
    "detectType": "2d_bounding_boxes",
    "outputMode": "both"
  }'
```

#### Detection with File Upload
```bash
curl -X POST http://localhost:3001/api/detect \
  -F "imageFile=@/path/to/your/image.jpg" \
  -F "detectType=2d_bounding_boxes" \
  -F "outputMode=both"
```

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/` | GET | API documentation and info |
| `/api/health` | GET | Health check and service status |
| `/api/models` | GET | Available detection types |
| `/api/detect` | POST | Main detection endpoint |
| `/test-ui.html` | GET | Interactive test interface |

## 🔧 Configuration Options

### Detection Types
- `2d_bounding_boxes` - Rectangle bounding boxes
- `3d_bounding_boxes` - 3D oriented bounding boxes
- `points` - Point coordinates
- `segmentation_masks` - Segmentation with masks

### Output Modes
- `coordinates_only` - Just the detection coordinates
- `image_only` - Annotated image only
- `both` - Coordinates and annotated image

### Parameters
- `temperature` (0-1): AI creativity level
- `maxResults` (1-25): Maximum detections to return
- `showCoordinates` (boolean): Show labels on image
- `fov` (30-120°): Field of view for 3D boxes
- `imageScale` (0.5-2.0): Output image scaling

## 🐳 Docker Deployment

### Build and Run
```bash
docker build -t spatial-api .
docker run -p 3001:3001 -e GEMINI_API_KEY=your_key_here spatial-api
```

### Using Docker Compose
```bash
# Edit docker-compose.yml with your API key
docker-compose up
```

## 🔍 Troubleshooting

### Common Issues

1. **API Key Error**
   - Ensure your `GEMINI_API_KEY` is set in `.env`
   - Verify the key is valid at Google AI Studio

2. **CORS Issues**
   - Check `ALLOWED_ORIGINS` in `.env`
   - Default allows localhost:3000, localhost:3001, localhost:5173

3. **Rate Limiting**
   - Default: 100 requests per 15 minutes per IP
   - Adjust `RATE_LIMIT_MAX_REQUESTS` and `RATE_LIMIT_WINDOW_MS`

4. **Image Processing Errors**
   - Ensure image is valid (JPEG, PNG, WebP, GIF)
   - Check image size (max 50MB)
   - Verify image URL is accessible

### Debug Mode
Set `NODE_ENV=development` in `.env` for detailed error messages.

## 📝 Example Responses

### Successful Detection
```json
{
  "success": true,
  "detectType": "2d_bounding_boxes",
  "coordinates": [
    {
      "label": "person",
      "x": 0.25,
      "y": 0.30,
      "width": 0.40,
      "height": 0.60,
      "confidence": 0.95
    }
  ],
  "annotatedImage": "data:image/jpeg;base64,/9j/4AAQ...",
  "metadata": {
    "processingTime": 1250,
    "resultCount": 1,
    "imageSize": { "width": 800, "height": 600 }
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": "Invalid detection type",
  "details": "Must be one of: 2d_bounding_boxes, 3d_bounding_boxes, points, segmentation_masks"
}
```

## 🔗 Useful Links

- [Google Gemini API Documentation](https://ai.google.dev/docs)
- [Test UI](http://localhost:3001/test-ui.html)
- [API Health Check](http://localhost:3001/api/health)
- [Available Models](http://localhost:3001/api/models)

## 🆘 Support

If you encounter issues:
1. Check the server logs for error messages
2. Verify your API key is valid
3. Test with the provided example images
4. Check network connectivity for external image URLs 