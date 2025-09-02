#!/usr/bin/env python3
"""
MongoDB Connection Test Script
Tests the MongoDB URI configuration from .env file
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_mongodb_connection():
    """Test MongoDB connection with current configuration"""
    
    try:
        from pymongo import MongoClient
        from pymongo.errors import ConnectionFailure
        import os
        from dotenv import load_dotenv
        
        # Load environment variables
        load_dotenv()
        
        mongo_uri = os.getenv('MONGO_URI')
        mongo_database = os.getenv('MONGO_DATABASE')
        
        # Extract database name from URI if MONGO_DATABASE is not set
        if not mongo_database and mongo_uri:
            try:
                # Parse URI to extract database name
                from urllib.parse import urlparse
                parsed = urlparse(mongo_uri)
                if parsed.path and len(parsed.path) > 1:
                    mongo_database = parsed.path[1:]  # Remove leading '/'
            except Exception as e:
                print(f"⚠️ Warning: Could not extract database from URI: {e}")
        
        print("=== MongoDB Connection Test ===")
        print(f"URI: {mongo_uri}")
        print(f"Database: {mongo_database}")
        print()
        
        # Test connection
        print("Attempting to connect...")
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        
        # Test authentication
        print("Testing authentication...")
        client.admin.command('ping')
        
        # Test database access
        print("Testing database access...")
        db = client[mongo_database]
        collections = db.list_collection_names()
        
        print("✅ SUCCESS: MongoDB connection successful!")
        print(f"Available collections: {collections}")
        
        # Test basic operations
        print("\nTesting basic operations...")
        test_collection = db['connection_test']
        
        # Insert test document
        test_doc = {"test": "connection", "timestamp": "2025-08-31"}
        result = test_collection.insert_one(test_doc)
        print(f"✅ Insert test successful. Document ID: {result.inserted_id}")
        
        # Read test document
        found_doc = test_collection.find_one({"_id": result.inserted_id})
        print(f"✅ Read test successful. Document: {found_doc}")
        
        # Delete test document
        test_collection.delete_one({"_id": result.inserted_id})
        print("✅ Delete test successful.")
        
        client.close()
        
        return True
        
    except ConnectionFailure as e:
        print(f"❌ CONNECTION FAILED: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure MongoDB is running: mongod --version")
        print("2. Check if MongoDB service is started")
        print("3. Verify port 27017 is accessible")
        return False
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ ERROR: {error_msg}")
        
        if "Authentication failed" in error_msg or "auth" in error_msg.lower():
            print("\n❌ AUTHENTICATION FAILED")
            print("\nTroubleshooting tips:")
            print("1. Verify username/password are correct")
            print("2. Check if user exists: mongo --eval 'db.getUsers()'")
            print("3. Try different authSource (admin vs database name)")
            print("\nAlternative URI formats to try:")
            print("- mongodb://samay2504:250403@localhost:27017/human_ai_co_create?authSource=admin")
            print("- mongodb://samay2504:250403@localhost:27017/human_ai_co_create")
            
        elif "ImportError" in error_msg or "pymongo" in error_msg:
            print("\n❌ IMPORT ERROR")
            print("Install pymongo: pip install pymongo")
            
        return False

def suggest_uri_alternatives():
    """Suggest alternative URI configurations"""
    
    username = "samay2504"
    password = "250403"
    database = "human_ai_co_create"
    
    print("\n=== Alternative MongoDB URI Configurations ===")
    
    uris = [
        f"mongodb://{username}:{password}@localhost:27017/{database}?authSource=admin",
        f"mongodb://{username}:{password}@localhost:27017/{database}?authSource={database}",
        f"mongodb://{username}:{password}@localhost:27017/{database}",
        f"mongodb://localhost:27017/{database}",  # No auth
    ]
    
    for i, uri in enumerate(uris, 1):
        print(f"{i}. {uri}")
    
    print("\nTry these URIs if the current one fails.")

if __name__ == "__main__":
    success = test_mongodb_connection()
    
    if not success:
        suggest_uri_alternatives()
        
        print("\n=== Manual Test Commands ===")
        print("Test MongoDB connection manually:")
        print("1. mongo --host localhost --port 27017 -u samay2504 -p 250403 --authenticationDatabase admin")
        print("2. mongo --host localhost --port 27017 -u samay2504 -p 250403 --authenticationDatabase human_ai_co_create")
        print("3. mongo --host localhost --port 27017")
        
    sys.exit(0 if success else 1)
