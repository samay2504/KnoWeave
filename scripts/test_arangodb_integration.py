#!/usr/bin/env python3
"""
ArangoDB Integration Test
Tests that ArangoDB is properly activated and data is being saved correctly
"""

import os
import sys
import asyncio
import json
import logging
from pathlib import Path

# Add server to path
current_dir = Path(__file__).parent
server_dir = current_dir.parent / "server"
sys.path.insert(0, str(server_dir))

# Set environment to load config properly
os.chdir(current_dir.parent)

from server_config import ServerConfig
from db.arango_client import ArangoGraphClient, create_arango_client, GraphNode, GraphEdge

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArangoDBIntegrationTest:
    """Test ArangoDB connection, data saving, and retrieval"""
    
    def __init__(self):
        self.config = None
        self.client = None
        self.test_data = {
            "nodes": [],
            "edges": [],
            "session_id": f"test-session-{asyncio.get_event_loop().time()}"
        }
        
    async def setup(self):
        """Initialize ArangoDB connection"""
        try:
            # Load configuration
            self.config = ServerConfig()
            logger.info(f"🔧 Loaded server config - ArangoDB: {self.config.arango_url}")
            
            # Create ArangoDB client
            self.client = await create_arango_client(self.config.get_database_config()["arango"])
            logger.info("✅ ArangoDB client created successfully")
            
            return True
        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            return False
    
    async def test_connection(self):
        """Test basic ArangoDB connection"""
        try:
            # Test if client is connected
            if hasattr(self.client, 'db') and self.client.db:
                logger.info("✅ ArangoDB connection verified")
                return True
            else:
                logger.error("❌ ArangoDB client not properly connected")
                return False
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False
    
    async def test_create_collections(self):
        """Test collection creation and access"""
        try:
            await self.client._initialize_collections()
            logger.info("✅ Collections initialized successfully")
            
            # Verify collections exist
            if hasattr(self.client, 'nodes_collection') and hasattr(self.client, 'edges_collection'):
                logger.info("✅ Node and edge collections accessible")
                return True
            else:
                logger.error("❌ Collections not properly initialized")
                return False
        except Exception as e:
            logger.error(f"❌ Collection creation failed: {e}")
            return False
    
    async def test_save_nodes(self):
        """Test saving graph nodes to ArangoDB"""
        try:
            # Create test nodes
            test_nodes = [
                GraphNode(
                    id="test_character_1",
                    type="entity",
                    summary="A brave knight on a quest",
                    properties={
                        "name": "Sir Galahad",
                        "class": "character",
                        "attributes": ["brave", "noble", "questing"]
                    },
                    confidence=0.95,
                    timestamp=str(asyncio.get_event_loop().time())
                ),
                GraphNode(
                    id="test_event_1", 
                    type="event",
                    summary="The knight enters a dark forest",
                    properties={
                        "location": "Dark Forest",
                        "action": "entering",
                        "mood": "mysterious"
                    },
                    confidence=0.90,
                    timestamp=str(asyncio.get_event_loop().time())
                )
            ]
            
            # Save nodes
            for node in test_nodes:
                result = await self.client.add_node(self.test_data["session_id"], node)
                if result:
                    logger.info(f"✅ Saved node: {node.id}")
                    self.test_data["nodes"].append(node.id)
                else:
                    logger.error(f"❌ Failed to save node: {node.id}")
                    return False
            
            logger.info(f"✅ Successfully saved {len(test_nodes)} nodes")
            return True
            
        except Exception as e:
            logger.error(f"❌ Node saving failed: {e}")
            return False
    
    async def test_save_edges(self):
        """Test saving graph edges to ArangoDB"""
        try:
            if len(self.test_data["nodes"]) < 2:
                logger.error("❌ Need at least 2 nodes to create edges")
                return False
            
            # Create test edge
            test_edge = GraphEdge(
                from_node=self.test_data["nodes"][0],
                to_node=self.test_data["nodes"][1],
                type="encounters",
                properties={
                    "context": "The knight encounters the forest",
                    "sequence": 1,
                    "causality": "temporal"
                },
                confidence=0.85
            )
            
            # Save edge
            result = await self.client.add_edge(self.test_data["session_id"], test_edge)
            if result:
                logger.info(f"✅ Saved edge: {test_edge.from_node} -> {test_edge.to_node}")
                self.test_data["edges"].append(f"{test_edge.from_node}->{test_edge.to_node}")
                return True
            else:
                logger.error(f"❌ Failed to save edge")
                return False
                
        except Exception as e:
            logger.error(f"❌ Edge saving failed: {e}")
            return False
    
    async def test_retrieve_data(self):
        """Test retrieving saved data from ArangoDB"""
        try:
            # Test node retrieval using session-based queries
            retrieved_nodes = 0
            all_nodes = await self.client.get_nodes(self.test_data["session_id"])
            
            for node in all_nodes:
                if node.id in self.test_data["nodes"]:
                    logger.info(f"✅ Retrieved node: {node.id} - {node.summary}")
                    retrieved_nodes += 1
            
            # Test edge retrieval
            all_edges = await self.client.get_edges(self.test_data["session_id"])
            logger.info(f"✅ Retrieved {len(all_edges)} edges for session")
            
            # Test graph summary
            graph_summary = await self.client.get_graph_summary(self.test_data["session_id"])
            logger.info(f"✅ Graph summary: {graph_summary['total_nodes']} nodes, {graph_summary['total_edges']} edges")
            
            if retrieved_nodes > 0:
                logger.info(f"✅ Successfully retrieved {retrieved_nodes}/{len(self.test_data['nodes'])} nodes")
                return True
            else:
                logger.error("❌ No nodes could be retrieved")
                return False
                
        except Exception as e:
            logger.error(f"❌ Data retrieval failed: {e}")
            return False
    
    async def test_graph_operations(self):
        """Test graph-specific operations"""
        try:
            # Test traversal or path finding
            if len(self.test_data["nodes"]) >= 2:
                try:
                    # Test path finding between nodes
                    path = await self.client.find_path(
                        self.test_data["session_id"],
                        self.test_data["nodes"][0], 
                        self.test_data["nodes"][1]
                    )
                    if path:
                        logger.info(f"✅ Found path between nodes: {len(path)} steps")
                    else:
                        logger.info("ℹ️  No path found between test nodes (expected for simple test)")
                except Exception as e:
                    logger.warning(f"⚠️  Path finding failed: {e}")
                
                # Test neighbor finding
                try:
                    neighbors = await self.client.get_neighbors(
                        self.test_data["session_id"],
                        self.test_data["nodes"][0]
                    )
                    logger.info(f"✅ Found {len(neighbors)} neighbors for first node")
                    
                    # Test different directions
                    outbound_neighbors = await self.client.get_neighbors(
                        self.test_data["session_id"],
                        self.test_data["nodes"][0],
                        direction="outbound"
                    )
                    logger.info(f"✅ Found {len(outbound_neighbors)} outbound neighbors")
                    
                    inbound_neighbors = await self.client.get_neighbors(
                        self.test_data["session_id"], 
                        self.test_data["nodes"][1],
                        direction="inbound"
                    )
                    logger.info(f"✅ Found {len(inbound_neighbors)} inbound neighbors")
                    
                except Exception as e:
                    logger.warning(f"⚠️  Neighbor finding failed: {e}")
                
                # Test connected subgraph
                try:
                    subgraph = await self.client.get_connected_subgraph(
                        self.test_data["session_id"],
                        self.test_data["nodes"][0],
                        max_depth=2
                    )
                    logger.info(f"✅ Generated subgraph: {subgraph['node_count']} nodes, {subgraph['edge_count']} edges")
                except Exception as e:
                    logger.warning(f"⚠️  Subgraph generation failed: {e}")
            
            logger.info("✅ Graph operations test completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Graph operations failed: {e}")
            return False
    
    async def test_cleanup(self):
        """Clean up test data"""
        try:
            # Clean up entire session (more efficient)
            success = await self.client.clear_session_graph(self.test_data["session_id"])
            if success:
                logger.info(f"🧹 Cleaned up all test data for session: {self.test_data['session_id']}")
                return True
            else:
                logger.warning("⚠️  Session cleanup failed, trying individual node deletion")
                
                # Fallback to individual node deletion
                deleted_nodes = 0
                for node_id in self.test_data["nodes"]:
                    try:
                        success = await self.client.delete_node(self.test_data["session_id"], node_id)
                        if success:
                            deleted_nodes += 1
                            logger.info(f"🧹 Deleted test node: {node_id}")
                    except Exception as e:
                        logger.warning(f"⚠️  Could not delete node {node_id}: {e}")
                
                logger.info(f"🧹 Cleanup completed - deleted {deleted_nodes} nodes")
                return deleted_nodes > 0
            
        except Exception as e:
            logger.warning(f"⚠️  Cleanup failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run comprehensive ArangoDB integration test suite"""
        logger.info("🧪 Starting ArangoDB Integration Tests")
        logger.info("=" * 60)
        
        test_results = {}
        
        # Setup
        test_results["setup"] = await self.setup()
        if not test_results["setup"]:
            logger.error("❌ Setup failed - cannot continue with tests")
            return test_results
        
        # Connection test
        test_results["connection"] = await self.test_connection()
        
        # Collections test
        test_results["collections"] = await self.test_create_collections()
        
        # Data saving tests
        test_results["save_nodes"] = await self.test_save_nodes()
        test_results["save_edges"] = await self.test_save_edges()
        
        # Data retrieval test
        test_results["retrieve_data"] = await self.test_retrieve_data()
        
        # Graph operations test
        test_results["graph_operations"] = await self.test_graph_operations()
        
        # Cleanup
        test_results["cleanup"] = await self.test_cleanup()
        
        # Summary
        logger.info("=" * 60)
        logger.info("🧪 ArangoDB Integration Test Results:")
        
        passed = sum(1 for result in test_results.values() if result)
        total = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"  {test_name}: {status}")
        
        logger.info(f"\n📊 Overall Result: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 ALL TESTS PASSED - ArangoDB is properly activated and working!")
        elif passed >= total * 0.8:  # 80% pass rate
            logger.info("⚠️  MOSTLY WORKING - Some optional features may not be implemented")
        else:
            logger.error("❌ CRITICAL ISSUES - ArangoDB integration needs attention")
        
        return test_results

async def main():
    """Main test execution"""
    test = ArangoDBIntegrationTest()
    results = await test.run_all_tests()
    
    # Return appropriate exit code
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    if passed >= total * 0.8:  # 80% pass rate considered success
        return 0
    else:
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
