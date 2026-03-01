# Spatial Understanding API Server

A powerful API server for spatial understanding using Google Gemini AI models. This server provides endpoints for detecting objects, bounding boxes, points, and segmentation masks in images.

## Features

- **Multiple Detection Types**: 2D/3D bounding boxes, points, segmentation masks
- **Flexible Input**: Support for base64 images, URLs, and file uploads
- **Multiple Output Modes**: Coordinates only, annotated images, or both
- **Real-time Processing**: Fast image processing with Google Gemini AI
- **Rate Limiting**: Built-in rate limiting for API protection
- **CORS Support**: Configurable CORS for web applications
- **Comprehensive Validation**: Input validation and error handling

## Quick Start

### Prerequisites

- Node.js 18+ 
- Google Gemini API key
- npm or yarn

### Installation

1. **Clone and navigate to server directory**:
   ```bash
   cd server
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Set up environment variables**:
   ```bash
   cp env.example .env
   ```
   
   Edit `.env` and add your Gemini API key:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   PORT=3001
   NODE_ENV=development
   ```

4. **Start the server**:
   ```bash
   # Development mode with auto-reload
   npm run dev
   
   # Production mode
   npm start
   ```

The server will start on `http://localhost:3001`

## API Endpoints

### GET `/api/health`
Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "uptime": 123.45,
  "version": "1.0.0",
  "geminiServiceReady": true
}
```

### GET `/api/models`
Get available models and detection types.

**Response:**
```json
{
  "success": true,
  "models": {
    "gemini-2.0-flash": {
      "supportedTypes": ["2d_bounding_boxes", "3d_bounding_boxes", "points"],
      "description": "Fast and accurate for most detection tasks"
    }
  },
  "detectTypes": {
    "2d_bounding_boxes": {
      "description": "2D bounding boxes around objects",
      "maxResults": 25
    }
  }
}
```

### POST `/api/detect`
Main detection endpoint.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `image` | string/file | Yes | Base64 data URL, image URL, or file upload |
| `detectType` | string | Yes | `2d_bounding_boxes`, `3d_bounding_boxes`, `points`, `segmentation_masks` |
| `prompt` | string | No | Custom prompt (uses defaults if not provided) |
| `temperature` | number | No | AI model temperature (0-1, default: 0.5) |
| `maxResults` | number | No | Maximum number of results |
| `outputMode` | string | No | `coordinates_only`, `image_only`, `both` (default: `coordinates_only`) |
| `showCoordinates` | boolean | No | Show coordinate labels on image (default: true) |
| `fov` | number | No | Field of view for 3D boxes (30-120, default: 60) |
| `imageScale` | number | No | Scale factor for output image (0.1-2.0, default: 1.0) |

## Usage Examples

### 1. Basic 2D Bounding Box Detection (JSON)

```bash
curl -X POST http://localhost:3001/api/detect \
  -H "Content-Type: application/json" \
  -d '{
    "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ...",
    "detectType": "2d_bounding_boxes",
    "outputMode": "coordinates_only"
  }'
```

**Response:**
```json
{
  "success": true,
  "detectType": "2d_bounding_boxes",
  "coordinates": [
    {
      "x": 0.1,
      "y": 0.2,
      "width": 0.3,
      "height": 0.4,
      "label": "person"
    }
  ],
  "metadata": {
    "resultCount": 1,
    "timestamp": "2024-01-01T00:00:00.000Z"
  }
}
```

### 2. File Upload with Annotated Image Output

```bash
curl -X POST http://localhost:3001/api/detect \
  -F "imageFile=@image.jpg" \
  -F "detectType=2d_bounding_boxes" \
  -F "outputMode=both" \
  -F "showCoordinates=true"
```

### 3. Point Detection with Custom Prompt

```bash
curl -X POST http://localhost:3001/api/detect \
  -H "Content-Type: application/json" \
  -d '{
    "image": "https://example.com/image.jpg",
    "detectType": "points",
    "prompt": "Find all the cars in this image",
    "maxResults": 5,
    "outputMode": "both"
  }'
```

### 4. 3D Bounding Boxes

```bash
curl -X POST http://localhost:3001/api/detect \
  -H "Content-Type: application/json" \
  -d '{
    "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ...",
    "detectType": "3d_bounding_boxes",
    "fov": 90,
    "maxResults": 10
  }'
```

### 5. JavaScript/Frontend Usage

```javascript
// Using fetch API
async function detectObjects(imageFile) {
  const formData = new FormData();
  formData.append('imageFile', imageFile);
  formData.append('detectType', '2d_bounding_boxes');
  formData.append('outputMode', 'both');
  formData.append('showCoordinates', 'true');

  const response = await fetch('http://localhost:3001/api/detect', {
    method: 'POST',
    body: formData
  });

  const result = await response.json();
  return result;
}

// Using base64 image
async function detectFromBase64(base64Image) {
  const response = await fetch('http://localhost:3001/api/detect', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      image: base64Image,
      detectType: 'points',
      outputMode: 'coordinates_only',
      maxResults: 10
    })
  });

  const result = await response.json();
  return result;
}
```

## Detection Types

### 2D Bounding Boxes (`2d_bounding_boxes`)
Detects rectangular bounding boxes around objects.

**Output format:**
```json
{
  "x": 0.1,        // Left position (0-1, relative to image width)
  "y": 0.2,        // Top position (0-1, relative to image height)
  "width": 0.3,    // Width (0-1, relative to image width)
  "height": 0.4,   // Height (0-1, relative to image height)
  "label": "car"   // Object description
}
```

### 3D Bounding Boxes (`3d_bounding_boxes`)
Detects 3D bounding boxes with position, size, and rotation.

**Output format:**
```json
{
  "center": [1.0, 2.0, 3.0],     // 3D position [x, y, z]
  "size": [1.5, 2.0, 1.0],       // 3D dimensions [width, height, depth]
  "rpy": [0.1, 0.2, 0.3],        // Rotation [roll, pitch, yaw] in radians
  "label": "box"                  // Object description
}
```

### Points (`points`)
Detects specific points or locations of objects.

**Output format:**
```json
{
  "point": {
    "x": 0.5,      // X coordinate (0-1, relative to image width)
    "y": 0.3       // Y coordinate (0-1, relative to image height)
  },
  "label": "door handle"
}
```

### Segmentation Masks (`segmentation_masks`)
Detects objects with segmentation masks and bounding boxes.

**Output format:**
```json
{
  "x": 0.1,
  "y": 0.2,
  "width": 0.3,
  "height": 0.4,
  "label": "person",
  "imageData": "mask_data_string"
}
```

## Output Modes

- **`coordinates_only`**: Returns only the detection coordinates
- **`image_only`**: Returns only the annotated image (base64)
- **`both`**: Returns both coordinates and annotated image

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | - | **Required** Google Gemini API key |
| `PORT` | 3001 | Server port |
| `NODE_ENV` | development | Environment mode |
| `ALLOWED_ORIGINS` | localhost:3000,localhost:5173 | CORS allowed origins (comma-separated) |
| `RATE_LIMIT_WINDOW_MS` | 900000 | Rate limit window (15 minutes) |
| `RATE_LIMIT_MAX_REQUESTS` | 100 | Max requests per window |
| `MAX_IMAGE_SIZE_MB` | 10 | Maximum image size |

### Rate Limiting

The server includes built-in rate limiting:
- **Window**: 15 minutes (configurable)
- **Limit**: 100 requests per IP per window (configurable)
- **Response**: 429 status code when exceeded

## Error Handling

The API returns consistent error responses:

```json
{
  "success": false,
  "error": "Error description",
  "details": "Detailed error message (development mode only)"
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Bad Request (invalid parameters)
- `413`: Payload Too Large (image too big)
- `429`: Rate Limited
- `500`: Internal Server Error

## Development

### Project Structure

```
server/
├── src/
│   ├── index.js          # Main server entry point
│   ├── routes.js         # API route handlers
│   ├── geminiService.js  # Gemini AI service
│   ├── utils.js          # Utility functions
│   └── types.js          # Constants and types
├── package.json
├── env.example
└── README.md
```

### Running in Development

```bash
npm run dev
```

This starts the server with nodemon for auto-reloading on file changes.

### Testing

You can test the API using the provided examples or tools like:
- curl
- Postman
- Insomnia
- Browser fetch API

## Production Deployment

1. **Set environment variables**:
   ```bash
   export GEMINI_API_KEY=your_api_key
   export NODE_ENV=production
   export PORT=3001
   ```

2. **Install dependencies**:
   ```bash
   npm install --production
   ```

3. **Start the server**:
   ```bash
   npm start
   ```

### Docker Deployment (Optional)

Create a `Dockerfile`:

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install --production
COPY src/ ./src/
EXPOSE 3001
CMD ["npm", "start"]
```

Build and run:
```bash
docker build -t spatial-understanding-api .
docker run -p 3001:3001 -e GEMINI_API_KEY=your_key spatial-understanding-api
```

## License

Apache-2.0

## Support

For issues and questions, please check the API documentation at `http://localhost:3001/` when the server is running. 