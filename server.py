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
from mongo_search import query_products, add_to_closet, get_all_closet_items, clear_closets_collection

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
            formatted_product = {
                "id": str(product.get("_id", "")),
                "product_name": product.get("product_name", "N/A"),
                "brand": product.get("brand", "N/A"),
                "category": product.get("category", "N/A"),
                "subcategory": product.get("subcategory", "N/A"),
                "colors": product.get("colors", {}),
                "price": product.get("metadata", {}).get("price", "N/A"),
                "rating": product.get("metadata", {}).get("rating", "N/A"),
                "image_url": product.get("urls", {}).get("image", ""),
                "product_url": product.get("urls", {}).get("product", ""),
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
    closet_item: Dict[Any, Any] = Body(..., description="Item data to add to closet")
):
    """
    Add an item to the user's closet collection
    
    Args:
        closet_item: Dictionary containing the item data to add to closet
    
    Returns:
        JSON response with insertion confirmation
    """
    try:
        if not closet_item:
            raise HTTPException(status_code=400, detail="Closet item data is required")
        
        # Validate required fields (basic validation)
        if "type" not in closet_item:
            closet_item["type"] = "manual_add"  # Default type
        
        # Call the MongoDB add function
        result_id = add_to_closet(closet_item)
        
        if result_id:
            return JSONResponse(content={
                "success": True,
                "message": "Item successfully added to closet",
                "closet_item_id": closet_item.get("closet_item_id"),
                "mongodb_id": result_id,
                "item_type": closet_item.get("type", "unknown")
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to add item to closet")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding item to closet: {str(e)}")

@app.get("/closet-items")
async def get_closet_items_endpoint(
    user_id: Optional[str] = None,
    limit: Optional[int] = None
):
    """
    Get all items from the closets collection
    
    Args:
        user_id (str, optional): Filter by specific user ID
        limit (int, optional): Limit the number of results returned
    
    Returns:
        JSON response with closet items
    """
    try:
        # Call the MongoDB function to get closet items
        closet_items = get_all_closet_items(user_id=user_id, limit=limit)
        
        # Format the response
        formatted_items = []
        for item in closet_items:
            formatted_item = {
                "id": str(item.get("_id", "")),
                "closet_item_id": item.get("closet_item_id", ""),
                "type": item.get("type", "N/A"),
                "product_name": item.get("product_name") or item.get("title", "N/A"),
                "brand": item.get("brand", "N/A"),
                "colors": item.get("colors", {}),
                "category": item.get("category", "N/A"),
                "subcategory": item.get("subcategory", "N/A"),
                "price": item.get("metadata", {}).get("price", "N/A"),
                "user_id": item.get("closet_metadata", {}).get("user_id") or item.get("user_id", "N/A"),
                "created_at": str(item.get("created_at", "N/A")),
                "image_url": item.get("image_url", "") or item.get("urls", {}).get("image", ""),
                "product_url": item.get("product_url", "") or item.get("urls", {}).get("product", ""),
                "notes": item.get("closet_metadata", {}).get("notes", ""),
                "metadata": item.get("metadata", {})
            }
            formatted_items.append(formatted_item)
        
        return JSONResponse(content={
            "success": True,
            "total_items": len(closet_items),
            "user_filter": user_id,
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
