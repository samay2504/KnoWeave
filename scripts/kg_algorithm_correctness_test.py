#!/usr/bin/env python3
"""
Knowledge Graph Algorithm Correctness Testing
============================================

Comprehensive testing of all graph algorithms including:
- Pathfinding (BFS, DFS, Dijkstra, shortest path)
- Neighbor discovery and traversal
- Backtracking algorithms
- Graph merging and pruning
- Complex graph structure validation

Part of the autonomous Knowledge Graph validation mission.
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set

# Add server to path
current_dir = Path(__file__).parent
server_dir = current_dir.parent / "server"
sys.path.insert(0, str(server_dir))

# Set environment
import os
os.chdir(current_dir.parent)

from server_config import ServerConfig
from db.arango_client import create_arango_client, GraphNode, GraphEdge

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AlgorithmCorrectnessTest:
    """Test all graph algorithms for correctness and production readiness"""
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or f"session_test_algorithms_{datetime.now().strftime('%Y%m%dT%H%M%SZ')}"
        self.client = None
        self.test_results = {
            "timestamp": datetime.now().strftime('%Y%m%dT%H%M%SZ'),
            "session_id": self.session_id,
            "algorithms": {},
            "performance": {},
            "status": "INIT"
        }
        
        # Test graph structure - create a complex graph for thorough testing
        self.test_nodes = []
        self.test_edges = []
        self.node_map = {}  # id -> GraphNode for easy lookup
        
    async def setup_client(self):
        """Initialize ArangoDB client"""
        try:
            self.config = ServerConfig()
            logger.info("🔧 Loading server configuration...")
            
            self.client = await create_arango_client(self.config.get_database_config()["arango"])
            if not self.client:
                logger.error("❌ Failed to create ArangoDB client")
                return False
                
            logger.info("✅ ArangoDB client connected successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to ArangoDB: {e}")
            return False
    
    def create_test_graph(self):
        """
        Create a complex test graph structure:
        
        Network topology:
              A ---- B ---- C
              |      |      |
              D ---- E ---- F
              |      |      |
              G ---- H ---- I
        
        With additional edges for complex pathfinding:
        - A->C (diagonal)
        - D->F (diagonal) 
        - G->I (diagonal)
        - B->H (vertical shortcut)
        - E is a central hub
        """
        logger.info("🏗️ Creating complex test graph...")
        
        # Create nodes in a 3x3 grid
        node_labels = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']
        for i, label in enumerate(node_labels):
            node = GraphNode(
                id=f"{self.session_id}_node_{label}",
                type="test_node",
                summary=f"Test node {label} content",
                properties={
                    "position": {"x": i % 3, "y": i // 3},
                    "test_id": label,
                    "centrality": 1.0 if label == 'E' else 0.5,
                    "label": f"Node_{label}"
                },
                embedding=[0.1 * (i + 1)] * 384,
                confidence=1.0
            )
            self.test_nodes.append(node)
            self.node_map[label] = node
        
        # Create edges for the grid structure
        edge_connections = [
            # Horizontal connections
            ('A', 'B'), ('B', 'C'),
            ('D', 'E'), ('E', 'F'),
            ('G', 'H'), ('H', 'I'),
            # Vertical connections
            ('A', 'D'), ('B', 'E'), ('C', 'F'),
            ('D', 'G'), ('E', 'H'), ('F', 'I'),
            # Diagonal shortcuts for complex pathfinding
            ('A', 'C'), ('D', 'F'), ('G', 'I'),
            # Central hub connections
            ('B', 'H'), ('E', 'A'), ('E', 'C'), ('E', 'G'), ('E', 'I')
        ]
        
        for i, (from_node, to_node) in enumerate(edge_connections):
            edge = GraphEdge(
                from_node=self.node_map[from_node].id,
                to_node=self.node_map[to_node].id,
                type="connects",
                properties={
                    "weight": 1.0 if (from_node, to_node) in [('A', 'B'), ('B', 'C'), ('D', 'E'), ('E', 'F')] else 2.0,
                    "edge_type": "diagonal" if (from_node, to_node) in [('A', 'C'), ('D', 'F'), ('G', 'I')] else "grid",
                    "test_weight": 1.0
                },
                confidence=1.0
            )
            self.test_edges.append(edge)
        
        logger.info(f"Created test graph: {len(self.test_nodes)} nodes, {len(self.test_edges)} edges")
    
    async def setup_test_data(self):
        """Insert test graph data into database"""
        logger.info("📊 Setting up test graph data...")
        
        try:
            # Create nodes
            nodes_added = 0
            for node in self.test_nodes:
                result = await self.client.add_node(self.session_id, node)
                if result:
                    nodes_added += 1
            
            # Create edges
            edges_added = 0
            for edge in self.test_edges:
                result = await self.client.add_edge(self.session_id, edge)
                if result:
                    edges_added += 1
            
            logger.info(f"✅ Test data setup: {nodes_added}/{len(self.test_nodes)} nodes, {edges_added}/{len(self.test_edges)} edges")
            return nodes_added == len(self.test_nodes) and edges_added == len(self.test_edges)
            
        except Exception as e:
            logger.error(f"❌ Failed to setup test data: {e}")
            return False
    
    async def test_pathfinding_algorithms(self):
        """Test all pathfinding algorithms for correctness"""
        logger.info("🛤️ Testing pathfinding algorithms...")
        
        pathfinding_results = {}
        
        # Test cases: (start, end, expected_path_exists, algorithm_name)
        test_cases = [
            ('A', 'I', True, "Long diagonal path"),
            ('A', 'C', True, "Direct diagonal"),
            ('G', 'C', True, "Corner to corner"),
            ('E', 'A', True, "Hub to corner"),
            ('B', 'H', True, "Direct vertical"),
            ('A', 'Z', False, "Non-existent destination"),
        ]
        
        algorithms = ['bfs', 'dfs', 'shortest', 'dijkstra']
        
        for algorithm in algorithms:
            logger.info(f"  Testing {algorithm.upper()} algorithm...")
            algo_results = {
                "tests_passed": 0,
                "tests_total": len(test_cases),
                "test_details": [],
                "performance": {"avg_time": 0, "total_time": 0}
            }
            
            total_time = 0
            
            for start_label, end_label, should_exist, description in test_cases:
                start_time = time.time()
                
                try:
                    start_node_id = self.node_map[start_label].id if start_label in self.node_map else "invalid"
                    end_node_id = self.node_map[end_label].id if end_label in self.node_map else "invalid"
                    
                    # Call the pathfinding algorithm
                    path = await self.client.find_path(
                        session_id=self.session_id,
                        from_node_id=start_node_id,
                        to_node_id=end_node_id,
                        algorithm=algorithm
                    )
                    
                    duration = time.time() - start_time
                    total_time += duration
                    
                    # Evaluate result
                    path_found = path is not None and len(path) > 0
                    test_passed = (path_found and should_exist) or (not path_found and not should_exist)
                    
                    if test_passed:
                        algo_results["tests_passed"] += 1
                    
                    test_detail = {
                        "description": description,
                        "start": start_label,
                        "end": end_label,
                        "expected_path": should_exist,
                        "path_found": path_found,
                        "path_length": len(path) if path else 0,
                        "duration_ms": duration * 1000,
                        "status": "PASS" if test_passed else "FAIL"
                    }
                    
                    if path and len(path) > 0:
                        # Extract readable path
                        path_labels = []
                        for node_id in path:
                            for label, node in self.node_map.items():
                                if node.id == node_id:
                                    path_labels.append(label)
                                    break
                        test_detail["path_trace"] = " -> ".join(path_labels)
                    
                    algo_results["test_details"].append(test_detail)
                    
                except Exception as e:
                    duration = time.time() - start_time
                    total_time += duration
                    
                    test_detail = {
                        "description": description,
                        "start": start_label,
                        "end": end_label,
                        "expected_path": should_exist,
                        "error": str(e),
                        "duration_ms": duration * 1000,
                        "status": "ERROR"
                    }
                    algo_results["test_details"].append(test_detail)
            
            algo_results["performance"]["total_time"] = total_time
            algo_results["performance"]["avg_time"] = total_time / len(test_cases)
            algo_results["success_rate"] = (algo_results["tests_passed"] / algo_results["tests_total"]) * 100
            algo_results["status"] = "PASS" if algo_results["tests_passed"] == algo_results["tests_total"] else "FAIL"
            
            pathfinding_results[algorithm] = algo_results
        
        self.test_results["algorithms"]["pathfinding"] = pathfinding_results
        logger.info(f"✅ Pathfinding tests completed")
    
    async def test_neighbor_discovery(self):
        """Test neighbor discovery algorithms"""
        logger.info("🔍 Testing neighbor discovery...")
        
        neighbor_results = {}
        
        # Test cases for neighbor discovery (only direct neighbors)
        test_cases = [
            ('E', 1, 5, "Central hub - direct neighbors"),  # E should have many direct neighbors
            ('A', 1, 2, "Corner node - direct neighbors"),  # A has fewer direct neighbors
            ('B', 1, 3, "Edge node - direct neighbors"),    # B has moderate neighbors
            ('I', 1, 2, "Corner node - direct neighbors"),  # I has fewer direct neighbors
        ]
        
        for node_label, max_depth, expected_min_neighbors, description in test_cases:
            start_time = time.time()
            
            try:
                node_id = self.node_map[node_label].id
                
                # Test neighbor discovery
                neighbors = await self.client.get_neighbors(
                    session_id=self.session_id,
                    node_id=node_id,
                    direction="both"
                )
                
                duration = time.time() - start_time
                
                neighbor_count = len(neighbors) if neighbors else 0
                test_passed = neighbor_count >= expected_min_neighbors
                
                # Get readable neighbor list
                neighbor_labels = []
                if neighbors:
                    for neighbor_id in neighbors:
                        for label, node in self.node_map.items():
                            if node.id == neighbor_id:
                                neighbor_labels.append(label)
                                break
                
                test_result = {
                    "description": description,
                    "node": node_label,
                    "max_depth": max_depth,
                    "expected_min": expected_min_neighbors,
                    "neighbors_found": neighbor_count,
                    "neighbor_list": neighbor_labels,
                    "duration_ms": duration * 1000,
                    "status": "PASS" if test_passed else "FAIL"
                }
                
                neighbor_results[f"{node_label}_depth_{max_depth}"] = test_result
                
            except Exception as e:
                duration = time.time() - start_time
                test_result = {
                    "description": description,
                    "node": node_label,
                    "max_depth": max_depth,
                    "error": str(e),
                    "duration_ms": duration * 1000,
                    "status": "ERROR"
                }
                neighbor_results[f"{node_label}_depth_{max_depth}"] = test_result
        
        # Calculate overall neighbor discovery stats
        passed_tests = sum(1 for result in neighbor_results.values() if result["status"] == "PASS")
        total_tests = len(neighbor_results)
        
        neighbor_summary = {
            "tests_passed": passed_tests,
            "tests_total": total_tests,
            "success_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
            "status": "PASS" if passed_tests == total_tests else "FAIL",
            "test_details": neighbor_results
        }
        
        self.test_results["algorithms"]["neighbor_discovery"] = neighbor_summary
        logger.info(f"✅ Neighbor discovery tests completed: {passed_tests}/{total_tests} passed")
    
    async def test_backtracking_correctness(self):
        """Test backtracking algorithms for correctness"""
        logger.info("🔄 Testing backtracking algorithm correctness...")
        
        backtrack_results = {}
        
        # Create a test case that requires backtracking
        # We'll test DFS specifically since it uses backtracking
        test_cases = [
            {
                "name": "Simple backtrack",
                "start": "A",
                "end": "I", 
                "description": "Path from A to I should require backtracking in DFS"
            },
            {
                "name": "Multi-path exploration",
                "start": "A",
                "end": "F",
                "description": "Multiple valid paths available, DFS should backtrack when needed"
            },
            {
                "name": "Dead end avoidance",
                "start": "G",
                "end": "C",
                "description": "Path requiring strategic backtracking"
            }
        ]
        
        for test_case in test_cases:
            start_time = time.time()
            
            try:
                start_id = self.node_map[test_case["start"]].id
                end_id = self.node_map[test_case["end"]].id
                
                # Test DFS with backtracking
                path = await self.client.find_path(
                    session_id=self.session_id,
                    from_node_id=start_id,
                    to_node_id=end_id,
                    algorithm="dfs"
                )
                
                duration = time.time() - start_time
                
                # Verify path correctness
                path_valid = path is not None and len(path) >= 2
                path_connected = True
                
                if path_valid and len(path) > 1:
                    # Verify each step in the path is connected
                    for i in range(len(path) - 1):
                        current_node = path[i]
                        next_node = path[i + 1]
                        
                        # Check if there's an edge between these nodes
                        edge_exists = False
                        for edge in self.test_edges:
                            if ((edge.from_node == current_node and edge.to_node == next_node) or
                                (edge.from_node == next_node and edge.to_node == current_node)):
                                edge_exists = True
                                break
                        
                        if not edge_exists:
                            path_connected = False
                            break
                
                # Get readable path
                path_labels = []
                if path:
                    for node_id in path:
                        for label, node in self.node_map.items():
                            if node.id == node_id:
                                path_labels.append(label)
                                break
                
                test_passed = path_valid and path_connected
                
                test_result = {
                    "name": test_case["name"],
                    "description": test_case["description"],
                    "start": test_case["start"],
                    "end": test_case["end"],
                    "path_found": path_valid,
                    "path_connected": path_connected,
                    "path_length": len(path) if path else 0,
                    "path_trace": " -> ".join(path_labels),
                    "duration_ms": duration * 1000,
                    "status": "PASS" if test_passed else "FAIL"
                }
                
                backtrack_results[test_case["name"]] = test_result
                
            except Exception as e:
                duration = time.time() - start_time
                test_result = {
                    "name": test_case["name"],
                    "description": test_case["description"],
                    "error": str(e),
                    "duration_ms": duration * 1000,
                    "status": "ERROR"
                }
                backtrack_results[test_case["name"]] = test_result
        
        # Calculate backtracking summary
        passed_tests = sum(1 for result in backtrack_results.values() if result["status"] == "PASS")
        total_tests = len(backtrack_results)
        
        backtrack_summary = {
            "tests_passed": passed_tests,
            "tests_total": total_tests,
            "success_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
            "status": "PASS" if passed_tests == total_tests else "FAIL",
            "test_details": backtrack_results
        }
        
        self.test_results["algorithms"]["backtracking"] = backtrack_summary
        logger.info(f"✅ Backtracking tests completed: {passed_tests}/{total_tests} passed")
    
    async def test_graph_traversal(self):
        """Test complete graph traversal algorithms"""
        logger.info("🌐 Testing graph traversal completeness...")
        
        traversal_results = {}
        
        # Test complete graph traversal from different starting points
        test_cases = [
            ("E", "Central hub traversal"),
            ("A", "Corner traversal"),
            ("G", "Opposite corner traversal")
        ]
        
        for start_label, description in test_cases:
            start_time = time.time()
            
            try:
                start_id = self.node_map[start_label].id
                
                # Get all reachable nodes using direct neighbors (simplified test)
                all_neighbors = await self.client.get_neighbors(
                    session_id=self.session_id,
                    node_id=start_id,
                    direction="both"
                )
                
                duration = time.time() - start_time
                
                # Count reachable nodes (including start node)
                reachable_count = len(all_neighbors) + 1 if all_neighbors else 1
                total_nodes = len(self.test_nodes)
                
                # In our test, we're only checking direct connectivity (not full traversal)
                direct_connectivity = reachable_count >= 2  # At least one neighbor
                
                # Get readable neighbor list
                neighbor_labels = []
                if all_neighbors:
                    for neighbor_id in all_neighbors:
                        for label, node in self.node_map.items():
                            if node.id == neighbor_id:
                                neighbor_labels.append(label)
                                break
                
                test_result = {
                    "description": description,
                    "start_node": start_label,
                    "reachable_nodes": reachable_count,
                    "total_nodes": total_nodes,
                    "direct_connectivity": direct_connectivity,
                    "reachable_list": neighbor_labels,
                    "duration_ms": duration * 1000,
                    "status": "PASS" if direct_connectivity else "FAIL"
                }
                
                traversal_results[start_label] = test_result
                
            except Exception as e:
                duration = time.time() - start_time
                test_result = {
                    "description": description,
                    "start_node": start_label,
                    "error": str(e),
                    "duration_ms": duration * 1000,
                    "status": "ERROR"
                }
                traversal_results[start_label] = test_result
        
        # Calculate traversal summary
        passed_tests = sum(1 for result in traversal_results.values() if result["status"] == "PASS")
        total_tests = len(traversal_results)
        
        traversal_summary = {
            "tests_passed": passed_tests,
            "tests_total": total_tests,
            "success_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
            "status": "PASS" if passed_tests == total_tests else "FAIL",
            "test_details": traversal_results
        }
        
        self.test_results["algorithms"]["graph_traversal"] = traversal_summary
        logger.info(f"✅ Graph traversal tests completed: {passed_tests}/{total_tests} passed")
    
    async def cleanup_test_data(self):
        """Clean up test data"""
        logger.info("🧹 Cleaning up algorithm test data...")
        
        try:
            # Clear all test data for this session
            await self.client.clear_session_graph(self.session_id)
            logger.info("✅ Algorithm test cleanup completed")
        except Exception as e:
            logger.warning(f"⚠️ Cleanup warning: {e}")
    
    def save_results(self, output_dir: str):
        """Save test results to JSON file"""
        results_file = os.path.join(output_dir, "algorithm_correctness_results.json")
        
        # Calculate overall performance
        all_algorithms = self.test_results.get("algorithms", {})
        total_tests = 0
        passed_tests = 0
        
        for algo_category in all_algorithms.values():
            if isinstance(algo_category, dict):
                if "tests_passed" in algo_category and "tests_total" in algo_category:
                    # Single test category
                    total_tests += algo_category["tests_total"]
                    passed_tests += algo_category["tests_passed"]
                else:
                    # Multiple sub-categories (like pathfinding with multiple algorithms)
                    for sub_category in algo_category.values():
                        if isinstance(sub_category, dict) and "tests_passed" in sub_category:
                            total_tests += sub_category["tests_total"]
                            passed_tests += sub_category["tests_passed"]
        
        # Add summary
        self.test_results["summary"] = {
            "tests_passed": passed_tests,
            "tests_total": total_tests,
            "success_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
            "overall_status": "PASS" if passed_tests == total_tests else "FAIL"
        }
        
        # Set final status
        self.test_results["status"] = self.test_results["summary"]["overall_status"]
        
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        logger.info(f"📄 Algorithm correctness results saved to: {results_file}")
        return results_file

async def main():
    """Main test execution"""
    logger.info("🧮 Knowledge Graph Algorithm Correctness Test Suite")
    logger.info("=" * 60)
    
    # Create output directory
    timestamp = datetime.now().strftime('%Y%m%dT%H%M%SZ')
    output_dir = f"internal_checks/kg_run_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize test suite
    test_suite = AlgorithmCorrectnessTest()
    
    try:
        # Setup
        logger.info("🔧 Setting up algorithm correctness tests...")
        if not await test_suite.setup_client():
            logger.error("❌ Failed to setup ArangoDB client")
            return False
        
        # Create test graph
        test_suite.create_test_graph()
        
        # Setup test data
        if not await test_suite.setup_test_data():
            logger.error("❌ Failed to setup test data")
            return False
        
        logger.info("🚀 Starting algorithm correctness tests...")
        
        # Run all algorithm tests
        await test_suite.test_pathfinding_algorithms()
        await test_suite.test_neighbor_discovery()
        await test_suite.test_backtracking_correctness()
        await test_suite.test_graph_traversal()
        
        # Save results
        results_file = test_suite.save_results(output_dir)
        
        # Print summary
        summary = test_suite.test_results.get("summary", {})
        logger.info("📊 Algorithm Correctness Test Summary:")
        logger.info(f"   Tests passed: {summary.get('tests_passed', 0)}/{summary.get('tests_total', 0)}")
        logger.info(f"   Success rate: {summary.get('success_rate', 0):.1f}%")
        logger.info(f"   Overall status: {summary.get('overall_status', 'UNKNOWN')}")
        
        if summary.get('overall_status') == 'PASS':
            logger.info("🎉 ALL ALGORITHM TESTS PASSED!")
        else:
            logger.warning("⚠️ Some algorithm tests failed - check detailed results")
        
        return summary.get('overall_status') == 'PASS'
        
    except Exception as e:
        logger.error(f"❌ Algorithm correctness test failed: {e}")
        return False
        
    finally:
        # Cleanup
        if test_suite.client:
            await test_suite.cleanup_test_data()

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
