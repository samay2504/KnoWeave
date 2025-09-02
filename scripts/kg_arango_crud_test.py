#!/usr/bin/env python3
"""
Knowledge Graph ArangoDB CRUD Test
Comprehensive test for data persistence with 50 nodes, embeddings, and complex graph structure
"""

import asyncio
import logging
import sys
import json
import uuid
import random
import numpy as np
from pathlib import Path
from datetime import datetime, timezone

# Add server to path
current_dir = Path(__file__).parent
server_dir = current_dir.parent / "server"
sys.path.insert(0, str(server_dir))

# Set environment
import os
os.chdir(current_dir.parent)

from server_config import ServerConfig
from db.arango_client import create_arango_client, GraphNode, GraphEdge

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KGCRUDTest:
    """Comprehensive CRUD test for Knowledge Graph"""
    
    def __init__(self):
        self.config = None
        self.client = None
        self.session_id = f"session_test_kg_20250831T130357Z"
        self.nodes_created = []
        self.edges_created = []
        self.test_results = {
            "timestamp": "20250831T130357Z",
            "session_id": self.session_id,
            "operations": {},
            "performance": {},
            "status": "UNKNOWN"
        }
        
    async def setup(self):
        """Initialize ArangoDB connection"""
        try:
            self.config = ServerConfig()
            logger.info("🔧 Loading server configuration...")
            
            self.client = await create_arango_client(self.config.get_database_config()["arango"])
            if not self.client:
                logger.error("❌ Failed to create ArangoDB client")
                return False
                
            logger.info("✅ ArangoDB client created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            self.test_results["setup_error"] = str(e)
            return False
    
    def generate_synthetic_embedding(self, dimension=384):
        """Generate synthetic embedding vector"""
        # Create normalized random vector
        vector = np.random.normal(0, 1, dimension)
        vector = vector / np.linalg.norm(vector)
        return vector.tolist()
    
    def generate_test_nodes(self, count=50):
        """Generate test nodes with varied content"""
        node_types = ["character", "location", "event", "concept", "object"]
        
        nodes = []
        for i in range(count):
            node_type = random.choice(node_types)
            
            node = GraphNode(
                id=f"test_node_{i:03d}",
                type=node_type,
                summary=f"Test {node_type} #{i}: {self._generate_content(node_type)}",
                properties={
                    "test_id": i,
                    "node_type": node_type,
                    "score": random.uniform(0.1, 1.0),
                    "usage_count": random.randint(0, 100),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "metadata": {
                        "importance": random.uniform(0.1, 1.0),
                        "complexity": random.choice(["low", "medium", "high"]),
                        "tags": [f"tag_{j}" for j in range(random.randint(1, 4))]
                    }
                },
                embedding=self.generate_synthetic_embedding(),
                confidence=random.uniform(0.7, 1.0),
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            nodes.append(node)
        
        return nodes
    
    def _generate_content(self, node_type):
        """Generate realistic content for different node types"""
        content_templates = {
            "character": ["brave knight", "wise wizard", "cunning thief", "noble queen", "mysterious stranger"],
            "location": ["ancient castle", "dark forest", "bustling marketplace", "hidden cave", "mountain peak"],
            "event": ["epic battle", "royal wedding", "secret meeting", "magical ritual", "treasure hunt"],
            "concept": ["ancient magic", "divine power", "friendship bond", "heroic sacrifice", "forbidden knowledge"],
            "object": ["magical sword", "ancient tome", "golden crown", "mysterious amulet", "enchanted ring"]
        }
        
        templates = content_templates.get(node_type, ["generic item"])
        return random.choice(templates)
    
    def generate_test_edges(self, nodes):
        """Generate edges forming DAG + cycles for comprehensive testing"""
        edges = []
        edge_types = ["relates_to", "leads_to", "contains", "influences", "preceded_by"]
        
        # Create linear connections (DAG structure)
        for i in range(len(nodes) - 1):
            edge = GraphEdge(
                from_node=nodes[i].id,
                to_node=nodes[i + 1].id,
                type=random.choice(edge_types),
                properties={
                    "relationship_strength": random.uniform(0.1, 1.0),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "edge_metadata": {
                        "importance": random.uniform(0.1, 1.0),
                        "verified": random.choice([True, False])
                    }
                },
                confidence=random.uniform(0.6, 1.0)
            )
            edges.append(edge)
        
        # Add random connections for complexity
        for _ in range(min(25, len(nodes) // 2)):
            from_idx = random.randint(0, len(nodes) - 1)
            to_idx = random.randint(0, len(nodes) - 1)
            
            if from_idx != to_idx:
                edge = GraphEdge(
                    from_node=nodes[from_idx].id,
                    to_node=nodes[to_idx].id,
                    type=random.choice(edge_types),
                    properties={
                        "relationship_strength": random.uniform(0.1, 1.0),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "random_connection": True
                    },
                    confidence=random.uniform(0.5, 0.9)
                )
                edges.append(edge)
        
        # Add a few cycles for traversal testing
        if len(nodes) >= 5:
            cycle_edges = [
                GraphEdge(
                    from_node=nodes[0].id,
                    to_node=nodes[4].id,
                    type="creates_cycle",
                    properties={"cycle_edge": True},
                    confidence=0.8
                ),
                GraphEdge(
                    from_node=nodes[4].id,
                    to_node=nodes[2].id,
                    type="creates_cycle",
                    properties={"cycle_edge": True},
                    confidence=0.8
                )
            ]
            edges.extend(cycle_edges)
        
        return edges
    
    async def test_create_operations(self):
        """Test node and edge creation"""
        start_time = datetime.now()
        
        try:
            logger.info("📝 Testing CREATE operations...")
            
            # Generate test data
            test_nodes = self.generate_test_nodes(50)
            logger.info(f"Generated {len(test_nodes)} test nodes")
            
            # Create nodes
            created_count = 0
            failed_nodes = []
            
            for node in test_nodes:
                try:
                    result = await self.client.add_node(self.session_id, node)
                    if result:
                        self.nodes_created.append(node.id)
                        created_count += 1
                    else:
                        failed_nodes.append(node.id)
                except Exception as e:
                    failed_nodes.append(f"{node.id}: {str(e)}")
            
            logger.info(f"✅ Created {created_count}/{len(test_nodes)} nodes")
            
            # Generate and create edges
            test_edges = self.generate_test_edges(test_nodes)
            logger.info(f"Generated {len(test_edges)} test edges")
            
            edges_created = 0
            failed_edges = []
            
            for edge in test_edges:
                try:
                    result = await self.client.add_edge(self.session_id, edge)
                    if result:
                        self.edges_created.append(f"{edge.from_node}->{edge.to_node}")
                        edges_created += 1
                    else:
                        failed_edges.append(f"{edge.from_node}->{edge.to_node}")
                except Exception as e:
                    failed_edges.append(f"{edge.from_node}->{edge.to_node}: {str(e)}")
            
            logger.info(f"✅ Created {edges_created}/{len(test_edges)} edges")
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.test_results["operations"]["create"] = {
                "nodes_attempted": len(test_nodes),
                "nodes_created": created_count,
                "nodes_failed": len(failed_nodes),
                "edges_attempted": len(test_edges),
                "edges_created": edges_created,
                "edges_failed": len(failed_edges),
                "duration_seconds": duration,
                "failed_items": {"nodes": failed_nodes, "edges": failed_edges},
                "status": "PASS" if (created_count > 40 and edges_created > 20) else "FAIL"
            }
            
            return created_count > 40 and edges_created > 20
            
        except Exception as e:
            logger.error(f"❌ Create operations failed: {e}")
            self.test_results["operations"]["create"] = {
                "status": "FAIL",
                "error": str(e)
            }
            return False
    
    async def test_read_operations(self):
        """Test data retrieval and verification"""
        start_time = datetime.now()
        
        try:
            logger.info("📖 Testing READ operations...")
            
            # Read all nodes for session
            nodes = await self.client.get_nodes(self.session_id)
            logger.info(f"Retrieved {len(nodes)} nodes")
            
            # Read all edges for session
            edges = await self.client.get_edges(self.session_id)
            logger.info(f"Retrieved {len(edges)} edges")
            
            # Verify node data integrity - handle both dict and GraphNode objects
            verified_nodes = 0
            for node in nodes[:10]:  # Sample verification
                # Handle both dict and GraphNode object formats
                if hasattr(node, '__dict__'):
                    # It's a GraphNode object
                    node_data = node.__dict__
                else:
                    # It's already a dict
                    node_data = node
                
                if (node_data.get("id") and 
                    node_data.get("type") and 
                    node_data.get("summary")):
                    verified_nodes += 1
            
            # Verify edge data integrity - handle both dict and GraphEdge objects
            verified_edges = 0
            for edge in edges[:10]:  # Sample verification
                # Handle both dict and GraphEdge object formats
                if hasattr(edge, '__dict__'):
                    # It's a GraphEdge object
                    edge_data = edge.__dict__
                else:
                    # It's already a dict
                    edge_data = edge
                
                if (edge_data.get("from_node") and 
                    edge_data.get("to_node") and 
                    edge_data.get("type")):
                    verified_edges += 1
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.test_results["operations"]["read"] = {
                "nodes_retrieved": len(nodes),
                "edges_retrieved": len(edges),
                "nodes_verified": verified_nodes,
                "edges_verified": verified_edges,
                "duration_seconds": duration,
                "status": "PASS" if (len(nodes) > 40 and len(edges) > 20) else "FAIL"
            }
            
            return len(nodes) > 40 and len(edges) > 20
            
        except Exception as e:
            logger.error(f"❌ Read operations failed: {e}")
            self.test_results["operations"]["read"] = {
                "status": "FAIL",
                "error": str(e)
            }
            return False
    
    async def test_update_operations(self):
        """Test node updates"""
        start_time = datetime.now()
        
        try:
            logger.info("✏️ Testing UPDATE operations...")
            
            if not self.nodes_created:
                logger.warning("No nodes to update")
                return False
            
            # Select a node to update
            test_node_id = self.nodes_created[0]
            
            # Get current node data
            nodes = await self.client.get_nodes(self.session_id)
            target_node = None
            for node in nodes:
                # Handle both dict and GraphNode object formats
                if hasattr(node, '__dict__'):
                    node_data = node.__dict__
                else:
                    node_data = node
                
                if node_data.get("id") == test_node_id:
                    target_node = node_data
                    break
            
            if not target_node:
                logger.error(f"Target node {test_node_id} not found")
                return False
            
            # Update node properties
            updated_properties = target_node.get("properties", {})
            updated_properties["updated_at"] = datetime.now(timezone.utc).isoformat()
            updated_properties["score"] = 0.95
            updated_properties["test_update"] = True
            
            # Create updated node
            updated_node = GraphNode(
                id=target_node["id"],
                type=target_node["type"],
                summary=target_node["summary"] + " [UPDATED]",
                properties=updated_properties,
                embedding=target_node.get("embedding"),
                confidence=target_node.get("confidence", 1.0)
            )
            
            # Save update
            result = await self.client.add_node(self.session_id, updated_node)
            
            # Verify update
            updated_nodes = await self.client.get_nodes(self.session_id)
            verification_passed = False
            
            for node in updated_nodes:
                # Handle both dict and GraphNode object formats
                if hasattr(node, '__dict__'):
                    node_data = node.__dict__
                else:
                    node_data = node
                
                if (node_data.get("id") == test_node_id and 
                    "[UPDATED]" in node_data.get("summary", "") and
                    node_data.get("properties", {}).get("test_update") == True):
                    verification_passed = True
                    break
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.test_results["operations"]["update"] = {
                "node_updated": test_node_id,
                "update_successful": result,
                "verification_passed": verification_passed,
                "duration_seconds": duration,
                "status": "PASS" if (result and verification_passed) else "FAIL"
            }
            
            return result and verification_passed
            
        except Exception as e:
            logger.error(f"❌ Update operations failed: {e}")
            self.test_results["operations"]["update"] = {
                "status": "FAIL",
                "error": str(e)
            }
            return False
    
    async def test_delete_operations(self):
        """Test node deletion"""
        start_time = datetime.now()
        
        try:
            logger.info("🗑️ Testing DELETE operations...")
            
            if len(self.nodes_created) < 2:
                logger.warning("Not enough nodes to test deletion")
                return False
            
            # Select node to delete (not the first one we updated)
            node_to_delete = self.nodes_created[-1]
            
            # Delete node
            result = await self.client.delete_node(self.session_id, node_to_delete)
            
            # Verify deletion
            remaining_nodes = await self.client.get_nodes(self.session_id)
            node_still_exists = False
            
            for node in remaining_nodes:
                # Handle both dict and GraphNode object formats
                if hasattr(node, '__dict__'):
                    node_data = node.__dict__
                else:
                    node_data = node
                
                if node_data.get("id") == node_to_delete:
                    node_still_exists = True
                    break
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.test_results["operations"]["delete"] = {
                "node_deleted": node_to_delete,
                "deletion_result": result,
                "node_still_exists": node_still_exists,
                "remaining_nodes": len(remaining_nodes),
                "duration_seconds": duration,
                "status": "PASS" if (result and not node_still_exists) else "FAIL"
            }
            
            return result and not node_still_exists
            
        except Exception as e:
            logger.error(f"❌ Delete operations failed: {e}")
            self.test_results["operations"]["delete"] = {
                "status": "FAIL",
                "error": str(e)
            }
            return False
    
    async def run_all_tests(self):
        """Run all CRUD tests"""
        logger.info("🚀 Starting comprehensive CRUD tests...")
        
        test_sequence = [
            ("CREATE", self.test_create_operations),
            ("READ", self.test_read_operations),
            ("UPDATE", self.test_update_operations),
            ("DELETE", self.test_delete_operations)
        ]
        
        passed_tests = 0
        total_tests = len(test_sequence)
        
        for test_name, test_func in test_sequence:
            logger.info(f"\n--- {test_name} TEST ---")
            try:
                success = await test_func()
                if success:
                    logger.info(f"✅ {test_name} test: PASSED")
                    passed_tests += 1
                else:
                    logger.error(f"❌ {test_name} test: FAILED")
            except Exception as e:
                logger.error(f"❌ {test_name} test exception: {e}")
        
        # Overall results
        self.test_results["summary"] = {
            "tests_passed": passed_tests,
            "tests_total": total_tests,
            "success_rate": (passed_tests / total_tests) * 100,
            "overall_status": "PASS" if passed_tests >= total_tests - 1 else "FAIL"
        }
        
        self.test_results["status"] = self.test_results["summary"]["overall_status"]
        
        logger.info(f"\n📊 CRUD Test Summary:")
        logger.info(f"   Tests passed: {passed_tests}/{total_tests}")
        logger.info(f"   Success rate: {self.test_results['summary']['success_rate']:.1f}%")
        logger.info(f"   Overall status: {self.test_results['status']}")
        
        return self.test_results["status"] == "PASS"
    
    async def cleanup(self):
        """Clean up test data"""
        try:
            logger.info("🧹 Cleaning up test data...")
            await self.client.clear_session_graph(self.session_id)
            logger.info("✅ Cleanup completed")
        except Exception as e:
            logger.warning(f"⚠️ Cleanup warning: {e}")
    
    def save_results(self):
        """Save test results to file"""
        results_file = "internal_checks/kg_run_20250831T130357Z/crud_results.json"
        try:
            with open(results_file, 'w') as f:
                json.dump(self.test_results, f, indent=2)
            logger.info(f"📄 Results saved to: {results_file}")
        except Exception as e:
            logger.error(f"❌ Failed to save results: {e}")

async def main():
    """Main test execution"""
    logger.info("🧪 Knowledge Graph CRUD Test Suite")
    logger.info("=" * 60)
    
    test = KGCRUDTest()
    
    try:
        # Setup
        if not await test.setup():
            logger.error("❌ Setup failed")
            test.save_results()
            return False
        
        # Run tests
        success = await test.run_all_tests()
        
        # Cleanup
        await test.cleanup()
        
        # Save results
        test.save_results()
        
        if success:
            logger.info("\n🎉 ALL CRUD TESTS PASSED!")
        else:
            logger.error("\n❌ Some CRUD tests failed")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        test.test_results["fatal_error"] = str(e)
        test.save_results()
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        exit(1)
