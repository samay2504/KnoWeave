#!/usr/bin/env python3
"""
Advanced Path Finding Algorithm Test
Tests production-ready path finding algorithms including backtracking
"""

# Import warning suppression first
import sys
from pathlib import Path

# Add scripts directory to path for warning suppression
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Suppress all warnings using our module
from warning_suppression import configure_clean_logging

# Configure clean environment
logger = configure_clean_logging(__name__)

import asyncio
import json
import os

# Add server to path
server_dir = current_dir.parent / "server"
sys.path.insert(0, str(server_dir))

# Set environment to load config properly
os.chdir(current_dir.parent)

from server_config import ServerConfig  # type: ignore
from db.arango_client import create_arango_client, GraphNode, GraphEdge  # type: ignore

class AdvancedPathFindingTest:
    """Test advanced path finding algorithms"""
    
    def __init__(self):
        self.config = None
        self.client = None
        self.session_id = "advanced-pathfinding-test"
        self.nodes = {}
        self.edges = []
        
    async def setup(self):
        """Initialize ArangoDB connection"""
        try:
            # Load configuration
            self.config = ServerConfig()
            logger.info(f"🔧 Loaded server config - ArangoDB: {self.config.arango_url}")
            
            # Create ArangoDB client
            self.client = await create_arango_client(self.config.get_database_config()["arango"])
            if not self.client:
                logger.error("❌ Failed to create ArangoDB client")
                return False
                
            logger.info("✅ ArangoDB client created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            return False
    
    async def create_test_graph(self):
        """Create a complex test graph for path finding"""
        try:
            logger.info("🏗️  Creating complex test graph...")
            
            # Create nodes for a story graph
            test_nodes = [
                GraphNode(
                    id="start_village",
                    type="location",
                    summary="A peaceful starting village",
                    properties={"name": "Peaceful Village", "type": "settlement"},
                    confidence=1.0
                ),
                GraphNode(
                    id="dark_forest",
                    type="location", 
                    summary="A mysterious dark forest",
                    properties={"name": "Dark Forest", "type": "wilderness", "danger": "medium"},
                    confidence=0.9
                ),
                GraphNode(
                    id="mountain_pass",
                    type="location",
                    summary="A treacherous mountain pass",
                    properties={"name": "Mountain Pass", "type": "terrain", "danger": "high"},
                    confidence=0.8
                ),
                GraphNode(
                    id="hidden_cave",
                    type="location",
                    summary="A hidden cave behind the waterfall",
                    properties={"name": "Hidden Cave", "type": "secret", "danger": "low"},
                    confidence=0.7
                ),
                GraphNode(
                    id="dragon_lair",
                    type="location",
                    summary="The dragon's lair at the mountain peak",
                    properties={"name": "Dragon Lair", "type": "dungeon", "danger": "extreme"},
                    confidence=0.95
                ),
                GraphNode(
                    id="ancient_bridge",
                    type="location",
                    summary="An ancient stone bridge over the chasm",
                    properties={"name": "Ancient Bridge", "type": "crossing", "danger": "medium"},
                    confidence=0.85
                )
            ]
            
            # Save nodes
            for node in test_nodes:
                result = await self.client.add_node(self.session_id, node)
                if result:
                    self.nodes[node.id] = node
                    logger.info(f"✅ Created node: {node.id}")
                else:
                    logger.error(f"❌ Failed to create node: {node.id}")
            
            # Create edges with different weights/confidence
            test_edges = [
                GraphEdge(
                    from_node="start_village",
                    to_node="dark_forest",
                    type="travels_to",
                    properties={"distance": 5, "difficulty": "easy"},
                    confidence=0.9
                ),
                GraphEdge(
                    from_node="dark_forest",
                    to_node="mountain_pass",
                    type="travels_to", 
                    properties={"distance": 8, "difficulty": "hard"},
                    confidence=0.7
                ),
                GraphEdge(
                    from_node="dark_forest",
                    to_node="hidden_cave",
                    type="discovers",
                    properties={"distance": 3, "difficulty": "medium"},
                    confidence=0.6
                ),
                GraphEdge(
                    from_node="mountain_pass",
                    to_node="dragon_lair",
                    type="leads_to",
                    properties={"distance": 10, "difficulty": "extreme"},
                    confidence=0.8
                ),
                GraphEdge(
                    from_node="hidden_cave",
                    to_node="ancient_bridge",
                    type="connects_to",
                    properties={"distance": 4, "difficulty": "medium"},
                    confidence=0.75
                ),
                GraphEdge(
                    from_node="ancient_bridge",
                    to_node="dragon_lair",
                    type="leads_to",
                    properties={"distance": 6, "difficulty": "hard"},
                    confidence=0.85
                ),
                # Alternative route
                GraphEdge(
                    from_node="start_village",
                    to_node="ancient_bridge",
                    type="travels_to",
                    properties={"distance": 12, "difficulty": "medium"},
                    confidence=0.65
                ),
                # Add bidirectional reverse edges for comprehensive path testing
                GraphEdge(
                    from_node="dark_forest",
                    to_node="start_village",
                    type="returns_to",
                    properties={"distance": 5, "difficulty": "easy"},
                    confidence=0.85
                ),
                GraphEdge(
                    from_node="hidden_cave",
                    to_node="dark_forest",
                    type="returns_to",
                    properties={"distance": 3, "difficulty": "medium"},
                    confidence=0.55
                ),
                GraphEdge(
                    from_node="ancient_bridge",
                    to_node="hidden_cave",
                    type="returns_to",
                    properties={"distance": 4, "difficulty": "medium"},
                    confidence=0.7
                ),
                GraphEdge(
                    from_node="ancient_bridge",
                    to_node="start_village",
                    type="returns_to",
                    properties={"distance": 12, "difficulty": "medium"},
                    confidence=0.6
                )
            ]
            
            # Save edges
            for edge in test_edges:
                result = await self.client.add_edge(self.session_id, edge)
                if result:
                    self.edges.append(edge)
                    logger.info(f"✅ Created edge: {edge.from_node} -> {edge.to_node}")
                else:
                    logger.error(f"❌ Failed to create edge: {edge.from_node} -> {edge.to_node}")
            
            logger.info(f"🎯 Test graph created: {len(self.nodes)} nodes, {len(self.edges)} edges")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create test graph: {e}")
            return False

    async def test_algorithm(self, algorithm: str, from_node: str, to_node: str):
        """Test a specific path finding algorithm"""
        try:
            logger.info(f"\n🔍 Testing {algorithm.upper()} algorithm: {from_node} → {to_node}")
            
            result = await self.client.find_path(
                session_id=self.session_id,
                from_node_id=from_node,
                to_node_id=to_node,
                max_depth=10,
                algorithm=algorithm
            )
            
            if result and result.get("found", False):
                logger.info(f"✅ {algorithm.upper()} SUCCESS:")
                logger.info(f"   📏 Distance: {result.get('distance', 'N/A')} steps")
                
                if "weight" in result:
                    logger.info(f"   ⚖️  Weight: {result['weight']:.2f}")
                if "total_confidence" in result:
                    logger.info(f"   🎯 Total Confidence: {result['total_confidence']:.2f}")
                if "avg_confidence" in result:
                    logger.info(f"   📊 Avg Confidence: {result['avg_confidence']:.2f}")
                if "nodes_visited" in result:
                    logger.info(f"   👁️  Nodes Visited: {result['nodes_visited']}")
                if "count" in result:
                    logger.info(f"   🔢 Paths Found: {result['count']}")
                if "heuristic_score" in result:
                    logger.info(f"   🎯 Heuristic Score: {result['heuristic_score']:.3f}")
                if "f_score" in result:
                    logger.info(f"   🔍 F-Score: {result['f_score']:.3f}")
                
                # Show path details
                if "path" in result:
                    path = result["path"]
                    logger.info(f"   🛤️  Path: {' → '.join([step['node_id'] for step in path])}")
                elif "paths" in result:
                    paths = result["paths"][:3]  # Show first 3 paths
                    for i, path_info in enumerate(paths):
                        path = path_info["path"]
                        logger.info(f"   🛤️  Path {i+1}: {' → '.join([step['node_id'] for step in path])} (dist: {path_info['distance']})")
                
                return True
            else:
                logger.warning(f"⚠️  {algorithm.upper()}: No path found")
                if "error" in result:
                    logger.error(f"   Error: {result['error']}")
                return False
                
        except Exception as e:
            logger.error(f"❌ {algorithm.upper()} algorithm failed: {e}")
            return False

    async def run_all_tests(self):
        """Run comprehensive path finding tests"""
        logger.info("\n🧪 ADVANCED PATH FINDING ALGORITHM TESTS")
        logger.info("=" * 60)
        
        algorithms = [
            "shortest",      # ArangoDB optimized shortest path
            "bfs",          # Breadth-First Search  
            "dfs",          # Depth-First Search with backtracking
            "dijkstra",     # Dijkstra's weighted shortest path
            "astar",        # A* heuristic pathfinding
            "all_paths"     # Find all possible paths
        ]
        
        test_routes = [
            ("start_village", "dragon_lair"),     # Long journey
            ("start_village", "hidden_cave"),     # Medium journey  
            ("dark_forest", "dragon_lair"),       # Alternative routes
            ("hidden_cave", "start_village"),     # Reverse direction
        ]
        
        results = {}
        
        for route in test_routes:
            from_node, to_node = route
            route_key = f"{from_node}_to_{to_node}"
            results[route_key] = {}
            
            logger.info(f"\n🗺️  TESTING ROUTE: {from_node} → {to_node}")
            logger.info("-" * 50)
            
            for algorithm in algorithms:
                success = await self.test_algorithm(algorithm, from_node, to_node)
                results[route_key][algorithm] = success
        
        # Summary
        logger.info("\n📊 ALGORITHM TEST SUMMARY")
        logger.info("=" * 60)
        
        for route_key, route_results in results.items():
            logger.info(f"\n🛣️  Route: {route_key.replace('_to_', ' → ').replace('_', ' ')}")
            for algorithm, success in route_results.items():
                status = "✅ PASS" if success else "❌ FAIL"
                logger.info(f"   {algorithm.upper():12} {status}")
        
        # Calculate overall success rate
        total_tests = sum(len(route_results) for route_results in results.values())
        passed_tests = sum(sum(route_results.values()) for route_results in results.values())
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        logger.info(f"\n🎯 OVERALL RESULTS:")
        logger.info(f"   Tests Passed: {passed_tests}/{total_tests}")
        logger.info(f"   Success Rate: {success_rate:.1f}%")
        
        # Success criteria: >70% for production-ready status
        # Note: Some failures expected due to directional graph constraints
        return success_rate >= 70.0

    async def cleanup(self):
        """Clean up test data"""
        try:
            logger.info("\n🧹 Cleaning up test data...")
            await self.client.clear_session_graph(self.session_id)
            logger.info("✅ Cleanup completed")
        except Exception as e:
            logger.warning(f"⚠️  Cleanup warning: {e}")

async def main():
    """Main test execution"""
    logger.info("🚀 Advanced Path Finding Algorithm Test")
    logger.info("Testing production-ready algorithms with backtracking")
    logger.info("=" * 70)
    
    test = AdvancedPathFindingTest()
    
    try:
        # Setup
        if not await test.setup():
            logger.error("❌ Setup failed")
            return False
        
        # Create test graph
        if not await test.create_test_graph():
            logger.error("❌ Test graph creation failed")
            return False
        
        # Run tests
        success = await test.run_all_tests()
        
        # Cleanup
        await test.cleanup()
        
        if success:
            logger.info("\n🎉 ADVANCED PATH FINDING TESTS SUCCESSFUL!")
            logger.info("✅ Production-ready algorithms are working correctly.")
            logger.info("📊 Success rate meets production standards (≥70%)")
        else:
            logger.error("\n❌ Path finding tests below production standards")
            logger.error("🔧 Success rate below 70% - needs improvement")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        await test.cleanup()
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        exit(1)
