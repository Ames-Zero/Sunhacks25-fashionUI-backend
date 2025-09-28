from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
from typing import Optional
from bs4 import BeautifulSoup

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

# Initialize Google Gemini client with API key
api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable is required. Please set your Google AI Studio API key.")

client = genai.Client(api_key=api_key)

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