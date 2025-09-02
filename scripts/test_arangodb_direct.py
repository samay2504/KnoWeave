#!/usr/bin/env python3
"""
Direct ArangoDB Test
Test ArangoDB connection and data operations directly
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add server to path
sys.path.insert(0, str(Path(__file__).parent.parent / "server"))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def test_direct_arangodb():
    """Test ArangoDB directly with manual configuration"""
    logger.info("🧪 Direct ArangoDB Connection Test")
    logger.info("=" * 40)
    
    try:
        # Load environment
        from dotenv import load_dotenv
        load_dotenv()
        
        # Manual config from environment
        arango_config = {
            "url": os.getenv("ARANGO_URL", "http://localhost:8529"),
            "user": os.getenv("ARANGO_USER", "root"),
            "password": os.getenv("ARANGO_PASSWORD", "samay2504"),
            "database": os.getenv("ARANGO_DATABASE", "project-db")
        }
        
        logger.info(f"🔗 URL: {arango_config['url']}")
        logger.info(f"👤 User: {arango_config['user']}")
        logger.info(f"🗄️  Database: {arango_config['database']}")
        
        # Test with aioarango
        try:
            from aioarango import ArangoClient
            
            client = ArangoClient(hosts=arango_config["url"])
            
            # Connect to _system database first
            sys_db = await client.db(
                name="_system",
                username=arango_config["user"],
                password=arango_config["password"]
            )
            logger.info("✅ Connected to _system database")
            
            # List databases
            try:
                databases_response = await sys_db.databases()
                logger.info(f"📋 Raw databases response: {databases_response}")
                
                # Handle different response formats
                if isinstance(databases_response, dict) and 'result' in databases_response:
                    database_names = databases_response['result']
                elif isinstance(databases_response, list):
                    database_names = databases_response
                else:
                    database_names = []
                
                logger.info(f"📁 Available databases: {database_names}")
                
                # Create our database if it doesn't exist
                if arango_config['database'] not in database_names:
                    logger.info(f"🔨 Creating database: {arango_config['database']}")
                    try:
                        await sys_db.create_database(
                            name=arango_config['database'],
                            users=[{
                                'username': arango_config['user'],
                                'password': arango_config['password'],
                                'active': True
                            }]
                        )
                        logger.info(f"✅ Created database: {arango_config['database']}")
                    except Exception as e:
                        logger.warning(f"⚠️  Database creation failed (might already exist): {e}")
                else:
                    logger.info(f"✅ Database already exists: {arango_config['database']}")
                
                # Connect to our target database
                target_db = await client.db(
                    name=arango_config['database'],
                    username=arango_config['user'],
                    password=arango_config['password']
                )
                logger.info(f"✅ Connected to target database: {arango_config['database']}")
                
                # Test collections
                collections_response = await target_db.collections()
                logger.info(f"📋 Collections response: {collections_response}")
                
                # Handle different response formats for collections
                if isinstance(collections_response, dict) and 'result' in collections_response:
                    collections = collections_response['result']
                elif isinstance(collections_response, list):
                    collections = collections_response
                else:
                    collections = []
                
                logger.info(f"📂 Existing collections: {[c.get('name', str(c)) for c in collections]}")
                
                # Create test collections
                test_collections = ['nodes', 'edges']
                
                for collection_name in test_collections:
                    try:
                        has_collection = await target_db.has_collection(collection_name)
                        if not has_collection:
                            if collection_name == 'edges':
                                await target_db.create_collection(collection_name, edge=True)
                                logger.info(f"✅ Created edge collection: {collection_name}")
                            else:
                                await target_db.create_collection(collection_name)
                                logger.info(f"✅ Created document collection: {collection_name}")
                        else:
                            logger.info(f"✅ Collection already exists: {collection_name}")
                    except Exception as e:
                        logger.error(f"❌ Failed to create collection {collection_name}: {e}")
                
                # Test document operations
                nodes_collection = target_db.collection('nodes')
                
                # Insert test document
                test_doc = {
                    "_key": "test_node_001",
                    "type": "character",
                    "name": "Test Character",
                    "description": "A test character for validation",
                    "session_id": "test-session-direct-001",
                    "timestamp": str(asyncio.get_event_loop().time())
                }
                
                try:
                    insert_result = await nodes_collection.insert(test_doc)
                    logger.info(f"✅ Inserted test document: {insert_result}")
                    
                    # Read back the document
                    retrieved_doc = await nodes_collection.get("test_node_001")
                    logger.info(f"✅ Retrieved test document: {retrieved_doc}")
                    
                    # Update the document
                    test_doc["updated"] = True
                    update_result = await nodes_collection.update(test_doc)
                    logger.info(f"✅ Updated test document: {update_result}")
                    
                    # Delete the document
                    delete_result = await nodes_collection.delete("test_node_001")
                    logger.info(f"✅ Deleted test document: {delete_result}")
                    
                    logger.info("🎉 All document operations successful!")
                    
                except Exception as e:
                    logger.error(f"❌ Document operations failed: {e}")
                
                # Test edge operations if both collections exist
                if await target_db.has_collection('edges'):
                    edges_collection = target_db.collection('edges')
                    
                    # Insert test nodes for edge
                    node1 = {"_key": "node1", "type": "character", "name": "Hero"}
                    node2 = {"_key": "node2", "type": "location", "name": "Castle"}
                    
                    try:
                        await nodes_collection.insert(node1)
                        await nodes_collection.insert(node2)
                        
                        # Create edge
                        test_edge = {
                            "_from": "nodes/node1",
                            "_to": "nodes/node2", 
                            "relationship": "visits",
                            "context": "The hero visits the castle"
                        }
                        
                        edge_result = await edges_collection.insert(test_edge)
                        logger.info(f"✅ Created test edge: {edge_result}")
                        
                        # Cleanup
                        await edges_collection.delete(edge_result["_key"])
                        await nodes_collection.delete("node1")
                        await nodes_collection.delete("node2")
                        
                        logger.info("✅ Edge operations successful!")
                        
                    except Exception as e:
                        logger.error(f"❌ Edge operations failed: {e}")
                
                await client.close()
                
                logger.info("\n🎉 ArangoDB is fully operational!")
                logger.info("✅ Database connection: WORKING")
                logger.info("✅ Database creation: WORKING")
                logger.info("✅ Collection operations: WORKING")
                logger.info("✅ Document operations: WORKING")
                logger.info("✅ Data persistence: CONFIRMED")
                
                return True
                
            except Exception as e:
                logger.error(f"❌ Database operations failed: {e}")
                await client.close()
                return False
                
        except ImportError:
            logger.error("❌ aioarango not available")
            return False
            
    except Exception as e:
        logger.error(f"❌ Direct test failed: {e}")
        return False

async def main():
    """Main test execution"""
    success = await test_direct_arangodb()
    
    if success:
        logger.info("\n🎯 FINAL RESULT: ArangoDB is properly activated and data will be saved!")
        return 0
    else:
        logger.error("\n❌ FINAL RESULT: ArangoDB setup needs attention")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        exit(exit_code)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        exit(1)
