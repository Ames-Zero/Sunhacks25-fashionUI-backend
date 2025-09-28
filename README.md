# Fashion Fitter FastAPI

A FastAPI application that generates professional fashion photos by combining dress images with model images using Google's Gemini AI.

## Features

- **AI Fashion Photo Generation**: Generate professional fashion photos using Google's Gemini AI
- **Amazon Product Scraping**: Automatically scrape product data and images from Amazon URLs
- **Natural Language Search**: Search through 3000+ products using queries like "blue shirts" or "red t-shirts"
- **Personal Closet Management**: Save generated photos and products to personal closet collections
- **MongoDB Integration**: Persistent storage for products and user closets
- **S3 Cloud Storage**: Generated images stored in AWS S3 with public URLs
- **REST API**: Complete RESTful API with multiple endpoints
- **Interactive Documentation**: Built-in Swagger UI for API testing

## Setup

### Prerequisites

- Python 3.8+
- Google Gemini API access (requires API key)
- MongoDB Atlas account (for products and closets data)
- AWS S3 bucket (for image storage)
- Virtual environment (recommended)

### Installation

1. **Activate virtual environment**:
   ```bash
   source hacksun/bin/activate  # or your virtual environment
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   export GOOGLE_API_KEY="your_google_gemini_api_key"
   export MONGO_PASSWORD="your_mongodb_password"
   export S3_BUCKET="your-s3-bucket-name"
   export IMAGE_GENERATION_MODEL="gemini-2.5-flash-image-preview"
   ```

4. **Configure services**:
   - **Google Gemini API**: Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - **MongoDB**: Set up MongoDB Atlas cluster and get connection credentials
   - **AWS S3**: Create S3 bucket and configure AWS credentials

### Running the Server

```bash
python server.py
```

The server will start on `http://localhost:8000`

## API Endpoints

### `POST /generate-photo-and-data`

Generate a fashion photo by combining a dress image with a model image using AI.

**Parameters:**
- `url` (string): Amazon product URL to scrape
- `prompt` (optional string): Custom prompt for image generation

**Response:**
```json
{
  "success": true,
  "image_public_url": "<S3 URL>",
  "metadata": {
    "url": "<original product URL>",
    "title": "...",
    "price": "...",
    "color": "...",
    "size": "...",
    "category": "...",
    "product_about_info": ["additional", "product", "info"]
  },
  "image_format": "PNG"
}
```

### `POST /search-products`

Search products using natural language queries from the MongoDB products collection.

**Parameters:**
- `query` (string): Natural language search query (e.g., "blue shirts", "red t-shirts")

**Response:**
```json
{
  "success": true,
  "query": "blue shirts",
  "total_results": 5,
  "products": [
    {
      "id": "product_mongodb_id",
      "product_name": "Brand Blue Cotton Shirt",
      "brand": "Brand Name",
      "category": "men's clothing",
      "subcategory": "Shirts",
      "colors": {
        "primary": "Blue",
        "secondary": "White"
      },
      "price": 29.99,
      "rating": 4.2,
      "image_url": "https://...",
      "product_url": "https://...",
      "attributes": {
        "material": "cotton",
        "fit_type": "regular",
        "pattern_type": "solid"
      }
    }
  ]
}
```

### `POST /add-to-closet`

Add an item to the user's closet collection in MongoDB.

**Parameters:**
- `closet_item` (JSON object): Item data to add to closet

**Request Body Example:**
```json
{
  "type": "generated_photo",
  "product_name": "AI Generated Blue Shirt",
  "brand": "AI Fashion",
  "category": "men's clothing",
  "subcategory": "Shirts",
  "colors": {
    "primary": "Blue",
    "secondary": "White"
  },
  "metadata": {
    "price": 35.99,
    "generated_at": "2025-09-27T10:30:00Z"
  },
  "closet_metadata": {
    "user_id": "user123",
    "notes": "My favorite generated shirt"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Item successfully added to closet",
  "closet_item_id": "uuid-generated-id",
  "mongodb_id": "mongodb_object_id",
  "item_type": "generated_photo"
}
```

### `GET /`
Health check endpoint

### `GET /health`
Detailed health check

### `GET /docs`
Interactive API documentation (Swagger UI)




## Usage Examples

### Generate Fashion Photo from Amazon URL
```python
import requests

test_url = "https://www.amazon.com/WRITKC-Hawaiian-Shirts-Sleeve-Resort/dp/B0CPFVNH35"
        
# Generate fashion photo
data = {
    'url': test_url,
    'prompt': 'Create a professional e-commerce fashion photo. Take the shirt from the first image and let the person from the second image wear it.'
}

response = requests.post('http://localhost:8000/generate-photo-and-data', data=data)
if response.status_code == 200:
    result = response.json()
    print(f"Generated image URL: {result['image_public_url']}")
```

### Search Products with Natural Language
```python
import requests

# Search for products
search_data = {"query": "blue shirts"}
response = requests.post('http://localhost:8000/search-products', data=search_data)

if response.status_code == 200:
    result = response.json()
    print(f"Found {result['total_results']} products")
    for product in result['products']:
        print(f"- {product['product_name']} - ${product['price']}")
```

### Add Item to Personal Closet
```python
import requests

# Add generated photo to closet
closet_item = {
    "type": "generated_photo",
    "product_name": "AI Generated Blue Shirt",
    "brand": "AI Fashion",
    "colors": {"primary": "Blue", "secondary": "White"},
    "metadata": {"price": 35.99},
    "closet_metadata": {
        "user_id": "user123",
        "notes": "Love this generated look!"
    }
}

response = requests.post('http://localhost:8000/add-to-closet', json=closet_item)
if response.status_code == 200:
    result = response.json()
    print(f"Added to closet with ID: {result['mongodb_id']}")
```

## File Structure

```
├── server.py               # Main FastAPI application
├── test_endpoints.py       # API endpoint tests
├── requirements.txt       # Python dependencies
└── README.md             # This file
```



## Testing

### Test All Endpoints
```bash
# Start the server
python server.py

# In another terminal, run endpoint tests
python test_endpoints.py
```

### Test MongoDB Functions
```bash
# Test natural language search and closet functionality
python test_mongo.py
```

### Interactive Testing
Visit `http://localhost:8000/docs` for Swagger UI interactive testing.

## Development

To extend the API:
1. Add new endpoints in `server.py`
2. Add MongoDB functions in `mongo_search.py`
3. Update `requirements.txt` for new dependencies
4. Test using the test scripts or `/docs` endpoint
5. Update this README with new features

## Notes

- The API uses Google's Gemini 2.5 Flash Image Preview model
- Generated images are returned as PNG format in base64 encoding
- File uploads are limited by FastAPI's default settings
- Make sure you have proper authentication for the Gemini API
