from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Body
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
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


MODEL_IMAGE_PATH = "model_photo.jpg"  # Replace with your model image path
IMAGE_GENERATION_MODEL = os.getenv('IMAGE_GENERATION_MODEL')  # Replace with your desired model
S3_BUCKET_NAME = os.getenv('S3_BUCKET')

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
    raise ValueError("GOOGLE_API_KEY environment variable is required. Please set your Google AI Studio API key.")

client = genai.Client(api_key=api_key)

# Clear closets collection on startup
print("🚀 Starting Fashion Fitter API...")
clear_result = clear_closets_collection()
if clear_result["success"]:
    print(f"✅ Startup: {clear_result['message']} ({clear_result['deleted_count']} items removed)")
else:
    print(f"⚠️ Startup warning: {clear_result['message']}")

def scrape_amazon_product(url):
    headers = {
        "User-Agent": random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36"
        ])
    }
    time.sleep(random.uniform(1, 3))  # Random delay to avoid blocking
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract Product Title
        title = soup.find('span', {'id': 'productTitle'}).get_text(strip=True) if soup.find('span', {'id': 'productTitle'}) else 'N/A'
        color = soup.find('span', {'id': 'inline-twister-expanded-dimension-text-color_name'}).get_text(strip=True) if soup.find('span', {'id': 'inline-twister-expanded-dimension-text-color_name'}) else 'N/A'
        size = soup.find('span', {'id': 'inline-twister-expanded-dimension-text-size_name'}).get_text(strip=True) if soup.find('span', {'id': 'inline-twister-expanded-dimension-text-size_name'}) else 'N/A'

        # Extract Price
        price = soup.find('span', {'class': 'a-price-whole'}).get_text(strip=True) if soup.find('span', {'class': 'a-price-whole'}) else 'N/A'

        # Extract High-Resolution Image URLs using regex
        image_urls = re.findall('"hiRes":"(https://.+?)"', response.text)

        # Get breadcrumbs text
        breadcrumbs = soup.select("#wayfinding-breadcrumbs_feature_div ul li span a")
        categories = [b.get_text(strip=True) for b in breadcrumbs]
        category = categories[-1] if categories else "N/A"

        product_about_ul = soup.find("ul", {"class": "a-unordered-list a-vertical a-spacing-small"})
        product_about_info = [li.get_text(strip=True) for li in product_about_ul.find_all("li")] if product_about_ul else []

        return {
            'url': url,
            'title': title,
            'price': price,
            'color': color,
            'size': size,
            'category': category,
            'product_about_info': product_about_info
        }, image_urls
    else:
        print(f"Failed to fetch data from {url}")
        return None

@app.post("/generate-photo-and-data")
async def generate_photo_and_data(
    url: str = Form(..., description="Amazon product URL to scrape"),
    prompt: Optional[str] = Form(
        default="""Create a professional e-commerce fashion photo.
        Take the dress from the first image and let the person from the second image wear it.
        Generate a realistic, full-body shot of the person wearing the dress, with the lighting and shadows adjusted to match the environment.
        """,
        description="Custom prompt for image generation"
    )
):
    """
    Generate a fashion photo by combining a dress image with a model image.
    Returns the generated image as base64 encoded string.
    """

    page_metadata, image_urls = scrape_amazon_product(url)
    if not page_metadata or not image_urls:
        print(page_metadata, image_urls)
        raise HTTPException(status_code=400, detail="Failed to scrape product data or no images found from the provided URL")

    if len(image_urls) >= 1:
        dress_image_url = image_urls[0]
    else:
        raise HTTPException(status_code=400, detail="No product images found from the provided URL")

    # Download the dress image from the URL
    try:
        dress_response = requests.get(dress_image_url)
        dress_response.raise_for_status()
        dress_pil = Image.open(BytesIO(dress_response.content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download dress image: {str(e)}")

    # Load the local model image
    try:
        with open(MODEL_IMAGE_PATH, 'rb') as model_file:
            model_bytes = model_file.read()
        model_pil = Image.open(BytesIO(model_bytes))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load model image: {str(e)}")

    try:

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
            raise HTTPException(status_code=500, detail="No image generated from the model")

        generated_image = Image.open(BytesIO(image_parts[0]))

        # Convert PIL image to buffer for S3 upload
        buffer = BytesIO()
        generated_image.save(buffer, format='PNG')

        # Upload image to S3 and make it publicly accessible
        s3_client = boto3.client("s3")
        bucket_name = S3_BUCKET_NAME
        s3_key = f"generated_images/{uuid.uuid4()}.png"

        buffer.seek(0)
        s3_client.upload_fileobj(buffer, bucket_name, s3_key, ExtraArgs={'ContentType': 'image/png'})
        image_url = s3_client.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': s3_key}, ExpiresIn=3600)  # 1 hour expiry

        return JSONResponse(content={
            "success": True,
            "image_public_url": image_url,
            "metadata": page_metadata,
            "image_format": "PNG"
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating fashion photo: {str(e)}")

@app.post("/search-products")
async def search_products_endpoint(
    query: str = Form(..., description="Natural language query like 'blue shirts' or 'red t-shirts'")
):
    """
    Search products using natural language query

    Args:
        query: Natural language search query (e.g., "blue shirts", "red t-shirts")

    Returns:
        JSON response with matching products (max 10)
    """
    try:
        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="Query parameter is required and cannot be empty")

        # Call the MongoDB query function
        results = query_products(query.strip())

        # Format the response
        formatted_results = []
        for product in results:
            # Handle different possible URL field structures
            urls = product.get("urls", {})
            image_url = ""
            product_url = ""
            
            # Try different possible field names for URLs
            if isinstance(urls, dict):
                image_url = urls.get("image", "") or urls.get("image_url", "")
                product_url = urls.get("product", "") or urls.get("product_url", "")
            
            # Fallback to direct fields if urls dict doesn't exist
            if not image_url:
                image_url = product.get("image_url", "")
            if not product_url:
                product_url = product.get("product_url", "")
            
            formatted_product = {
                "id": str(product.get("_id", "")),
                "product_name": product.get("product_name", "N/A"),
                "brand": product.get("brand", "N/A"),
                "category": product.get("category", "N/A"),
                "subcategory": product.get("subcategory", "N/A"),
                "colors": product.get("colors", {}),
                "price": product.get("metadata", {}).get("price", "N/A"),
                "rating": product.get("metadata", {}).get("rating", "N/A"),
                "image_url": image_url,
                "product_url": product_url,
                "attributes": product.get("attributes", {})
            }
            formatted_results.append(formatted_product)

        return JSONResponse(content={
            "success": True,
            "query": query,
            "total_results": len(results),
            "products": formatted_results
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching products: {str(e)}")

@app.post("/add-to-closet")
async def add_to_closet_endpoint(
    product_id: str = Form(..., description="Product ID from the products collection")
):
    """
    Add a product to the closet collection using product ID
    
    Args:
        product_id: MongoDB _id of the product from products collection
        
    Returns:
        JSON response with insertion confirmation
    """
    try:
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
                "product_name": item.get("product_name") or item.get("title", "N/A"),
                "brand": item.get("brand", "N/A"),
                "category": item.get("category", "N/A"),
                "subcategory": item.get("subcategory", "N/A"),
                "colors": item.get("colors", {}),
                "price": item.get("metadata", {}).get("price", "N/A"),
                "image_url": item.get("image_url", "") or item.get("urls", {}).get("image", ""),
                "product_url": item.get("product_url", "") or item.get("urls", {}).get("product", "")
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
async def get_outfit_suggestions_endpoint(
    query: str = Form(..., description="Natural language query describing the occasion or outfit preference")
):
    """
    Get AI-powered outfit suggestions based on closet items and natural language query
    
    Args:
        query: Natural language query like "casual date night", "business meeting", "weekend brunch"
        
    Returns:
        JSON response with AI-generated outfit suggestions from closet items
    """
    try:
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
                "stylist_suggestions": result["stylist_suggestions"],
                "available_items_count": result["available_items"]
            })
        else:
            # Handle case where no items found or other errors
            if "No items found in closet" in result["message"]:
                return JSONResponse(
                    content={
                        "success": False,
                        "query": query,
                        "message": result["message"],
                        "stylist_suggestions": "I'd love to help you style an outfit, but it looks like your closet is empty! Start by adding some items to your closet collection, and I'll be able to suggest amazing outfits for any occasion.",
                        "total_closet_items": 0,
                        "available_items_count": 0
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
