# Fashion Fitter FastAPI

A FastAPI application that generates professional fashion photos by combining dress images with model images using Google's Gemini AI.

## Features

- **REST API**: Upload dress and model images via HTTP endpoints
- **Base64 Output**: Returns generated images as base64-encoded strings
- **Custom Prompts**: Customize the image generation with your own prompts
- **Interactive Documentation**: Built-in Swagger UI for API testing
- **Test Client**: Simple HTML interface for easy testing

## Setup

### Prerequisites

- Python 3.8+
- Google Gemini API access (requires API key)
- Virtual environment (recommended)

### Installation

1. **Activate your virtual environment** (if using one):
   ```bash
   source hacksun/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Google Gemini API**:
   - Get your API key from Google AI Studio
   - Set it as an environment variable or configure it in your application

### Running the Server

**Option 1: Use the startup script**
```bash
./run_server.sh
```

**Option 2: Run directly**
```bash
python fastapi_fitter.py
```

The server will start on `http://localhost:8000`

## API Endpoints

### `POST /generate-fashion-photo`

Generate a fashion photo by combining a dress image with a model image.

**Parameters:**
- `dress_image` (file): Image of the dress on a plain background
- `model_image` (file): Image of the model
- `prompt` (optional string): Custom prompt for image generation

**Response:**
```json
{
  "success": true,
  "message": "Fashion photo generated successfully",
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
  "image_format": "PNG"
}
```

### `GET /`
Health check endpoint

### `GET /health`
Detailed health check

### `GET /docs`
Interactive API documentation (Swagger UI)

### `GET /test`
Test client HTML interface

## Usage Examples

### Using curl
```bash
curl -X POST "http://localhost:8000/generate-fashion-photo" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "dress_image=@dress.jpg" \
     -F "model_image=@model.jpg" \
     -F "prompt=Create a professional fashion photo..."
```

### Using the Test Client
1. Navigate to `http://localhost:8000/test`
2. Upload your dress and model images
3. Optionally customize the prompt
4. Click "Generate Fashion Photo"
5. View the generated image

### Using Python requests
```python
import requests
import base64
from PIL import Image
from io import BytesIO

# Prepare files
with open('dress.jpg', 'rb') as dress_file, open('model.jpg', 'rb') as model_file:
    files = {
        'dress_image': dress_file,
        'model_image': model_file
    }
    data = {
        'prompt': 'Create a professional e-commerce fashion photo...'
    }
    
    response = requests.post('http://localhost:8000/generate-fashion-photo', 
                           files=files, data=data)

if response.status_code == 200:
    result = response.json()
    if result['success']:
        # Decode base64 image
        image_data = base64.b64decode(result['image_base64'])
        image = Image.open(BytesIO(image_data))
        image.save('generated_fashion_photo.png')
        print("Image saved as generated_fashion_photo.png")
```

## File Structure

```
├── fastapi_fitter.py      # Main FastAPI application
├── fitter.py             # Original script (reference)
├── requirements.txt      # Python dependencies
├── run_server.sh        # Startup script
├── test_client.html     # HTML test interface
└── README.md           # This file
```

## Error Handling

The API includes comprehensive error handling:
- File type validation
- Image processing errors
- API generation failures
- Proper HTTP status codes and error messages

## Development

To extend the API:
1. Add new endpoints in `fastapi_fitter.py`
2. Update `requirements.txt` for new dependencies
3. Test using the `/docs` endpoint or test client
4. Update this README with new features

## Notes

- The API uses Google's Gemini 2.5 Flash Image Preview model
- Generated images are returned as PNG format in base64 encoding
- File uploads are limited by FastAPI's default settings
- Make sure you have proper authentication for the Gemini API