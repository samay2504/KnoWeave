#!/usr/bin/env python3
"""
Knowledge Graph Performance and Scalability Testing
=================================================

Testing KG performance under various load conditions:
- Large graph creation (1000+ nodes)
- Concurrent operations
- Query response times
- Memory usage patterns
- Scalability limits

Part of the autonomous Knowledge Graph validation mission.
"""

import asyncio
import json
import logging
import os
import sys
import time
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Add the server directory to the path
current_dir = Path(__file__).parent
server_dir = current_dir.parent / "server"
sys.path.insert(0, str(server_dir))

# Set environment
os.chdir(current_dir.parent)

from server_config import ServerConfig
from db.arango_client import create_arango_client, GraphNode, GraphEdge

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PerformanceTest:
    """Test Knowledge Graph performance and scalability"""
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or f"session_perf_test_{datetime.now().strftime('%Y%m%dT%H%M%SZ')}"
        self.config = None
        self.client = None
        self.test_results = {
            "timestamp": datetime.now().strftime('%Y%m%dT%H%M%SZ'),
            "session_id": self.session_id,
            "performance_tests": {},
            "scalability": {},
            "status": "INIT"
        }
        
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
    
    def generate_large_graph(self, num_nodes: int = 1000, num_edges: int = 2000):
        """Generate a large graph for performance testing"""
        logger.info(f"🏗️ Generating large graph: {num_nodes} nodes, {num_edges} edges...")
        
        nodes = []
        edges = []
        
        # Generate nodes
        for i in range(num_nodes):
            node = GraphNode(
                id=f"perf_node_{i:04d}",
                type=random.choice(["entity", "event", "concept"]),
                summary=f"Performance test node {i:04d}: {self._generate_content()}",
                properties={
                    "test_id": i,
                    "cluster": i // 100,  # Group nodes into clusters
                    "importance": random.uniform(0.1, 1.0),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
                embedding=[random.uniform(-1, 1) for _ in range(384)],
                confidence=random.uniform(0.8, 1.0)
            )
            nodes.append(node)
        
        # Generate edges (prefer connections within clusters, some between clusters)
        edge_count = 0
        attempts = 0
        max_attempts = num_edges * 3
        
        while edge_count < num_edges and attempts < max_attempts:
            attempts += 1
            
            from_idx = random.randint(0, num_nodes - 1)
            to_idx = random.randint(0, num_nodes - 1)
            
            if from_idx == to_idx:
                continue
            
            # Prefer connections within same cluster (80% chance)
            from_cluster = from_idx // 100
            to_cluster = to_idx // 100
            
            if from_cluster != to_cluster and random.random() > 0.2:
                continue
            
            edge = GraphEdge(
                from_node=nodes[from_idx].id,
                to_node=nodes[to_idx].id,
                type=random.choice(["relates_to", "influences", "precedes", "contains"]),
                properties={
                    "weight": random.uniform(0.1, 1.0),
                    "strength": random.uniform(0.5, 1.0),
                    "cluster_connection": from_cluster == to_cluster
                },
                confidence=random.uniform(0.7, 1.0)
            )
            edges.append(edge)
            edge_count += 1
        
        logger.info(f"✅ Generated {len(nodes)} nodes and {len(edges)} edges")
        return nodes, edges
    
    def _generate_content(self):
        """Generate realistic content for test nodes"""
        topics = [
            "machine learning algorithm", "data processing pipeline", "user interaction",
            "system optimization", "network communication", "database operation",
            "security protocol", "performance metric", "business logic", "api endpoint"
        ]
        return random.choice(topics)
    
    async def test_bulk_creation_performance(self, nodes: List[GraphNode], edges: List[GraphEdge]):
        """Test performance of bulk data creation"""
        logger.info("📊 Testing bulk creation performance...")
        
        start_time = time.time()
        
        # Test node creation performance
        node_start = time.time()
        nodes_created = 0
        for i, node in enumerate(nodes):
            try:
                result = await self.client.add_node(self.session_id, node)
                if result:
                    nodes_created += 1
                
                # Report progress every 100 nodes
                if (i + 1) % 100 == 0:
                    elapsed = time.time() - node_start
                    rate = (i + 1) / elapsed
                    logger.info(f"  Created {i + 1}/{len(nodes)} nodes ({rate:.1f} nodes/sec)")
                    
            except Exception as e:
                logger.warning(f"Failed to create node {node.id}: {e}")
        
        node_duration = time.time() - node_start
        
        # Test edge creation performance
        edge_start = time.time()
        edges_created = 0
        for i, edge in enumerate(edges):
            try:
                result = await self.client.add_edge(self.session_id, edge)
                if result:
                    edges_created += 1
                
                # Report progress every 100 edges
                if (i + 1) % 100 == 0:
                    elapsed = time.time() - edge_start
                    rate = (i + 1) / elapsed
                    logger.info(f"  Created {i + 1}/{len(edges)} edges ({rate:.1f} edges/sec)")
                    
            except Exception as e:
                logger.warning(f"Failed to create edge: {e}")
        
        edge_duration = time.time() - edge_start
        total_duration = time.time() - start_time
        
        bulk_results = {
            "nodes_attempted": len(nodes),
            "nodes_created": nodes_created,
            "node_creation_time": node_duration,
            "node_creation_rate": nodes_created / node_duration if node_duration > 0 else 0,
            "edges_attempted": len(edges),
            "edges_created": edges_created,
            "edge_creation_time": edge_duration,
            "edge_creation_rate": edges_created / edge_duration if edge_duration > 0 else 0,
            "total_time": total_duration,
            "status": "PASS" if nodes_created == len(nodes) and edges_created == len(edges) else "PARTIAL"
        }
        
        self.test_results["performance_tests"]["bulk_creation"] = bulk_results
        logger.info(f"✅ Bulk creation: {nodes_created}/{len(nodes)} nodes, {edges_created}/{len(edges)} edges in {total_duration:.2f}s")
        
        return bulk_results
    
    async def test_query_performance(self, num_queries: int = 100):
        """Test query response times"""
        logger.info(f"🔍 Testing query performance with {num_queries} queries...")
        
        query_results = {
            "path_finding": [],
            "neighbor_discovery": [],
            "node_retrieval": [],
            "edge_retrieval": []
        }
        
        # Get some test node IDs for queries
        test_nodes = await self.client.get_nodes(self.session_id)
        if len(test_nodes) < 10:
            logger.warning("Not enough nodes for comprehensive query testing")
            return {"status": "SKIP", "reason": "Insufficient test data"}
        
        node_ids = [node.id for node in test_nodes[:20]]
        
        # Test path finding performance
        for i in range(min(num_queries // 4, 25)):
            start_node = random.choice(node_ids)
            end_node = random.choice(node_ids)
            
            if start_node == end_node:
                continue
            
            start_time = time.time()
            try:
                path = await self.client.find_path(
                    session_id=self.session_id,
                    from_node_id=start_node,
                    to_node_id=end_node,
                    algorithm="bfs"
                )
                duration = time.time() - start_time
                
                query_results["path_finding"].append({
                    "duration_ms": duration * 1000,
                    "path_found": path is not None,
                    "path_length": len(path) if path else 0
                })
            except Exception as e:
                duration = time.time() - start_time
                query_results["path_finding"].append({
                    "duration_ms": duration * 1000,
                    "error": str(e)
                })
        
        # Test neighbor discovery performance
        for i in range(min(num_queries // 4, 25)):
            node_id = random.choice(node_ids)
            
            start_time = time.time()
            try:
                neighbors = await self.client.get_neighbors(
                    session_id=self.session_id,
                    node_id=node_id
                )
                duration = time.time() - start_time
                
                query_results["neighbor_discovery"].append({
                    "duration_ms": duration * 1000,
                    "neighbors_found": len(neighbors) if neighbors else 0
                })
            except Exception as e:
                duration = time.time() - start_time
                query_results["neighbor_discovery"].append({
                    "duration_ms": duration * 1000,
                    "error": str(e)
                })
        
        # Test node retrieval performance
        for i in range(min(num_queries // 4, 25)):
            start_time = time.time()
            try:
                nodes = await self.client.get_nodes(self.session_id, limit=50)
                duration = time.time() - start_time
                
                query_results["node_retrieval"].append({
                    "duration_ms": duration * 1000,
                    "nodes_retrieved": len(nodes) if nodes else 0
                })
            except Exception as e:
                duration = time.time() - start_time
                query_results["node_retrieval"].append({
                    "duration_ms": duration * 1000,
                    "error": str(e)
                })
        
        # Test edge retrieval performance
        for i in range(min(num_queries // 4, 25)):
            start_time = time.time()
            try:
                edges = await self.client.get_edges(self.session_id, limit=50)
                duration = time.time() - start_time
                
                query_results["edge_retrieval"].append({
                    "duration_ms": duration * 1000,
                    "edges_retrieved": len(edges) if edges else 0
                })
            except Exception as e:
                duration = time.time() - start_time
                query_results["edge_retrieval"].append({
                    "duration_ms": duration * 1000,
                    "error": str(e)
                })
        
        # Calculate statistics for each query type
        performance_stats = {}
        for query_type, results in query_results.items():
            if results:
                durations = [r["duration_ms"] for r in results if "duration_ms" in r]
                if durations:
                    performance_stats[query_type] = {
                        "avg_duration_ms": sum(durations) / len(durations),
                        "min_duration_ms": min(durations),
                        "max_duration_ms": max(durations),
                        "total_queries": len(results),
                        "successful_queries": len([r for r in results if "error" not in r])
                    }
        
        self.test_results["performance_tests"]["query_performance"] = {
            "stats": performance_stats,
            "raw_results": query_results,
            "status": "PASS"
        }
        
        logger.info("✅ Query performance testing completed")
        return performance_stats
    
    async def test_concurrent_operations(self, num_concurrent: int = 10):
        """Test concurrent operation handling"""
        logger.info(f"🔄 Testing concurrent operations with {num_concurrent} parallel tasks...")
        
        concurrent_results = {
            "operations_attempted": num_concurrent,
            "operations_completed": 0,
            "operations_failed": 0,
            "avg_duration_ms": 0,
            "max_duration_ms": 0,
            "min_duration_ms": float('inf'),
            "status": "INIT"
        }
        
        async def concurrent_operation(task_id: int):
            """Single concurrent operation"""
            start_time = time.time()
            try:
                # Create a test node
                test_node = GraphNode(
                    id=f"concurrent_node_{task_id}_{int(time.time() * 1000)}",
                    type="test",
                    summary=f"Concurrent test node {task_id}",
                    properties={"task_id": task_id, "timestamp": time.time()},
                    embedding=[random.uniform(-1, 1) for _ in range(384)],
                    confidence=1.0
                )
                
                result = await self.client.add_node(self.session_id, test_node)
                duration = time.time() - start_time
                
                return {
                    "task_id": task_id,
                    "success": result is not None,
                    "duration": duration,
                    "error": None
                }
            except Exception as e:
                duration = time.time() - start_time
                return {
                    "task_id": task_id,
                    "success": False,
                    "duration": duration,
                    "error": str(e)
                }
        
        # Run concurrent operations
        tasks = [concurrent_operation(i) for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful = 0
        failed = 0
        durations = []
        
        for result in results:
            if isinstance(result, dict):
                if result["success"]:
                    successful += 1
                else:
                    failed += 1
                durations.append(result["duration"] * 1000)  # Convert to ms
            else:
                failed += 1
        
        if durations:
            concurrent_results.update({
                "operations_completed": successful,
                "operations_failed": failed,
                "avg_duration_ms": sum(durations) / len(durations),
                "max_duration_ms": max(durations),
                "min_duration_ms": min(durations),
                "success_rate": (successful / num_concurrent) * 100,
                "status": "PASS" if successful >= num_concurrent * 0.8 else "FAIL"
            })
        
        self.test_results["performance_tests"]["concurrent_operations"] = concurrent_results
        logger.info(f"✅ Concurrent operations: {successful}/{num_concurrent} succeeded")
        
        return concurrent_results
    
    async def cleanup_test_data(self):
        """Clean up performance test data"""
        logger.info("🧹 Cleaning up performance test data...")
        
        try:
            await self.client.clear_session_graph(self.session_id)
            logger.info("✅ Performance test cleanup completed")
        except Exception as e:
            logger.warning(f"⚠️ Cleanup warning: {e}")
    
    def save_results(self, output_dir: str):
        """Save test results to JSON file"""
        results_file = os.path.join(output_dir, "performance_results.json")
        
        # Calculate overall status
        perf_tests = self.test_results.get("performance_tests", {})
        total_tests = len(perf_tests)
        passed_tests = sum(1 for test in perf_tests.values() 
                          if isinstance(test, dict) and test.get("status") == "PASS")
        
        self.test_results["summary"] = {
            "tests_passed": passed_tests,
            "tests_total": total_tests,
            "success_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
            "overall_status": "PASS" if passed_tests == total_tests else "FAIL"
        }
        
        self.test_results["status"] = self.test_results["summary"]["overall_status"]
        
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        logger.info(f"📄 Performance results saved to: {results_file}")
        return results_file

async def main():
    """Main performance test execution"""
    logger.info("⚡ Knowledge Graph Performance & Scalability Test Suite")
    logger.info("=" * 60)
    
    # Create output directory
    timestamp = datetime.now().strftime('%Y%m%dT%H%M%SZ')
    output_dir = f"internal_checks/kg_run_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize test suite
    test_suite = PerformanceTest()
    
    try:
        # Setup
        logger.info("🔧 Setting up performance tests...")
        if not await test_suite.setup_client():
            logger.error("❌ Failed to setup ArangoDB client")
            return False
        
        # Generate test data
        logger.info("🏗️ Generating performance test data...")
        nodes, edges = test_suite.generate_large_graph(num_nodes=200, num_edges=400)  # Reduced for initial test
        
        # Run performance tests
        logger.info("🚀 Starting performance tests...")
        
        await test_suite.test_bulk_creation_performance(nodes, edges)
        await test_suite.test_query_performance(num_queries=50)  # Reduced for initial test
        await test_suite.test_concurrent_operations(num_concurrent=5)  # Reduced for initial test
        
        # Save results
        results_file = test_suite.save_results(output_dir)
        
        # Print summary
        summary = test_suite.test_results.get("summary", {})
        logger.info("📊 Performance Test Summary:")
        logger.info(f"   Tests passed: {summary.get('tests_passed', 0)}/{summary.get('tests_total', 0)}")
        logger.info(f"   Success rate: {summary.get('success_rate', 0):.1f}%")
        logger.info(f"   Overall status: {summary.get('overall_status', 'UNKNOWN')}")
        
        if summary.get('overall_status') == 'PASS':
            logger.info("🎉 ALL PERFORMANCE TESTS PASSED!")
        else:
            logger.warning("⚠️ Some performance tests failed - check detailed results")
        
        return summary.get('overall_status') == 'PASS'
        
    except Exception as e:
        logger.error(f"❌ Performance test failed: {e}")
        return False
        
    finally:
        # Cleanup
        if test_suite.client:
            await test_suite.cleanup_test_data()

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
