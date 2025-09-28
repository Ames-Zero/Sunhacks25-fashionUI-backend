# Fashion Fitter FastAPI

A FastAPI application that generates professional fashion photos by combining dress images with model images using Google's Gemini AI.

## Features

- **AI Fashion Photo Generation**: Generate professional fashion photos using Google's Gemini AI
- **AI Outfit Suggestions**: Get personalized styling advice from your closet using natural language queries
- **Amazon Product Scraping**: Automatically scrape product data and images from Amazon URLs
- **Natural Language Search**: Search through 3000+ products using queries like "blue shirts" or "red t-shirts"
- **Personal Closet Management**: Save generated photos and products to personal closet collections
- **Professional Styling**: AI-powered outfit recommendations for any occasion
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


1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables**:
   ```bash
   export GOOGLE_API_KEY="your_google_gemini_api_key"
   export MONGO_PASSWORD="your_mongodb_password"
   export S3_BUCKET="your-s3-bucket-name"
   export IMAGE_GENERATION_MODEL="gemini-2.5-flash-image-preview"
   ```

3. **Configure services**:
   - **Google Gemini API**: Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - **MongoDB**: Set up MongoDB Atlas cluster and get connection credentials
   - **AWS S3**: Create S3 bucket and configure AWS credentials

### Running the Server

```bash
python server.py
```

The server will start on `http://localhost:8000`

## API Endpoints

### Health Check Endpoints

#### `GET /`
Basic health check endpoint.

**Curl Command:**
```bash
curl http://localhost:8000/
```

**Response:**
```json
{
  "message": "Fashion Fitter API is running",
  "status": "healthy"
}
```

#### `GET /health`
Detailed health check endpoint.

**Curl Command:**
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "Fashion Fitter API",
  "version": "1.0.0"
}
```

---

### Product Search

#### `POST /search-products`
Search products using natural language queries from the MongoDB products collection (3000+ products).

**Parameters:**
- `query` (string, required): Natural language search query

**Curl Commands:**
```bash
# Search for blue shirts
curl -X POST "http://localhost:8000/search-products" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "query=blue shirts"

# Search for red dresses
curl -X POST "http://localhost:8000/search-products" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "query=red dresses"

# Search for casual wear
curl -X POST "http://localhost:8000/search-products" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "query=casual wear"
```

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

---

### Closet Management

#### `POST /add-to-closet`
Add a product from the products collection to your personal closet using the product ID.

**Parameters:**
- `product_id` (string, required): MongoDB _id of the product from products collection

**Curl Command:**
```bash
# Replace PRODUCT_ID with actual ID from search results
curl -X POST "http://localhost:8000/add-to-closet" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "product_id=REPLACE_WITH_ACTUAL_PRODUCT_ID"
```

**Response:**
```json
{
  "success": true,
  "message": "Product successfully added to closet",
  "mongodb_id": "mongodb_object_id_in_closet",
  "product_id": "60f7b5a8c9e7b4a2d5f8g9h0"
}
```

#### `GET /closet-items`
Get all items from your personal closet collection.

**Parameters:**
- `limit` (int, optional): Limit the number of results returned

**Curl Commands:**
```bash
# Get all closet items
curl "http://localhost:8000/closet-items"

# Get limited closet items (5 items)
curl "http://localhost:8000/closet-items?limit=5"

# Get limited closet items (10 items)
curl "http://localhost:8000/closet-items?limit=10"
```

**Response:**
```json
{
  "success": true,
  "total_items": 15,
  "limit_applied": 5,
  "closet_items": [
    {
      "id": "closet_item_mongodb_id",
      "product_name": "Blue Cotton Shirt",
      "brand": "Brand Name",
      "category": "men's clothing",
      "subcategory": "Shirts",
      "colors": {
        "primary": "Blue"
      },
      "price": 29.99,
      "image_url": "https://...",
      "product_url": "https://..."
    }
  ]
}
```

#### `DELETE /closet-items`
Clear all items from your closet collection.

**Curl Command:**
```bash
curl -X DELETE "http://localhost:8000/closet-items"
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully cleared closets collection",
  "deleted_count": 15,
  "initial_count": 15,
  "final_count": 0
}
```

---

### AI Outfit Suggestions

#### `POST /outfit-suggestions`
Get AI-powered outfit suggestions based on your closet items and natural language queries about occasions.

**Parameters:**
- `query` (string, required): Natural language query describing the occasion or outfit preference

**Curl Commands:**
```bash
# Business meeting outfit
curl -X POST "http://localhost:8000/outfit-suggestions" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "query=business meeting"

# Casual date night outfit
curl -X POST "http://localhost:8000/outfit-suggestions" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "query=casual date night"

# Weekend brunch outfit
curl -X POST "http://localhost:8000/outfit-suggestions" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "query=weekend brunch"

# Summer party outfit
curl -X POST "http://localhost:8000/outfit-suggestions" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "query=summer party outfit"

# Office formal outfit
curl -X POST "http://localhost:8000/outfit-suggestions" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "query=office formal wear"
```

**Successful Response:**
```json
{
  "success": true,
  "query": "business meeting",
  "total_closet_items": 15,
  "message": "Outfit suggestions generated successfully",
  "outfit_suggestion": "For a business meeting, pair the navy blazer with white shirt and dark jeans. The classic combination projects confidence while remaining approachable.",
  "suggested_items": [
    {
      "id": "closet_item_id_1",
      "product_name": "Navy Blue Blazer",
      "brand": "Calvin Klein",
      "category": "Clothing",
      "subcategory": "Jackets & Coats",
      "colors": {
        "primary": "navy blue"
      },
      "price": "149.99",
      "image_url": "https://...",
      "product_url": "https://..."
    },
    {
      "id": "closet_item_id_2",
      "product_name": "White Cotton Dress Shirt",
      "brand": "Brooks Brothers",
      "category": "Clothing",
      "subcategory": "Shirts",
      "colors": {
        "primary": "white"
      },
      "price": "79.99",
      "image_url": "https://...",
      "product_url": "https://..."
    }
  ],
  "suggested_items_count": 2
}
```

**Empty Closet Response (404):**
```json
{
  "success": false,
  "query": "business meeting",
  "message": "No items found in closet collection",
  "outfit_suggestion": "I'd love to help you style an outfit, but it looks like your closet is empty! Start by adding some items to your closet collection, and I'll be able to suggest amazing outfits for any occasion.",
  "suggested_items": [],
  "total_closet_items": 0,
  "suggested_items_count": 0
}
```

**Example Queries:**
- "job interview at a tech company"
- "casual date night"
- "weekend brunch with friends"
- "formal dinner party"
- "business presentation"

---

### AI Fashion Photo Generation

#### `POST /generate-photo-and-data`
Generate a professional fashion photo by combining a dress image with a model image using Google's Gemini AI.

**Parameters:**
- `url` (string, required): Amazon product URL to scrape
- `prompt` (optional string): Custom prompt for image generation

**Curl Command:**
```bash
curl -X POST "http://localhost:8000/generate-photo-and-data" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "url=https://www.amazon.com/WRITKC-Hawaiian-Shirts-Sleeve-Resort/dp/B0CPFVNH35" \
  -d "prompt=Create a professional e-commerce fashion photo. Take the shirt from the first image and let the person from the second image wear it."
```

**Response:**
```json
{
  "success": true,
  "image_public_url": "https://your-s3-bucket.s3.amazonaws.com/generated_images/uuid.png",
  "metadata": {
    "url": "https://amazon.com/product/url",
    "title": "Hawaiian Resort Shirt",
    "price": "29.99",
    "color": "Blue",
    "size": "Medium",
    "category": "Shirts",
    "product_about_info": ["100% Cotton", "Machine Washable", "Relaxed Fit"]
  },
  "image_format": "PNG"
}
```

---

### Error Testing

Test error handling with these commands:

```bash
# Test empty search query (should return 400 error)
curl -X POST "http://localhost:8000/search-products" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "query="

# Test empty outfit query (should return 400 error)
curl -X POST "http://localhost:8000/outfit-suggestions" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "query="

# Test invalid product ID (should return 404 error)
curl -X POST "http://localhost:8000/add-to-closet" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "product_id=invalid_id_123"
```

---

### Interactive Documentation

#### `GET /docs`
Access the interactive Swagger UI documentation at `http://localhost:8000/docs` for testing all endpoints with a web interface.




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

### Add Product to Personal Closet
```python
import requests

# Add product to closet using product ID
data = {
    "product_id": "60f7b5a8c9e7b4a2d5f8g9h0"  # Get this from search results
}

response = requests.post('http://localhost:8000/add-to-closet', data=data)
if response.status_code == 200:
    result = response.json()
    print(f"Added to closet with ID: {result['mongodb_id']}")
```

### Get AI Outfit Suggestions
```python
import requests

# Get outfit suggestions for a specific occasion
outfit_data = {
    "query": "job interview at a tech startup"
}

response = requests.post('http://localhost:8000/outfit-suggestions', data=outfit_data)
if response.status_code == 200:
    result = response.json()
    print(f"AI Stylist found {result['total_closet_items']} items in your closet")
    print("\nStylist Suggestions:")
    print(result['stylist_suggestions'])
elif response.status_code == 404:
    result = response.json()
    print("Closet is empty. Add some items first!")
    print(result['stylist_suggestions'])  # Encouraging message
```

## File Structure

```
├── server.py               # Main FastAPI application
├── mongo_search.py        # MongoDB operations and AI outfit suggestions
├── test_outfit.py         # Simple test for outfit suggestions
├── requirements.txt       # Python dependencies
├── model_photo.jpg        # Model photo for outfit generation
└── README.md             # This file
```



## Testing

### Quick Start Testing Workflow

1. **Start the server:**
   ```bash
   python server.py
   ```

2. **Test in recommended order:**
   ```bash
   # 1. Health checks
   curl http://localhost:8000/
   curl http://localhost:8000/health
   
   # 2. Search for products (copy a product ID from results)
   curl -X POST "http://localhost:8000/search-products" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "query=blue shirts"
   
   # 3. Add product to closet (use real product ID from step 2)
   curl -X POST "http://localhost:8000/add-to-closet" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "product_id=REPLACE_WITH_ACTUAL_PRODUCT_ID"
   
   # 4. View closet items
   curl "http://localhost:8000/closet-items?limit=5"
   
   # 5. Get outfit suggestions
   curl -X POST "http://localhost:8000/outfit-suggestions" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "query=casual date night"
   
   # 6. Clear closet when done
   curl -X DELETE "http://localhost:8000/closet-items"
   ```

### Automated Testing Script

You can also run the automated test script:
```bash
# Make executable and run
chmod +x run_api_tests.sh
./run_api_tests.sh
```

This will:
- Test all endpoints automatically
- Log results to a timestamped file
- Use real product IDs from search results
- Show both successes and errors

### Pretty JSON Output

For better readable JSON responses, install and use `jq`:
```bash
# Install jq (if not already installed)
sudo apt-get install jq  # Ubuntu/Linux
brew install jq          # macOS

# Use jq for pretty printing
curl "http://localhost:8000/closet-items" | jq
curl "http://localhost:8000/health" | jq
```

### Test Different Scenarios

**Search Variations:**
```bash
curl -X POST "http://localhost:8000/search-products" -H "Content-Type: application/x-www-form-urlencoded" -d "query=red dresses"
curl -X POST "http://localhost:8000/search-products" -H "Content-Type: application/x-www-form-urlencoded" -d "query=casual jeans"
curl -X POST "http://localhost:8000/search-products" -H "Content-Type: application/x-www-form-urlencoded" -d "query=formal shirts"
```

**Outfit Suggestions for Different Occasions:**
```bash
curl -X POST "http://localhost:8000/outfit-suggestions" -H "Content-Type: application/x-www-form-urlencoded" -d "query=job interview"
curl -X POST "http://localhost:8000/outfit-suggestions" -H "Content-Type: application/x-www-form-urlencoded" -d "query=weekend party"
curl -X POST "http://localhost:8000/outfit-suggestions" -H "Content-Type: application/x-www-form-urlencoded" -d "query=business presentation"
```

### Error Scenarios Testing

Test error handling:
```bash
# Empty queries
curl -X POST "http://localhost:8000/search-products" -H "Content-Type: application/x-www-form-urlencoded" -d "query="
curl -X POST "http://localhost:8000/outfit-suggestions" -H "Content-Type: application/x-www-form-urlencoded" -d "query="

# Invalid product ID
curl -X POST "http://localhost:8000/add-to-closet" -H "Content-Type: application/x-www-form-urlencoded" -d "product_id=invalid123"

# Outfit suggestions with empty closet
curl -X DELETE "http://localhost:8000/closet-items"  # Clear closet first
curl -X POST "http://localhost:8000/outfit-suggestions" -H "Content-Type: application/x-www-form-urlencoded" -d "query=date night"
```

### Interactive Testing
Visit `http://localhost:8000/docs` for Swagger UI interactive testing with a web interface.

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
