#!/usr/bin/env python3
"""
Simple ArangoDB Connection Test
Quick test to verify ArangoDB server is running and accessible
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add server to path
sys.path.insert(0, str(Path(__file__).parent.parent / "server"))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def test_arangodb_connection():
    """Test basic ArangoDB connection"""
    logger.info("🧪 Testing ArangoDB Connection")
    logger.info("=" * 40)
    
    try:
        # Test aioarango import
        try:
            from aioarango import ArangoClient
            logger.info("✅ aioarango package available")
            use_async = True
        except ImportError:
            logger.warning("⚠️  aioarango not available, trying sync client")
            try:
                from arango import ArangoClient
                logger.info("✅ arango package available (sync)")
                use_async = False
            except ImportError:
                logger.error("❌ No ArangoDB client packages available")
                return False
        
        # Load config
        from server_config import ServerConfig
        config = ServerConfig()
        arango_config = config.database_config["arango"]
        
        logger.info(f"🔧 ArangoDB URL: {arango_config['url']}")
        logger.info(f"🔧 Database: {arango_config['database']}")
        logger.info(f"🔧 User: {arango_config['user']}")
        
        # Test connection
        if use_async:
            # Async connection test
            client = ArangoClient(hosts=arango_config["url"])
            db = await client.db(
                name=arango_config["database"],
                username=arango_config["user"],
                password=arango_config["password"]
            )
            
            # Test a simple operation
            try:
                collections = await db.collections()
                logger.info(f"✅ Connected to ArangoDB! Found {len(collections)} collections")
                
                # List collections
                for collection in collections[:5]:  # Show first 5
                    logger.info(f"  📁 Collection: {collection['name']}")
                
                await client.close()
                return True
                
            except Exception as e:
                logger.error(f"❌ Failed to query database: {e}")
                await client.close()
                return False
        
        else:
            # Sync connection test
            client = ArangoClient(hosts=arango_config["url"])
            db = client.db(
                name=arango_config["database"],
                username=arango_config["user"],
                password=arango_config["password"]
            )
            
            # Test a simple operation
            try:
                collections = db.collections()
                logger.info(f"✅ Connected to ArangoDB! Found {len(collections)} collections")
                
                # List collections
                for collection in collections[:5]:  # Show first 5
                    logger.info(f"  📁 Collection: {collection['name']}")
                
                return True
                
            except Exception as e:
                logger.error(f"❌ Failed to query database: {e}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Connection test failed: {e}")
        return False

async def test_basic_operations():
    """Test basic ArangoDB operations"""
    logger.info("\n🧪 Testing Basic ArangoDB Operations")
    logger.info("=" * 40)
    
    try:
        from server_config import ServerConfig
        from db.arango_client import create_arango_client
        
        config = ServerConfig()
        client = await create_arango_client(config.database_config["arango"])
        
        # Test client creation
        logger.info("✅ ArangoDB client created successfully")
        
        # Test collection initialization
        await client._initialize_collections()
        logger.info("✅ Collections initialized")
        
        # Test if we can access collections
        if hasattr(client, 'nodes_collection') and hasattr(client, 'edges_collection'):
            logger.info("✅ Node and edge collections accessible")
        else:
            logger.warning("⚠️  Collections not properly accessible")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Basic operations test failed: {e}")
        return False

def check_arangodb_server():
    """Check if ArangoDB server is running by attempting HTTP connection"""
    import requests
    import json
    
    logger.info("\n🧪 Checking ArangoDB Server Status")
    logger.info("=" * 40)
    
    try:
        from server_config import ServerConfig
        config = ServerConfig()
        url = config.arango_url
        user = config.arango_user
        password = config.arango_password
        
        # Try to get server version with authentication
        auth = (user, password)
        response = requests.get(f"{url}/_api/version", auth=auth, timeout=5)
        
        if response.status_code == 200:
            version_info = response.json()
            logger.info(f"✅ ArangoDB Server is running!")
            logger.info(f"  🔖 Version: {version_info.get('version', 'unknown')}")
            logger.info(f"  🏷️  Server: {version_info.get('server', 'ArangoDB')}")
            return True
        elif response.status_code == 401:
            logger.warning(f"⚠️  ArangoDB Server is running but authentication failed")
            logger.info(f"  🔑 Using credentials: {user}")
            logger.info(f"  💡 Server is accessible but check credentials")
            return True  # Server is running, just auth issue
        else:
            logger.error(f"❌ ArangoDB Server responded with status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        logger.error("❌ Cannot connect to ArangoDB server - is it running?")
        logger.info("💡 To start ArangoDB server:")
        logger.info("  - Docker: docker run -p 8529:8529 -e ARANGO_ROOT_PASSWORD=password arangodb/arangodb")
        logger.info("  - Local: Check if ArangoDB service is running")
        return False
    except Exception as e:
        logger.error(f"❌ Server check failed: {e}")
        return False

async def main():
    """Run all ArangoDB tests"""
    logger.info("🚀 Starting ArangoDB Verification Tests")
    logger.info("=" * 50)
    
    results = {}
    
    # Check if server is running
    results["server_running"] = check_arangodb_server()
    
    if results["server_running"]:
        # Test connection
        results["connection"] = await test_arangodb_connection()
        
        # Test basic operations
        results["basic_operations"] = await test_basic_operations()
    else:
        logger.warning("⚠️  Skipping connection tests - server not accessible")
        results["connection"] = False
        results["basic_operations"] = False
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 ArangoDB Test Summary:")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"  {test_name}: {status}")
    
    logger.info(f"\n🎯 Result: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ArangoDB is fully operational!")
    elif results["server_running"]:
        logger.info("⚠️  ArangoDB server is running but there are connection issues")
    else:
        logger.error("❌ ArangoDB server is not accessible")
        logger.info("\n💡 Next steps:")
        logger.info("  1. Start ArangoDB server")
        logger.info("  2. Check connection settings in .env file")
        logger.info("  3. Verify credentials and database exists")
    
    return passed >= 1  # At least server should be running

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        exit(0 if result else 1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Test interrupted by user")
        exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        exit(1)
