"""
MongoDB Data Verification Script
Checks if session data is properly saved in MongoDB
"""

from pymongo import MongoClient
from datetime import datetime
import json

# MongoDB connection details (from your config)
MONGO_URI = "mongodb://samay2504:250403@localhost:27017/human_ai_co_create"
DATABASE_NAME = "human_ai_co_create"
COLLECTION_NAME = "stories"

def check_mongodb_data():
    """Check MongoDB for saved sessions"""
    try:
        # Connect to MongoDB
        print("🔌 Connecting to MongoDB...")
        client = MongoClient(MONGO_URI)
        
        # Get database and collection
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        
        # Test connection
        client.admin.command('ping')
        print("✅ MongoDB connection successful!\n")
        
        # Get all sessions
        print("📊 Fetching all sessions...")
        sessions = list(collection.find())
        
        print(f"📦 Found {len(sessions)} session(s) in MongoDB\n")
        
        if not sessions:
            print("⚠️  No sessions found in database")
            return
        
        # Display session details
        for i, session in enumerate(sessions, 1):
            print(f"{'='*80}")
            print(f"Session #{i}")
            print(f"{'='*80}")
            print(f"📝 Session ID: {session.get('session_id', 'N/A')}")
            print(f"👤 User ID: {session.get('user_id', session.get('metadata', {}).get('user_id', 'N/A'))}")
            print(f"📚 Topic: {session.get('topic', 'N/A')}")
            print(f"🕐 Created: {session.get('created_at', session.get('metadata', {}).get('created_at', 'N/A'))}")
            print(f"🕑 Last Modified: {session.get('last_modified', 'N/A')}")
            
            # Check content
            story_content = session.get('story_so_far', '')
            topic_content = session.get('topic_content', '')
            content = story_content or topic_content
            
            print(f"\n📄 Content Length: {len(content)} characters")
            if content:
                print(f"📝 Content Preview (first 200 chars):")
                print(f"   {content[:200]}...")
            else:
                print("⚠️  No content found")
            
            # Check metadata
            metadata = session.get('metadata', {})
            if metadata:
                print(f"\n🏷️  Metadata:")
                print(f"   - User ID: {metadata.get('user_id', 'N/A')}")
                print(f"   - Last Activity: {metadata.get('last_activity', 'N/A')}")
                print(f"   - Version: {metadata.get('version', 'N/A')}")
            
            # Check projections
            projections = session.get('projections', {})
            if projections and any(projections.values()):
                print(f"\n🌿 Projections:")
                for key, value in projections.items():
                    if value:
                        print(f"   - Branch {key}: {value.get('title', 'N/A')}")
            
            print()
        
        # Get most recent session with content
        print(f"\n{'='*80}")
        print("🔍 Most Recent Session with Content")
        print(f"{'='*80}")
        
        recent_session = collection.find_one(
            {
                "$or": [
                    {"story_so_far": {"$ne": ""}},
                    {"topic_content": {"$ne": ""}}
                ]
            },
            sort=[("last_modified", -1)]
        )
        
        if recent_session:
            print(f"📝 Session ID: {recent_session.get('session_id')}")
            print(f"👤 User ID: {recent_session.get('user_id', recent_session.get('metadata', {}).get('user_id', 'N/A'))}")
            content = recent_session.get('story_so_far', '') or recent_session.get('topic_content', '')
            print(f"📄 Content ({len(content)} chars):")
            print(f"   {content}")
        else:
            print("⚠️  No sessions with content found")
        
        # Close connection
        client.close()
        print("\n✅ MongoDB verification complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def check_with_pymongo():
    """Alternative check using pymongo (synchronous)"""
    try:
        from pymongo import MongoClient
        
        print("\n" + "="*80)
        print("Using PyMongo (synchronous) alternative check")
        print("="*80 + "\n")
        
        client = MongoClient(MONGO_URI)
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        
        # Count documents
        count = collection.count_documents({})
        print(f"📦 Total sessions: {count}")
        
        # Find sessions with content
        content_count = collection.count_documents({
            "$or": [
                {"story_so_far": {"$ne": ""}},
                {"topic_content": {"$ne": ""}}
            ]
        })
        print(f"📝 Sessions with content: {content_count}")
        
        # Get latest session
        latest = collection.find_one(sort=[("last_modified", -1)])
        if latest:
            print(f"\n🆕 Latest Session:")
            print(f"   Session ID: {latest.get('session_id')}")
            print(f"   User ID: {latest.get('user_id', latest.get('metadata', {}).get('user_id', 'N/A'))}")
            print(f"   Last Modified: {latest.get('last_modified')}")
            content = latest.get('story_so_far', '') or latest.get('topic_content', '')
            print(f"   Content Length: {len(content)} chars")
        
        client.close()
        
    except ImportError:
        print("⚠️  pymongo not installed, skipping synchronous check")
    except Exception as e:
        print(f"❌ PyMongo Error: {e}")

if __name__ == "__main__":
    print("="*80)
    print("MongoDB Session Data Verification")
    print("="*80 + "\n")
    
    # Run check
    check_mongodb_data()
    
    # Run additional sync check if available
    try:
        check_with_pymongo()
    except:
        pass
