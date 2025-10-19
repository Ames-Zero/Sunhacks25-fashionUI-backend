from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from pydantic import BaseModel
from mongo_search import query_products, add_to_closet, add_product_to_closet, get_all_closet_items, clear_closets_collection, get_outfit_suggestions_with_llm
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import re
import os
import uvicorn
import requests
import time
import random
import boto3
import uuid
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fashion_api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Pydantic models for JSON request validation
class SearchProductsRequest(BaseModel):
    query: str

class AddToClosetRequest(BaseModel):
    product_id: str

class OutfitSuggestionsRequest(BaseModel):
    query: str

class PhotoGenerationRequest(BaseModel):
    url: str
    prompt: Optional[str] = """IMPORTANT: Keep the person from the second image EXACTLY the same - same face, same body, same pose, same everything. Only change the clothing to match the item from the first image. Preserve the person's identity, appearance, and background. Create a professional fashion photo with the same lighting and style."""

MODEL_IMAGE_PATH = "new_m_p.jpg"  # Replace with your model image path
IMAGE_GENERATION_MODEL = os.getenv('IMAGE_GENERATION_MODEL')  # Replace with your desired model
S3_BUCKET_NAME = os.getenv('S3_BUCKET')

logger.info("Initializing Fashion Fitter API...")
logger.info(f"IMAGE_GENERATION_MODEL: {IMAGE_GENERATION_MODEL}")
logger.info(f"S3_BUCKET_NAME: {S3_BUCKET_NAME}")

app = FastAPI(title="Fashion Fitter API", description="API to generate fashion photos by combining dress and model images")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your extension's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Initialize Google Gemini client with API key
api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    logger.error("GOOGLE_API_KEY environment variable is missing!")
    raise ValueError("GOOGLE_API_KEY environment variable is required. Please set your Google AI Studio API key.")

logger.info("Initializing Google Gemini client...")
client = genai.Client(api_key=api_key)
logger.info("Google Gemini client initialized successfully")

# Clear closets collection on startup
logger.info("🚀 Starting Fashion Fitter API...")
logger.info("Clearing closets collection on startup...")
clear_result = clear_closets_collection()
if clear_result["success"]:
    logger.info(f"✅ Startup: {clear_result['message']} ({clear_result['deleted_count']} items removed)")
else:
    logger.warning(f"⚠️ Startup warning: {clear_result['message']}")

def scrape_amazon_product(url):
    """
    Scrapes Amazon product details including title, size, category, color, price, images, and URL
    """
    logger.info(f"Starting Amazon product scraping for URL: {url}")

    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')  # Updated headless mode
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-software-rasterizer')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36')

    # Try to use system Chrome/Chromium or env override
    chrome_bin = os.getenv('CHROME_BIN', '/usr/bin/google-chrome')
    chrome_options.binary_location = chrome_bin  # e.g. '/usr/bin/google-chrome' or '/usr/bin/chromium-browser'

    # Initialize the driver
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    except Exception as e:
        logger.warning(f"Failed to initialize Chrome driver with {chrome_bin}: {e}")
        logger.info("Trying alternative approach with chromium-browser...")
        chrome_options.binary_location = '/usr/bin/chromium-browser'
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        # Load the page
        driver.get(url)
        time.sleep(3)  # Wait for page to load

        # Get page source and parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Initialize product data dictionary
        product_data = {
            'product_url': url,
            'title': None,
            'price': None,
            'category': None,
            'color': None,
            'size': None,
            'image_urls': []
        }

        # Extract Title
        try:
            title_element = soup.find('span', {'id': 'productTitle'})
            if title_element:
                product_data['title'] = title_element.get_text().strip()
        except Exception as e:
            logger.debug(f"Error extracting title: {e}")

        # Extract Price
        try:
            # Try different price selectors
            price_whole = soup.find('span', {'class': 'a-price-whole'})
            price_fraction = soup.find('span', {'class': 'a-price-fraction'})

            if price_whole and price_fraction:
                product_data['price'] = f"${price_whole.get_text().strip()}{price_fraction.get_text().strip()}"
            else:
                # Alternative price selector
                price_element = soup.find('span', {'class': 'a-offscreen'})
                if price_element:
                    product_data['price'] = price_element.get_text().strip()
        except Exception as e:
            logger.debug(f"Error extracting price: {e}")

        # Extract Category (from breadcrumbs)
        try:
            breadcrumb = soup.find('div', {'id': 'wayfinding-breadcrumbs_feature_div'})
            if breadcrumb:
                categories = breadcrumb.find_all('a', {'class': 'a-link-normal'})
                product_data['category'] = ' > '.join([cat.get_text().strip() for cat in categories])
        except Exception as e:
            logger.debug(f"Error extracting category: {e}")

        # Extract Color
        try:
            # Look for color in product details
            color_element = soup.find('span', string=lambda text: text and 'Color' in text)
            if color_element:
                color_value = color_element.find_next('span')
                if color_value:
                    product_data['color'] = color_value.get_text().strip()

            # Alternative: Look in variation section
            if not product_data['color']:
                color_name = soup.find('span', {'class': 'selection'})
                if color_name and 'Color' in color_name.get_text():
                    product_data['color'] = color_name.get_text().replace('Color name:', '').strip()
        except Exception as e:
            logger.debug(f"Error extracting color: {e}")

        # Extract Size
        try:
            # Look for size in product details
            size_element = soup.find('span', string=lambda text: text and 'Size' in text)
            if size_element:
                size_value = size_element.find_next('span')
                if size_value:
                    product_data['size'] = size_value.get_text().strip()

            # Alternative: Look in variation section
            if not product_data['size']:
                size_name = soup.find('span', {'class': 'selection'})
                if size_name and 'Size' in size_name.get_text():
                    product_data['size'] = size_name.get_text().replace('Size name:', '').strip()
        except Exception as e:
            logger.debug(f"Error extracting size: {e}")

        # Extract Image URLs
        try:
            # Main product image
            main_image = soup.find('img', {'id': 'landingImage'})
            if main_image and main_image.get('src'):
                product_data['image_urls'].append(main_image['src'])

            # Alternative images from image block
            image_block = soup.find('div', {'id': 'altImages'})
            if image_block:
                images = image_block.find_all('img')
                for img in images:
                    if img.get('src') and img['src'] not in product_data['image_urls']:
                        # Get high-res version if possible
                        img_url = img['src'].replace('_SS40_', '_SL1500_')
                        product_data['image_urls'].append(img_url)

            # Remove duplicates while preserving order
            product_data['image_urls'] = list(dict.fromkeys(product_data['image_urls']))
        except Exception as e:
            logger.debug(f"Error extracting images: {e}")

        logger.info(f"Successfully scraped product: {(product_data.get('title') or 'N/A')[:50]}...")
        logger.debug(f"Product data: {product_data}")

        return product_data

    except Exception as e:
        logger.error(f"Error scraping product: {e}")
        return None
    finally:
        try:
            driver.quit()
        except Exception:
            pass

@app.post("/generate-photo-and-data")
async def generate_photo_and_data(request: PhotoGenerationRequest):
    """
    Generate a fashion photo by combining a dress image with a model image.
    Returns the generated image as base64 encoded string.
    """
    url = request.url
    prompt = request.prompt
    logger.info(f"Starting photo generation request for URL: {url}")
    logger.debug(f"Custom prompt provided: {prompt[:100]}...")

    scraped = scrape_amazon_product(url)
    if not scraped:
        logger.error("Failed to scrape product data")
        raise HTTPException(status_code=400, detail="Failed to scrape product data from the provided URL")

    page_metadata = {
        'url': scraped.get('product_url'),
        'title': scraped.get('title'),
        'price': scraped.get('price'),
        'color': scraped.get('color'),
        'size': scraped.get('size'),
        'category': scraped.get('category'),
    }

    image_urls = scraped.get('image_urls', [])
    if image_urls:
        dress_image_url = image_urls[0]
        logger.info(f"Selected dress image URL: {dress_image_url}")
    else:
        logger.error("No product images found from the provided URL")
        raise HTTPException(status_code=400, detail="No product images found from the provided URL")

    # Download the dress image from the URL
    try:
        logger.info("Downloading dress image from URL...")
        dress_response = requests.get(dress_image_url)
        dress_response.raise_for_status()
        dress_pil = Image.open(BytesIO(dress_response.content))
        logger.info(f"Successfully downloaded dress image - Size: {dress_pil.size}")
    except Exception as e:
        logger.error(f"Failed to download dress image: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to download dress image: {str(e)}")

    # Load the local model image
    try:
        logger.info(f"Loading model image from: {MODEL_IMAGE_PATH}")
        with open(MODEL_IMAGE_PATH, 'rb') as model_file:
            model_bytes = model_file.read()
        model_pil = Image.open(BytesIO(model_bytes))
        logger.info(f"Successfully loaded model image - Size: {model_pil.size}")
    except Exception as e:
        logger.error(f"Failed to load model image: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to load model image: {str(e)}")

    try:
        logger.info("Starting image generation with Google Gemini...")
        logger.debug(f"Using model: {IMAGE_GENERATION_MODEL}")

        response = client.models.generate_content(
            model=IMAGE_GENERATION_MODEL,
            contents=[dress_pil, model_pil, prompt],
        )

        image_parts = [
            part.inline_data.data
            for part in response.candidates[0].content.parts
            if part.inline_data
        ]

        if not image_parts:
            logger.error("No image generated from the model")
            raise HTTPException(status_code=500, detail="No image generated from the model")

        logger.info("Successfully generated image from Gemini")
        generated_image = Image.open(BytesIO(image_parts[0]))
        logger.info(f"Generated image size: {generated_image.size}")

        # Convert PIL image to buffer for S3 upload
        buffer = BytesIO()
        generated_image.save(buffer, format='PNG')
        logger.debug("Image converted to PNG buffer")

        # Upload image to S3 and make it publicly accessible
        logger.info("Uploading image to S3...")
        s3_client = boto3.client("s3")
        bucket_name = S3_BUCKET_NAME
        s3_key = f"generated_images/{uuid.uuid4()}.png"
        logger.debug(f"S3 upload - Bucket: {bucket_name}, Key: {s3_key}")

        buffer.seek(0)
        s3_client.upload_fileobj(buffer, bucket_name, s3_key, ExtraArgs={'ContentType': 'image/png'})
        image_url = s3_client.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': s3_key}, ExpiresIn=3600)  # 1 hour expiry
        logger.info(f"Successfully uploaded image to S3: {s3_key}")

        logger.info("Photo generation completed successfully")
        return JSONResponse(content={
            "success": True,
            "image_public_url": image_url,
            "metadata": page_metadata,
            "image_format": "PNG"
        })

    except Exception as e:
        logger.error(f"Error generating fashion photo: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating fashion photo: {str(e)}")

@app.post("/search-products")
async def search_products_endpoint(request: SearchProductsRequest):
    """
    Search products using natural language query

    Args:
        request: JSON request containing query string

    Returns:
        JSON response with matching products (max 10)
    """
    query = request.query
    logger.info(f"Product search request received - Query: '{query}'")
    try:
        if not query or not query.strip():
            logger.warning("Empty or invalid query provided")
            raise HTTPException(status_code=400, detail="Query parameter is required and cannot be empty")

        # Call the MongoDB query function
        logger.info(f"Searching products in MongoDB for query: '{query.strip()}'")
        results = query_products(query.strip())
        logger.info(f"Found {len(results)} products matching the query")

        # Format the response
        formatted_results = []
        for product in results:
            # Handle new schema with direct fields
            formatted_product = {
                "id": str(product.get("_id", "")),
                "product_title": product.get("product_title", "N/A"),
                "product_name": product.get("product_title", "N/A"),  # Alias for compatibility
                "product_url": product.get("product_url", ""),
                "product_price": product.get("product_price", "N/A"),
                "product_color": product.get("product_color", "N/A"),
                "product_size": product.get("product_size", "N/A"),
                "product_category": product.get("product_category", "N/A"),
                "image_url": product.get("image_url", ""),
                # Legacy compatibility fields
                "price": product.get("product_price", "N/A"),
                "category": product.get("product_category", "N/A")
            }
            formatted_results.append(formatted_product)

        logger.info(f"Successfully formatted {len(formatted_results)} products for response")
        return JSONResponse(content={
            "success": True,
            "query": query,
            "total_results": len(results),
            "products": formatted_results
        })

    except Exception as e:
        logger.error(f"Error searching products: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error searching products: {str(e)}")

@app.post("/add-to-closet")
async def add_to_closet_endpoint(request: AddToClosetRequest):
    """
    Add a product to the closet collection using product ID
    
    Args:
        request: JSON request containing product_id
        
    Returns:
        JSON response with insertion confirmation
    """
    try:
        product_id = request.product_id
        if not product_id or not product_id.strip():
            raise HTTPException(status_code=400, detail="Product ID is required")
        
        # Call the simplified MongoDB add function
        result_id = add_product_to_closet(product_id.strip())
        
        if result_id:
            return JSONResponse(content={
                "success": True,
                "message": "Product successfully added to closet",
                "mongodb_id": result_id,
                "product_id": product_id
            })
        else:
            raise HTTPException(status_code=404, detail="Product not found or failed to add to closet")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding product to closet: {str(e)}")

@app.get("/closet-items")
async def get_closet_items_endpoint(
    limit: Optional[int] = None
):
    """
    Get all items from the closets collection

    Args:
        limit (int, optional): Limit the number of results returned

    Returns:
        JSON response with closet items
    """
    try:
        # Call the MongoDB function to get closet items
        closet_items = get_all_closet_items(limit=limit)

        # Format the response with only essential data
        formatted_items = []
        for item in closet_items:
            formatted_item = {
                "id": str(item.get("_id", "")),
                "product_title": item.get("product_title") or item.get("product_name") or item.get("title", "N/A"),
                "product_name": item.get("product_title") or item.get("product_name") or item.get("title", "N/A"),
                "product_price": item.get("product_price") or item.get("metadata", {}).get("price", "N/A"),
                "product_color": item.get("product_color") or item.get("colors", {}).get("primary", "N/A"),
                "product_category": item.get("product_category") or item.get("category", "N/A"),
                "product_size": item.get("product_size", "N/A"),
                "image_url": item.get("image_url", ""),
                "product_url": item.get("product_url", ""),
                # Legacy fields for compatibility
                "price": item.get("product_price") or item.get("metadata", {}).get("price", "N/A")
            }
            formatted_items.append(formatted_item)

        return JSONResponse(content={
            "success": True,
            "total_items": len(closet_items),
            "limit_applied": limit,
            "closet_items": formatted_items
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving closet items: {str(e)}")

@app.delete("/closet-items")
async def clear_closet_items_endpoint():
    """
    Clear all items from the closets collection

    Returns:
        JSON response with clear operation results
    """
    try:
        # Call the MongoDB clear function
        result = clear_closets_collection()

        if result["success"]:
            return JSONResponse(content={
                "success": True,
                "message": result["message"],
                "deleted_count": result["deleted_count"],
                "initial_count": result.get("initial_count", 0),
                "final_count": result.get("final_count", 0)
            })
        else:
            raise HTTPException(status_code=500, detail=result["message"])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing closet items: {str(e)}")

@app.post("/outfit-suggestions")
async def get_outfit_suggestions_endpoint(request: OutfitSuggestionsRequest):
    """
    Get AI-powered outfit suggestions based on closet items and natural language query
    
    Args:
        request: JSON request containing query string
        
    Returns:
        JSON response with AI-generated outfit suggestions from closet items
    """
    try:
        query = request.query
        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="Query parameter is required and cannot be empty")
        
        # Call the MongoDB + LLM function
        result = get_outfit_suggestions_with_llm(query.strip())
        
        if result["success"]:
            return JSONResponse(content={
                "success": True,
                "query": result["query"],
                "total_closet_items": result["total_closet_items"],
                "message": result["message"],
                "outfit_suggestion": result["outfit_suggestion"],
                "suggested_items": result["suggested_items"],
                "suggested_items_count": len(result["suggested_items"])
            })
        else:
            # Handle case where no items found or other errors
            if "No items found in closet" in result["message"]:
                return JSONResponse(
                    content={
                        "success": False,
                        "query": query,
                        "message": result["message"],
                        "outfit_suggestion": "I'd love to help you style an outfit, but it looks like your closet is empty! Start by adding some items to your closet collection, and I'll be able to suggest amazing outfits for any occasion.",
                        "suggested_items": [],
                        "total_closet_items": 0,
                        "suggested_items_count": 0
                    },
                    status_code=404
                )
            else:
                raise HTTPException(status_code=500, detail=result["message"])
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating outfit suggestions: {str(e)}")

@app.get("/")
async def root():
    """
    Health check endpoint
    """
    return {"message": "Fashion Fitter API is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    """
    Detailed health check endpoint
    """
    return {
        "status": "healthy",
        "service": "Fashion Fitter API",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
