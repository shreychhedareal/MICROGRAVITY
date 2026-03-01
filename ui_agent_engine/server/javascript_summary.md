# JavaScript Code Summary: Spatial Understanding API Server

Based on the `server` folder of the UI agent project, this is a Node.js Express server acting as an API backend for image-based spatial understanding and object detection utilizing the Google Gemini API.

The server receives an image (either as a file upload or Base64/URL) and a search prompt, forwards it to Gemini AI for detection (asking it to find 2D bounding boxes, 3D bounding boxes, segmentation masks, or specific points), and then returns both the coordinates and a visually annotated version of the image drawn with the detection results.

Here is a breakdown of the key JavaScript files and what they do:

### 1. `src/index.js` (The Server Entry Point)
This is the main setup file for the Express.js application. 
- **Middleware**: Sets up JSON passing limits (`50mb`), Cross-Origin Resource Sharing (CORS) so your frontend can communicate with it securely, and logs requests.
- **Rate Limiting**: Includes a basic rate limiter using an in-memory `Map` to prevent API abuse (defaulting to 100 requests per 15 minutes).
- **Static files & Routing**: Serves local files from a `public` sub-directory (which acts as a test UI) and mounts all logic to the `/api` route. It handles global unhandled errors and 404s gracefully.

### 2. `src/routes.js` (API endpoints)
This defines your API endpoints, mainly focusing on the core `/api/detect` route.
- **`/health` & `/models`**: Simple checks to ensure the Gemini service is correctly initialized with the API key.
- **`/detect`**: Accepts a multipart form upload (using `multer`) containing the image and the user's prompt (e.g., "detect all cars"). 
- **Processing Flow**:
  1. Validates the request (ensures the file is an image, the detection type is known, etc.).
  2. Submits the image and prompt to the Gemini API via `geminiService`.
  3. Prepares the response. If the user requested an annotated image (`OUTPUT_MODES.IMAGE_ONLY` or `BOTH`), it invokes visual generation scripts to physically draw the boxes/points onto the image before returning it as a Base64 string.

### 3. `src/utils.js` (Image processing and Drawing Tools)
This file handles the heavy processing for formatting and visually annotating the images.
- **Image Processing**: Uses `sharp` to resize and compress uploaded images under optimal boundaries.
- **Formatting**: Takes the raw JSON response returned by the Gemini model and maps it into clean, normalized Javascript objects.
- **Drawing**: Uses `skia-canvas` to literally draw on the images. It has specific functions like `draw2DBoundingBoxes`, `drawPoints`, and `drawSegmentationMasks`. It applies different colors and renders textual labels (like `TL: (0.123, 0.456)`) directly onto the corners of the drawn shapes.

### 4. `src/math3d.js` (3D Projection Logic)
This acts as a dedicated mathematics engine to project 3D wireframe bounding boxes onto a 2D image.
- It computes matrix multiplication, converts Euler angles (roll, pitch, yaw) to Quaternions, and generates rotation matrices.
- **`project3DBoundingBox`**: Given 3D camera intrinsic parameters (like the Field of View width/height), it computes the exact 8 corners of an arbitrary 3D cube and translates them onto flattened 2D Pixel space so they can be accurately drawn on the 2D image.

### 5. `src/types.js` (Types, Prompts, and Constants)
A centralized config file to keep the application modular.
- **Enums & Configurations**: Defines accepted `DETECT_TYPES` (e.g. `2d_bounding_boxes`, `segmentation_masks`), visual constants (`COLORS`, line width), validation constraints, and API status codes.
- **System Prompts**: Contains the exact hardcoded `DEFAULT_PROMPT_PARTS` used to instruct the Gemini models. For instance, the prompt for 2D bounding boxes forces the model to return a structured JSON list with less than 25 items without segmentation masks. 
- **Safety**: Modifies the `HarmBlockThreshold` settings to permissive (`BLOCK_NONE`), as spatial parsing on ordinary images often gets overly flagged by default content filters.

### Summary of Architecture Flow
If a user goes to your app and tries to locate *"all the red cups"* on an image:
1. `index.js` accepts the request.
2. `routes.js` receives the file via the `/detect` endpoint.
3. The prompt is built using templates from `types.js`.
4. The image and text are sent to the AI Model via `GeminiService`.
5. The model's coordinate data is passed directly into `utils.js` (or `math3d.js` if it's 3D).
6. `skia-canvas` draws boxes over the image.
7. The JSON coordinates alongside the newly drawn image are successfully returned to the user.
