# Fashion Fitter FastAPI

A FastAPI application that generates professional fashion photos by combining dress images with model images using Google's Gemini AI.

## Features

- **REST API**: Upload dress and model images via HTTP endpoints
- **Custom Prompts**: Customize the image generation with your own prompts
- **Interactive Documentation**: Built-in Swagger UI for API testing

## Setup

### Prerequisites

- Python 3.8+
- Google Gemini API access (requires API key)
- Virtual environment (recommended)

### Installation


1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up Google Gemini API**:
   - Get your API key from Google AI Studio
   - Set it as an environment variable or configure it in your application

### Running the Server

```bash
python server.py
```

The server will start on `http://localhost:8000`

## API Endpoints

### `POST /generate-fashion-photo`

Generate a fashion photo by combining a dress image with a model image.

**Parameters:**
- `url` (string): amazon product URL
- `prompt` (optional string): Custom prompt for image generation

**Response:**
```json
{
  "success": true,
  "image_public_url": "<[S3 URL]>",
  "metadata": {
    "url": "<[orignal product URL]>",
    "title": "...",
    "price": "...",
    "color": "...",
    "size": ".",
    "category": "...",
    "product_about_info": "additionalproductinfo - list format"
  },
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




### Using Python requests
```python
test_url = "https://www.amazon.in/Lymio-Casual-Stylish-Insta-Shirt-Regular/dp/B0DRNHN591/ref=sxin_15_pa_sp_search_thematic_sspa?cv_ct_cx=shirts+for+men+stylish&sbo=RZvfv%2F%2FHxDF%2BO5021pAnSA%3D%3D&sr=1-1-883a54c7-f466-4d42-997c-6d482a360a1a-spons&sp_csd=d2lkZ2V0TmFtZT1zcF9zZWFyY2hfdGhlbWF0aWM&psc=1"
        
        # Prepare the request data
        data = {
            'url': test_url,
            'prompt': 'Create a professional e-commerce fashion photo. Take the Hawaiian shirt from the first image and let the man from the second image wear it. Generate a realistic, full-body shot of the man wearing the shirt with proper lighting.'
        }
        
        print(f"Testing with URL: {test_url}")
        print("Sending request to API...")
        
        start_time = time.time()
        
        # Make the request to the new endpoint
        response = requests.post(
            'http://localhost:8000/generate-photo-and-data',
            data=data,
            timeout=120  # Increased timeout for scraping + AI generation
        )
        
        # Check response
        if response.status_code == 200:
            return response.json()
```

## File Structure

```
├── server.py      # Main FastAPI application
├── requirements.txt      # Python dependencies
└── README.md           # This file
```



## Development

To extend the API:
1. Add new endpoints in `server.py`
2. Update `requirements.txt` for new dependencies
3. Test using the `/docs` endpoint or test client
4. Update this README with new features

## Notes

- The API uses Google's Gemini 2.5 Flash Image Preview model
- Generated images are returned as PNG format in base64 encoding
- File uploads are limited by FastAPI's default settings
- Make sure you have proper authentication for the Gemini API
