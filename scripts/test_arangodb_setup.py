#!/usr/bin/env python3
"""
ArangoDB Setup and Test
Set up ArangoDB database and test data persistence
"""

import asyncio
import logging
import sys
import json
from pathlib import Path

# Add server to path
sys.path.insert(0, str(Path(__file__).parent.parent / "server"))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def setup_arangodb():
    """Set up ArangoDB database and collections"""
    logger.info("🔧 Setting up ArangoDB database...")
    
    try:
        # Try aioarango first
        try:
            from aioarango import ArangoClient
            use_async = True
            logger.info("✅ Using aioarango (async)")
        except ImportError:
            from arango import ArangoClient
            use_async = False
            logger.info("✅ Using arango (sync)")
        
        # Load config
        from server_config import ServerConfig
        config = ServerConfig()
        arango_config = config.get_database_config()["arango"]
        
        logger.info(f"🔗 Connecting to: {arango_config['url']}")
        logger.info(f"👤 User: {arango_config['user']}")
        logger.info(f"🗄️  Target database: {arango_config['database']}")
        
        if use_async:
            # Async setup
            client = ArangoClient(hosts=arango_config["url"])
            
            # First connect to _system database to create our database
            try:
                sys_db = await client.db(
                    name="_system",
                    username=arango_config["user"],
                    password=arango_config["password"]
                )
                logger.info("✅ Connected to _system database")
                
                # Check if our database exists
                databases = await sys_db.databases()
                db_names = [db['name'] for db in databases]
                
                if arango_config['database'] not in db_names:
                    # Create our database
                    await sys_db.create_database(
                        name=arango_config['database'],
                        users=[{
                            'username': arango_config['user'],
                            'password': arango_config['password'],
                            'active': True
                        }]
                    )
                    logger.info(f"✅ Created database: {arango_config['database']}")
                else:
                    logger.info(f"✅ Database already exists: {arango_config['database']}")
                
                # Now connect to our database
                db = await client.db(
                    name=arango_config['database'],
                    username=arango_config['user'],
                    password=arango_config['password']
                )
                logger.info(f"✅ Connected to database: {arango_config['database']}")
                
                # Create collections
                collections_to_create = ['nodes', 'edges']
                
                for collection_name in collections_to_create:
                    try:
                        if not await db.has_collection(collection_name):
                            if collection_name == 'edges':
                                await db.create_collection(collection_name, edge=True)
                                logger.info(f"✅ Created edge collection: {collection_name}")
                            else:
                                await db.create_collection(collection_name)
                                logger.info(f"✅ Created document collection: {collection_name}")
                        else:
                            logger.info(f"✅ Collection already exists: {collection_name}")
                    except Exception as e:
                        logger.error(f"❌ Failed to create collection {collection_name}: {e}")
                
                await client.close()
                return True
                
            except Exception as e:
                logger.error(f"❌ Database setup failed: {e}")
                await client.close()
                return False
        
        else:
            # Sync setup (fallback)
            client = ArangoClient(hosts=arango_config["url"])
            
            # Connect to _system database
            sys_db = client.db(
                name="_system",
                username=arango_config["user"],
                password=arango_config["password"]
            )
            logger.info("✅ Connected to _system database (sync)")
            
            # Check if our database exists
            databases = sys_db.databases()
            db_names = [db['name'] for db in databases]
            
            if arango_config['database'] not in db_names:
                # Create our database
                sys_db.create_database(
                    name=arango_config['database'],
                    users=[{
                        'username': arango_config['user'],
                        'password': arango_config['password'],
                        'active': True
                    }]
                )
                logger.info(f"✅ Created database: {arango_config['database']}")
            else:
                logger.info(f"✅ Database already exists: {arango_config['database']}")
            
            # Connect to our database
            db = client.db(
                name=arango_config['database'],
                username=arango_config['user'],
                password=arango_config['password']
            )
            logger.info(f"✅ Connected to database: {arango_config['database']}")
            
            # Create collections
            collections_to_create = ['nodes', 'edges']
            
            for collection_name in collections_to_create:
                try:
                    if not db.has_collection(collection_name):
                        if collection_name == 'edges':
                            db.create_collection(collection_name, edge=True)
                            logger.info(f"✅ Created edge collection: {collection_name}")
                        else:
                            db.create_collection(collection_name)
                            logger.info(f"✅ Created document collection: {collection_name}")
                    else:
                        logger.info(f"✅ Collection already exists: {collection_name}")
                except Exception as e:
                    logger.error(f"❌ Failed to create collection {collection_name}: {e}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        return False

async def test_data_persistence():
    """Test that data can be saved and retrieved from ArangoDB"""
    logger.info("\n🧪 Testing Data Persistence...")
    
    try:
        from db.arango_client import create_arango_client, GraphNode, GraphEdge
        from server_config import ServerConfig
        
        config = ServerConfig()
        client = await create_arango_client(config.get_database_config()["arango"])
        
        # Test data
        test_session_id = "test-session-arango-001"
        
        # Create test nodes
        test_nodes = [
            GraphNode(
                id="char_001",
                type="entity",
                summary="A brave knight named Sir Galahad",
                properties={
                    "name": "Sir Galahad",
                    "type": "character",
                    "session_id": test_session_id,
                    "attributes": ["brave", "noble", "questing"]
                },
                confidence=0.95
            ),
            GraphNode(
                id="event_001",
                type="event", 
                summary="The knight enters a mysterious forest",
                properties={
                    "location": "Dark Forest",
                    "action": "entering",
                    "session_id": test_session_id,
                    "mood": "mysterious"
                },
                confidence=0.90
            )
        ]
        
        # Save nodes
        saved_nodes = []
        for node in test_nodes:
            try:
                result = await client.save_node(node)
                if result:
                    logger.info(f"✅ Saved node: {node.id} - {node.summary}")
                    saved_nodes.append(node.id)
                else:
                    logger.error(f"❌ Failed to save node: {node.id}")
            except Exception as e:
                logger.error(f"❌ Error saving node {node.id}: {e}")
        
        # Create test edge
        if len(saved_nodes) >= 2:
            test_edge = GraphEdge(
                from_node=saved_nodes[0],
                to_node=saved_nodes[1],
                relationship_type="encounters",
                properties={
                    "context": "The knight encounters the forest",
                    "session_id": test_session_id,
                    "sequence": 1
                },
                confidence=0.85
            )
            
            try:
                result = await client.save_edge(test_edge)
                if result:
                    logger.info(f"✅ Saved edge: {test_edge.from_node} -> {test_edge.to_node}")
                else:
                    logger.error("❌ Failed to save edge")
            except Exception as e:
                logger.error(f"❌ Error saving edge: {e}")
        
        # Test retrieval
        retrieved_count = 0
        for node_id in saved_nodes:
            try:
                node = await client.get_node(node_id)
                if node:
                    logger.info(f"✅ Retrieved node: {node.id} - {node.summary}")
                    retrieved_count += 1
                else:
                    logger.warning(f"⚠️  Could not retrieve node: {node_id}")
            except Exception as e:
                logger.error(f"❌ Error retrieving node {node_id}: {e}")
        
        # Summary
        logger.info(f"\n📊 Data Persistence Results:")
        logger.info(f"  Nodes saved: {len(saved_nodes)}")
        logger.info(f"  Nodes retrieved: {retrieved_count}")
        
        success = len(saved_nodes) > 0 and retrieved_count > 0
        
        if success:
            logger.info("✅ Data persistence test PASSED")
        else:
            logger.error("❌ Data persistence test FAILED")
        
        # Cleanup test data
        for node_id in saved_nodes:
            try:
                await client.delete_node(node_id)
                logger.info(f"🧹 Cleaned up node: {node_id}")
            except Exception as e:
                logger.warning(f"⚠️  Could not clean up node {node_id}: {e}")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Data persistence test failed: {e}")
        return False

async def main():
    """Main test execution"""
    logger.info("🚀 ArangoDB Setup and Data Persistence Test")
    logger.info("=" * 50)
    
    # Setup database
    setup_success = await setup_arangodb()
    
    if setup_success:
        # Test data persistence
        persistence_success = await test_data_persistence()
        
        logger.info("\n" + "=" * 50)
        logger.info("📊 Final Results:")
        logger.info(f"  Database Setup: {'✅ PASS' if setup_success else '❌ FAIL'}")
        logger.info(f"  Data Persistence: {'✅ PASS' if persistence_success else '❌ FAIL'}")
        
        if setup_success and persistence_success:
            logger.info("\n🎉 ArangoDB is properly activated and data persistence works!")
            return True
        else:
            logger.error("\n❌ Some tests failed - check configuration")
            return False
    else:
        logger.error("\n❌ Database setup failed - cannot test persistence")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        exit(1)
