from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import ssl
import certifi

# Load environment variables from .env file
load_dotenv()

import os

DB_USERNAME = os.getenv("MONGO_USERNAME",)  # Your MongoDB Atlas username
DB_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_CLUSTER = os.getenv("MONGO_CLUSTER")  # Your cluster URL (e.g., cluster0.ab1cd.mongodb.net)
DB_NAME = os.getenv("MONGO_DBNAME")
# Construct connection string
uri = f"mongodb+srv://{DB_USERNAME}:{DB_PASSWORD}@{MONGO_CLUSTER}.mongodb.net/?retryWrites=true&w=majority&appName=Fashion"

# Create a new client and connect to the server with proper SSL configuration
# This fixes SSL certificate verification issues on macOS
client = MongoClient(
    uri, 
    server_api=ServerApi('1')
)


try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

# Get database reference
db = client.get_database(DB_NAME)  # Actual database name

def query_products(natural_language_query):
    """
    Query the products collection using natural language input

    Args:
        natural_language_query (str): Natural language query like "blue shirts" or "red t-shirts"

    Returns:
        list: List of matching product documents (MAX 10)
    """
    try:
        products_collection = db["products"]

        # Parse the natural language query
        query_lower = natural_language_query.lower().strip()

        # Extract color and category/subcategory from the query
        query_parts = query_lower.split()

        # Common colors mapping
        color_keywords = {
            'blue': ['blue', 'navy', 'dark blue', 'light blue'],
            'red': ['red', 'maroon', 'crimson', 'cherry'],
            'green': ['green', 'olive', 'forest green', 'lime'],
            'black': ['black', 'dark'],
            'white': ['white', 'cream', 'off-white'],
            'grey': ['grey', 'gray', 'charcoal'],
            'yellow': ['yellow', 'golden'],
            'pink': ['pink', 'rose'],
            'brown': ['brown', 'tan', 'beige'],
            'purple': ['purple', 'violet'],
            'orange': ['orange'],
            'multi': ['multi', 'multicolor', 'printed', 'pattern']
        }

        # Category/subcategory mapping
        category_mapping = {
            'shirt': 'Shirts',
            'shirts': 'Shirts',
            't-shirt': 'T-shirts & Polos',
            'tshirt': 'T-shirts & Polos',
            't-shirts': 'T-shirts & Polos',
            'tshirts': 'T-shirts & Polos',
            'polo': 'T-shirts & Polos',
            'polos': 'T-shirts & Polos',
            'jeans': 'Jeans',
            'pants': 'Trousers & Chinos',
            'trousers': 'Trousers & Chinos',
            'chinos': 'Trousers & Chinos',
            'shorts': 'Shorts',
            'jacket': 'Jackets & Coats',
            'jackets': 'Jackets & Coats',
            'sweater': 'Sweaters',
            'sweaters': 'Sweaters',
            'hoodie': 'Hoodies & Sweatshirts',
            'hoodies': 'Hoodies & Sweatshirts'
        }

        # Build MongoDB query
        mongo_query = {"$and": []}

        # Find color in query
        detected_color = None
        for color, variations in color_keywords.items():
            if any(variation in query_lower for variation in variations):
                detected_color = color
                break

        # Find category in query
        detected_category = None
        for keyword, subcategory in category_mapping.items():
            if keyword in query_lower:
                detected_category = subcategory
                break

        # Build query filters
        if detected_color:
            # Search in product_color field (case insensitive)
            color_filter = {
                "$or": [
                    {"product_color": {"$regex": detected_color, "$options": "i"}},
                    {"product_title": {"$regex": detected_color, "$options": "i"}}
                ]
            }
            mongo_query["$and"].append(color_filter)

        if detected_category:
            # Search in product_category field
            category_filter = {"product_category": {"$regex": detected_category, "$options": "i"}}
            mongo_query["$and"].append(category_filter)

        # If no specific filters found, do a text search
        if not mongo_query["$and"]:
            mongo_query = {
                "$or": [
                    {"product_title": {"$regex": query_lower, "$options": "i"}},
                    {"product_color": {"$regex": query_lower, "$options": "i"}},
                    {"product_category": {"$regex": query_lower, "$options": "i"}}
                ]
            }

        print(f"Searching for: '{natural_language_query}'")
        print(f"Detected - Color: {detected_color}, Category: {detected_category}")

        # Execute the query with limit of 10
        cursor = products_collection.find(mongo_query).limit(10)
        results = list(cursor)

        print(f"Found {len(results)} products matching the query")

        # Display results summary
        if results:
            print("\nMatching products:")
            for i, product in enumerate(results[:5], 1):  # Show first 5 in summary
                print(f"  {i}. {product.get('product_title', 'N/A')} - {product.get('product_color', 'N/A')} - ${product.get('product_price', 'N/A')}")
            if len(results) > 5:
                print(f"  ... and {len(results) - 5} more")

        return results

    except Exception as e:
        print(f"Error querying products: {e}")
        return []

def inspect_products_schema():
    """
    Inspect the actual structure of products in the database
    """
    try:
        products_collection = db["products"]
        sample_product = products_collection.find_one()
        
        if sample_product:
            print("Sample product structure:")
            for key, value in sample_product.items():
                if isinstance(value, dict):
                    print(f"  {key}: {list(value.keys()) if value else 'Empty dict'}")
                else:
                    print(f"  {key}: {type(value).__name__}")
            return sample_product
        return None
    except Exception as e:
        print(f"Error inspecting products schema: {e}")
        return None

def get_product_by_id(product_id):
    """
    Get a product from the products collection by its _id
    
    Args:
        product_id (str): The MongoDB _id of the product
        
    Returns:
        dict: Product document or None if not found
    """
    try:
        from bson import ObjectId
        products_collection = db["products"]
        
        # Convert string ID to ObjectId
        object_id = ObjectId(product_id)
        product = products_collection.find_one({"_id": object_id})
        
        return product
    except Exception as e:
        print(f"Error getting product by ID: {e}")
        return None

def add_product_to_closet(product_id):
    """
    Add a product from the products collection to the closets collection
    
    Args:
        product_id (str): The MongoDB _id of the product to add
        
    Returns:
        str: The inserted document ID or None if failed
    """
    try:
        # Get the product from products collection
        product = get_product_by_id(product_id)
        if not product:
            print(f"Product with ID {product_id} not found")
            return None
            
        # Get or create the closets collection
        closets_collection = db["closets"]
        
        # Create closet item from product data (new schema)
        closet_item = {
            "type": "product",
            "original_product_id": str(product["_id"]),
            "product_name": product.get("product_title", "N/A"),
            "product_title": product.get("product_title", "N/A"),
            "product_url": product.get("product_url", ""),
            "image_url": product.get("image_url", ""),
            "product_price": product.get("product_price", "N/A"),
            "product_color": product.get("product_color", "N/A"),
            "product_size": product.get("product_size", "N/A"),
            "product_category": product.get("product_category", "N/A"),
            # Legacy fields for backward compatibility
            "colors": {"primary": product.get("product_color", ""), "secondary": ""},
            "metadata": {"price": product.get("product_price", "N/A")},
            "category": product.get("product_category", "N/A"),
            "subcategory": product.get("product_category", "N/A")
        }
        
        # Add unique closet item ID
        import uuid
        closet_item["closet_item_id"] = str(uuid.uuid4())
        
        # Insert the document
        result = closets_collection.insert_one(closet_item)
        
        print(f"Successfully added product to closet with ID: {result.inserted_id}")
        return str(result.inserted_id)
        
    except Exception as e:
        print(f"Error adding product to closet: {e}")
        return None

def add_to_closet(closet_item):
    """
    Add a given item/row to the 'closets' collection in MongoDB
    Creates the collection if it doesn't exist
    
    DEPRECATED: Use add_product_to_closet() for adding products by ID

    Args:
        closet_item (dict): The item data to add to closets collection

    Returns:
        str: The inserted document ID or None if failed
    """
    try:
        # Get or create the closets collection
        closets_collection = db["closets"]

        # Check if collection exists, if not it will be created automatically on first insert
        existing_collections = db.list_collection_names()
        if "closets" not in existing_collections:
            print("Creating new 'closets' collection...")


        # Add an ID field if not provided for better tracking
        if "closet_item_id" not in closet_item:
            import uuid
            closet_item["closet_item_id"] = str(uuid.uuid4())

        # Insert the document (this creates the collection if it doesn't exist)
        result = closets_collection.insert_one(closet_item)

        print(f"Successfully added item to closet with ID: {result.inserted_id}")
        print(f"Closet item ID: {closet_item.get('closet_item_id')}")

        # Verify collection was created
        updated_collections = db.list_collection_names()
        if "closets" in updated_collections:
            total_items = closets_collection.count_documents({})
            print(f"Closets collection now has {total_items} items")

        return str(result.inserted_id)

    except Exception as e:
        print(f"Error adding item to closet: {e}")
        return None

def get_all_closet_items(limit=None):
    """
    Display all data entries from the 'closets' collection

    Args:
        limit (int, optional): Limit the number of results returned

    Returns:
        list: List of all closet items
    """
    try:
        closets_collection = db["closets"]

        # Check if collection exists
        existing_collections = db.list_collection_names()
        if "closets" not in existing_collections:
            print("❌ 'closets' collection doesn't exist yet")
            return []

        # Get total count
        total_count = closets_collection.count_documents({})

        if total_count == 0:
            print("❌ No items found in closets collection")
            return []

        print(f"👕 Closets Collection Data")
        print("=" * 60)
        print(f"Total items: {total_count}")
        print("-" * 60)

        # Execute query
        if limit:
            cursor = closets_collection.find({}).limit(limit)
            print(f"Showing first {limit} items:")
        else:
            cursor = closets_collection.find({})
            print("Showing all items:")

        results = list(cursor)

        # Display results in a formatted way
        for i, item in enumerate(results, 1):
            print(f"\n📦 Item {i}:")
            print(f"   MongoDB ID: {item.get('_id', 'N/A')}")
            print(f"   Closet Item ID: {item.get('closet_item_id', 'N/A')}")
            print(f"   Type: {item.get('type', 'N/A')}")

            # Handle different naming conventions
            product_name = item.get('product_name') or item.get('title', 'N/A')
            print(f"   Product Name: {product_name}")

            print(f"   Brand: {item.get('brand', 'N/A')}")

            # Display colors
            colors = item.get('colors', {})
            if colors:
                primary_color = colors.get('primary', 'N/A')
                secondary_color = colors.get('secondary', 'N/A')
                print(f"   Colors: {primary_color} / {secondary_color}")

            # Display category info
            category = item.get('category', 'N/A')
            subcategory = item.get('subcategory', 'N/A')
            print(f"   Category: {category} > {subcategory}")

            # Display price from metadata
            metadata = item.get('metadata', {})
            price = metadata.get('price', 'N/A')
            print(f"   Price: ${price}")

            # Display creation date
            created_at = item.get('created_at', 'N/A')
            print(f"   Created: {created_at}")

            # Display image URL if available
            image_url = item.get('image_url', '') or item.get('urls', {}).get('image', '')
            if image_url:
                print(f"   Image: {image_url[:60]}{'...' if len(image_url) > 60 else ''}")

            print("-" * 40)

        print(f"\n✅ Displayed {len(results)} closet items")
        return results

    except Exception as e:
        print(f"❌ Error retrieving closet items: {e}")
        return []

def clear_closets_collection():
    """
    Clear all items from the 'closets' collection
    This function removes all documents from the closets collection

    Returns:
        dict: Result of the clear operation
    """
    try:
        closets_collection = db["closets"]

        # Check if collection exists
        existing_collections = db.list_collection_names()
        if "closets" not in existing_collections:
            print("ℹ️ 'closets' collection doesn't exist - nothing to clear")
            return {"success": True, "message": "Collection doesn't exist", "deleted_count": 0}

        # Get count before deletion
        initial_count = closets_collection.count_documents({})

        if initial_count == 0:
            print("ℹ️ 'closets' collection is already empty")
            return {"success": True, "message": "Collection already empty", "deleted_count": 0}

        # Delete all documents
        result = closets_collection.delete_many({})

        print(f"🗑️ Cleared 'closets' collection")
        print(f"   Deleted {result.deleted_count} items")

        # Verify collection is empty
        final_count = closets_collection.count_documents({})
        if final_count == 0:
            print("✅ Collection cleared successfully")
        else:
            print(f"⚠️ Warning: {final_count} items still remain")

        return {
            "success": True,
            "message": f"Successfully cleared closets collection",
            "deleted_count": result.deleted_count,
            "initial_count": initial_count,
            "final_count": final_count
        }

    except Exception as e:
        error_msg = f"Error clearing closets collection: {e}"
        print(f"❌ {error_msg}")
        return {
            "success": False,
            "message": error_msg,
            "deleted_count": 0
        }

def get_outfit_suggestions_with_llm(user_query):
    """
    Get outfit suggestions based on natural language query using closet items and Gemini LLM
    
    Args:
        user_query (str): Natural language query about the occasion or outfit preference
        
    Returns:
        dict: Outfit suggestions with LLM-generated explanation and suggested items
    """
    try:
        from google import genai
        import os
        import json
        
        # Get all closet items
        closet_items = get_all_closet_items()
        
        if not closet_items:
            return {
                "success": False,
                "message": "No items found in closet",
                "outfit_suggestion": "",
                "suggested_items": []
            }
        
        # Format closet items for LLM with numbered IDs
        items_for_llm = []
        for i, item in enumerate(closet_items):
            # Handle both old and new schema
            color = item.get("product_color") or item.get("colors", {}).get("primary", "unknown color")
            category = item.get("product_category") or item.get("subcategory", "N/A")
            title = item.get("product_title") or item.get("product_name") or item.get("title", "Unknown Item")
            
            item_desc = f"{i+1}. {title} ({category}) in {color}"
            items_for_llm.append(item_desc)
        
        # Create prompt for Gemini
        closet_items_text = "\n".join(items_for_llm)
        
        prompt = f"""
You are a professional fashion stylist. A user wants outfit suggestions for: "{user_query}"

Available items in their closet (numbered):
{closet_items_text}

Your task:
1. Pick the item numbers that would work best for this occasion
2. Write a concise outfit suggestion (1-2 sentences, under 250 characters)

Respond in this EXACT JSON format:
{{
  "outfit_suggestion": "Your concise styling advice here",
  "item_numbers": [list of numbers like 1, 2, 3 for the items you recommend]
}}

Requirements:
- Only use item numbers from the list above
- Keep outfit_suggestion brief but helpful (under 250 characters)
- Consider color coordination and occasion appropriateness
- Focus on practical styling advice

Example:
{{
  "outfit_suggestion": "For a business meeting, pair the navy blazer with white shirt and dark jeans. Classic and professional.",
  "item_numbers": [1, 2, 3]
}}
"""

        # Initialize Gemini client
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            return {
                "success": False,
                "message": "Google API key not configured",
                "outfit_suggestion": "",
                "suggested_items": []
            }
        
        client = genai.Client(api_key=api_key)
        
        # Generate outfit suggestions using Gemini
        response = client.models.generate_content(
            model='gemini-2.5-pro',  # Using text-only model for outfit suggestions
            contents=[prompt]
        )
        
        # Extract the generated text
        if response.candidates and len(response.candidates) > 0:
            suggestion_text = response.candidates[0].content.parts[0].text
            
            try:
                # Parse JSON response from LLM
                # Clean the response text (remove any markdown formatting)
                clean_text = suggestion_text.strip()
                if clean_text.startswith('```json'):
                    clean_text = clean_text[7:]
                if clean_text.endswith('```'):
                    clean_text = clean_text[:-3]
                clean_text = clean_text.strip()
                
                parsed_response = json.loads(clean_text)
                
                # Extract suggested item numbers and get the actual items
                suggested_item_numbers = parsed_response.get("item_numbers", [])
                suggested_items = []
                
                for item_number in suggested_item_numbers:
                    # Convert to 0-based index
                    try:
                        index = int(item_number) - 1
                        if 0 <= index < len(closet_items):
                            item = closet_items[index]
                            formatted_item = {
                                "id": str(item.get("_id", "")),
                                "product_name": item.get("product_title") or item.get("product_name") or item.get("title", "N/A"),
                                "product_title": item.get("product_title", "N/A"),
                                "product_price": item.get("product_price") or item.get("metadata", {}).get("price", "N/A"),
                                "product_color": item.get("product_color") or item.get("colors", {}).get("primary", "N/A"),
                                "product_category": item.get("product_category") or item.get("category", "N/A"),
                                "product_size": item.get("product_size", "N/A"),
                                "image_url": item.get("image_url", ""),
                                "product_url": item.get("product_url", "")
                            }
                            suggested_items.append(formatted_item)
                    except (ValueError, IndexError):
                        continue
                
                # Get the AI's concise suggestion (not truncated)
                outfit_suggestion = parsed_response.get("outfit_suggestion", "")
                
                return {
                    "success": True,
                    "query": user_query,
                    "total_closet_items": len(closet_items),
                    "outfit_suggestion": outfit_suggestion,  # Use AI's complete suggestion
                    "suggested_items": suggested_items,
                    "message": "Outfit suggestions generated successfully"
                }
                
            except json.JSONDecodeError:
                # Fallback: if JSON parsing fails, return the raw text as suggestion
                return {
                    "success": True,
                    "query": user_query,
                    "total_closet_items": len(closet_items),
                    "outfit_suggestion": suggestion_text,  # Use complete text without truncation
                    "suggested_items": [],
                    "message": "Outfit suggestions generated successfully (fallback mode)"
                }
        else:
            return {
                "success": False,
                "message": "Failed to generate outfit suggestions from LLM",
                "outfit_suggestion": "",
                "suggested_items": []
            }
            
    except Exception as e:
        print(f"Error generating outfit suggestions: {e}")
        return {
            "success": False,
            "message": f"Error generating outfit suggestions: {str(e)}",
            "outfit_suggestion": "",
            "suggested_items": []
        }

def get_closet_summary():
    """
    Display a summary of closets collection statistics

    Returns:
        dict: Summary statistics
    """
    try:
        closets_collection = db["closets"]

        # Check if collection exists
        existing_collections = db.list_collection_names()
        if "closets" not in existing_collections:
            print("❌ 'closets' collection doesn't exist yet")
            return {}

        print(f"📊 Closets Collection Summary")
        print("=" * 50)

        # Total count
        total_items = closets_collection.count_documents({})
        print(f"Total items: {total_items}")

        if total_items == 0:
            print("Collection is empty")
            return {"total_items": 0}

        # Count by type
        type_counts = {}
        for item_type in closets_collection.distinct("type"):
            count = closets_collection.count_documents({"type": item_type})
            type_counts[item_type] = count
            print(f"  - {item_type}: {count} items")



        # Most recent items
        print(f"\nMost recent items:")
        recent_items = list(closets_collection.find().sort("created_at", -1).limit(3))
        for i, item in enumerate(recent_items, 1):
            product_name = item.get('product_name') or item.get('title', 'N/A')
            created_at = item.get('created_at', 'N/A')
            print(f"  {i}. {product_name} - {created_at}")

        summary = {
            "total_items": total_items,
            "type_counts": type_counts,
            "recent_items": len(recent_items)
        }

        print(f"\n✅ Summary complete")
        return summary

    except Exception as e:
        print(f"❌ Error getting closet summary: {e}")
        return {}

# Example usage functions
def search_products_by_category(category):
    """
    Search products by category

    Args:
        category (str): Product category to search for

    Returns:
        list: List of products in the specified category
    """
    return query_products({"category": category})

# Database Schema Exploration Functions

def list_all_databases():
    """
    List all databases in the MongoDB cluster

    Returns:
        list: List of database names
    """
    try:
        databases = client.list_database_names()
        print("Available databases:")
        for db_name in databases:
            print(f"  - {db_name}")
        return databases
    except Exception as e:
        print(f"Error listing databases: {e}")
        return []

def list_all_collections(database_name=None):
    """
    List all collections in a specific database

    Args:
        database_name (str): Name of the database (defaults to current db)

    Returns:
        list: List of collection names
    """
    try:
        if database_name:
            target_db = client.get_database(database_name)
        else:
            target_db = db
            database_name = db.name

        collections = target_db.list_collection_names()
        print(f"Collections in '{database_name}' database:")
        for collection_name in collections:
            count = target_db[collection_name].count_documents({})
            print(f"  - {collection_name} ({count} documents)")

        return collections
    except Exception as e:
        print(f"Error listing collections: {e}")
        return []

def explore_collection_schema(collection_name, database_name=None, sample_size=100):
    """
    Explore the schema/structure of a collection by sampling documents

    Args:
        collection_name (str): Name of the collection to explore
        database_name (str): Name of the database (defaults to current db)
        sample_size (int): Number of documents to sample for schema analysis

    Returns:
        dict: Schema information including field types and examples
    """
    try:
        if database_name:
            target_db = client.get_database(database_name)
        else:
            target_db = db

        collection = target_db[collection_name]

        # Get basic collection info
        total_docs = collection.count_documents({})
        print(f"\n=== Collection: {collection_name} ===")
        print(f"Total documents: {total_docs}")

        if total_docs == 0:
            print("Collection is empty")
            return {}

        # Sample documents for schema analysis
        sample_docs = list(collection.aggregate([{"$sample": {"size": min(sample_size, total_docs)}}]))

        # Analyze schema
        schema = {}
        for doc in sample_docs:
            for field, value in doc.items():
                field_type = type(value).__name__

                if field not in schema:
                    schema[field] = {
                        'types': set(),
                        'examples': [],
                        'count': 0
                    }

                schema[field]['types'].add(field_type)
                schema[field]['count'] += 1

                # Store a few examples
                if len(schema[field]['examples']) < 3:
                    schema[field]['examples'].append(value)

        # Display schema
        print(f"\nSchema analysis (based on {len(sample_docs)} documents):")
        print("-" * 60)

        for field, info in schema.items():
            types_str = ", ".join(info['types'])
            frequency = (info['count'] / len(sample_docs)) * 100

            print(f"Field: {field}")
            print(f"  Types: {types_str}")
            print(f"  Frequency: {frequency:.1f}% ({info['count']}/{len(sample_docs)} docs)")
            print(f"  Examples: {info['examples'][:2]}")
            print()

        # Convert sets to lists for JSON serialization
        for field in schema:
            schema[field]['types'] = list(schema[field]['types'])

        return schema

    except Exception as e:
        print(f"Error exploring collection schema: {e}")
        return {}

def get_sample_documents(collection_name, database_name=None, limit=5):
    """
    Get sample documents from a collection

    Args:
        collection_name (str): Name of the collection
        database_name (str): Name of the database (defaults to current db)
        limit (int): Number of sample documents to return

    Returns:
        list: Sample documents
    """
    try:
        if database_name:
            target_db = client.get_database(database_name)
        else:
            target_db = db

        collection = target_db[collection_name]
        samples = list(collection.find().limit(limit))

        print(f"\nSample documents from '{collection_name}':")
        print("=" * 50)

        for i, doc in enumerate(samples, 1):
            print(f"\nDocument {i}:")
            for key, value in doc.items():
                # Truncate long values for readability
                if isinstance(value, str) and len(value) > 100:
                    value = value[:100] + "..."
                elif isinstance(value, list) and len(value) > 3:
                    value = value[:3] + ["..."]
                print(f"  {key}: {value}")

        return samples

    except Exception as e:
        print(f"Error getting sample documents: {e}")
        return []

def full_database_exploration(database_name=None):
    """
    Perform a complete exploration of the database

    Args:
        database_name (str): Name of the database to explore (defaults to current db)
    """
    print("🔍 Starting full database exploration...")
    print("=" * 60)

    # List all databases
    databases = list_all_databases()

    # Focus on specified database or current one
    if database_name:
        target_db_name = database_name
    else:
        target_db_name = db.name

    print(f"\n🎯 Exploring database: {target_db_name}")
    print("=" * 60)

    # List collections
    collections = list_all_collections(target_db_name)

    # Explore each collection
    for collection_name in collections:
        print(f"\n📊 Analyzing collection: {collection_name}")
        explore_collection_schema(collection_name, target_db_name, sample_size=50)
        get_sample_documents(collection_name, target_db_name, limit=2)
        print("-" * 80)

# Convenience function to run exploration
def explore_db():
    """Quick function to explore the current database"""
    full_database_exploration(database_name="fashion_database")

# Test functions for the updated functionality
def test_natural_language_search():
    """Test function to demonstrate natural language search"""
    test_queries = [
        "blue shirts",
        "red t-shirts",
        "black jeans",
        "white polo",
        "green hoodie",
        "multi shirts"
    ]

    print("🧪 Testing Natural Language Product Search")
    print("=" * 50)

    for query in test_queries:
        print(f"\n🔍 Testing query: '{query}'")
        print("-" * 30)
        results = query_products(query)
        if not results:
            print("No results found")
        print()

def test_add_to_closet():
    """Test function to demonstrate adding items to closet"""
    print("🧪 Testing Add to Closet Functionality")
    print("=" * 50)

    # Test item 1: Generated photo
    test_item_1 = {
        "type": "generated_photo",
        "title": "Blue Cotton Shirt - Generated",
        "image_url": "https://example-bucket.s3.amazonaws.com/generated_123.png",
        "original_product_id": "some_product_id",
        "metadata": {
            "color": "blue",
            "category": "shirts",
            "generated_at": "2025-09-27"
        }
    }

    # Test item 2: Saved product
    test_item_2 = {
        "type": "saved_product",
        "title": "Red T-Shirt from Amazon",
        "product_url": "https://amazon.com/product/xyz",
        "image_url": "https://amazon.com/image.jpg",

        "price": 25.99,
        "metadata": {
            "color": "red",
            "category": "t-shirts",
            "brand": "Test Brand"
        }
    }

    print("Adding test items to closet...")

    result1 = add_to_closet(test_item_1)
    print()
    result2 = add_to_closet(test_item_2)

    if result1 and result2:
        print(f"\n✅ Successfully added both test items to closet!")
    else:
        print(f"\n❌ Some items failed to add")

def test_closet_display():
    """Test function to demonstrate closet display functionality"""
    print("🧪 Testing Closet Display Functions")
    print("=" * 50)

    # Test 1: Display summary
    print("\n📊 Testing closet summary...")
    get_closet_summary()

    # Test 2: Display all items
    print("\n📦 Testing display all closet items...")
    get_all_closet_items(limit=5)  # Limit to 5 for testing

    # Test 3: Display limited items
    print("\n👤 Testing display with limit...")
    get_all_closet_items(limit=3)

    print(f"\n✅ Closet display tests completed!")

def test_clear_closets():
    """Test function to demonstrate clear closets functionality"""
    print("🧪 Testing Clear Closets Functionality")
    print("=" * 50)

    # First show current state
    print("\n📊 Before clearing:")
    get_closet_summary()

    # Clear the collection
    print("\n🗑️ Clearing closets collection...")
    result = clear_closets_collection()

    # Show result
    if result["success"]:
        print(f"✅ Clear operation successful!")
        print(f"   {result['message']}")
        print(f"   Deleted {result['deleted_count']} items")
    else:
        print(f"❌ Clear operation failed!")
        print(f"   {result['message']}")

    # Show state after clearing
    print("\n📊 After clearing:")
    get_closet_summary()

    print(f"\n✅ Clear test completed!")

def test_outfit_suggestions():
    """Test function to demonstrate outfit suggestions functionality"""
    print("🧪 Testing Outfit Suggestions with LLM")
    print("=" * 50)
    
    # First, add some test items to the closet if it's empty
    closet_items = get_all_closet_items(limit=1)
    if not closet_items:
        print("📦 Adding test items to closet for demonstration...")
        
        test_items = [
            {
                "type": "test_item",
                "product_name": "Navy Blue Blazer",
                "category": "Clothing",
                "subcategory": "Jackets & Coats",
                "colors": {"primary": "navy blue", "secondary": ""},
                "brand": "Calvin Klein",
                "metadata": {"price": "149.99"}
            },
            {
                "type": "test_item", 
                "product_name": "White Cotton Dress Shirt",
                "category": "Clothing",
                "subcategory": "Shirts",
                "colors": {"primary": "white", "secondary": ""},
                "brand": "Brooks Brothers",
                "metadata": {"price": "79.99"}
            },
            {
                "type": "test_item",
                "product_name": "Dark Wash Jeans",
                "category": "Clothing", 
                "subcategory": "Jeans",
                "colors": {"primary": "dark blue", "secondary": ""},
                "brand": "Levi's",
                "metadata": {"price": "89.99"}
            },
            {
                "type": "test_item",
                "product_name": "Black Leather Shoes",
                "category": "Shoes",
                "subcategory": "Dress Shoes", 
                "colors": {"primary": "black", "secondary": ""},
                "brand": "Cole Haan",
                "metadata": {"price": "199.99"}
            }
        ]
        
        for item in test_items:
            add_to_closet(item)
        
        print("✅ Test items added to closet")
    
    # Test different occasion queries
    test_queries = [
        "business meeting",
        "casual date night", 
        "weekend brunch",
        "formal dinner party",
        "job interview"
    ]
    
    print(f"\n🎯 Testing outfit suggestions for different occasions:")
    print("-" * 60)
    
    for query in test_queries:
        print(f"\n🔍 Testing query: '{query}'")
        print("=" * 40)
        
        result = get_outfit_suggestions_with_llm(query)
        
        if result["success"]:
            print(f"✅ Query: {result['query']}")
            print(f"📊 Available items: {result['total_closet_items']}")
            print(f"👗 Stylist suggestions:")
            print("-" * 30)
            print(result['stylist_suggestions'])
            print("\n" + "="*60)
        else:
            print(f"❌ Failed: {result['message']}")
        
        print()
    
    print(f"\n✅ Outfit suggestions tests completed!")

# Example usage functions
