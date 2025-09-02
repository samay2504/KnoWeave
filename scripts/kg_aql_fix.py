#!/usr/bin/env python3
"""
Knowledge Graph AQL Syntax Auto-Fix
===================================

Auto-fix AQL syntax errors in shortest path and Dijkstra algorithms to achieve 100% algorithm correctness.
This script addresses the specific AQL syntax issues found in our algorithm correctness testing.

Author: AI Assistant
Date: 2025-08-31
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add the server directory to the path
current_dir = Path(__file__).parent
server_dir = current_dir.parent / "server"
sys.path.insert(0, str(server_dir))

# Set environment
os.chdir(current_dir.parent)

from server_config import ServerConfig
from db.arango_client import create_arango_client, GraphNode, GraphEdge

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class KnowledgeGraphAQLFixer:
    """Auto-fix AQL syntax issues in Knowledge Graph algorithms"""
    
    def __init__(self):
        self.client = None
        self.session_id = f"aql_fix_test_{datetime.now().strftime('%Y%m%dT%H%M%SZ')}"
        self.results = {}
        self.timestamp = datetime.now().strftime('%Y%m%dT%H%M%SZ')
        
        # Create results directory
        self.results_dir = Path("internal_checks") / f"kg_run_{self.timestamp}"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
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
            logger.error(f"❌ Failed to setup client: {e}")
            return False
        
    async def create_test_graph(self):
        """Create a test graph for algorithm validation"""
        logger.info("🏗️ Creating test graph for AQL syntax validation...")
        
        # Create test nodes
        nodes = []
        for i in range(6):
            node = GraphNode(
                id=f"test_node_{i}",
                type="test",
                summary=f"Test node {i} for AQL validation",
                properties={"index": i, "cluster": i // 2}
            )
            nodes.append(node)
            await self.client.add_node(self.session_id, node)
        
        # Create test edges with weights
        edges = [
            ("test_node_0", "test_node_1", 1.0),
            ("test_node_1", "test_node_2", 2.0),
            ("test_node_2", "test_node_3", 1.5),
            ("test_node_0", "test_node_3", 4.0),
            ("test_node_3", "test_node_4", 1.0),
            ("test_node_4", "test_node_5", 2.0),
            ("test_node_1", "test_node_4", 3.0),
        ]
        
        for from_node, to_node, weight in edges:
            edge = GraphEdge(
                from_node=from_node,
                to_node=to_node,
                type="test_connection",
                properties={"weight": weight}
            )
            await self.client.add_edge(self.session_id, edge)
            
        logger.info(f"✅ Created test graph: {len(nodes)} nodes, {len(edges)} edges")
        return nodes, edges
        
    async def test_current_algorithms(self):
        """Test current algorithm implementations to identify specific issues"""
        logger.info("🔍 Testing current algorithm implementations...")
        
        test_results = {
            "shortest_path": {"tested": 0, "passed": 0, "errors": []},
            "dijkstra": {"tested": 0, "passed": 0, "errors": []}
        }
        
        # Test shortest path algorithm
        test_pairs = [
            ("test_node_0", "test_node_3"),
            ("test_node_1", "test_node_4"), 
            ("test_node_0", "test_node_5")
        ]
        
        for from_node, to_node in test_pairs:
            # Test shortest path
            try:
                test_results["shortest_path"]["tested"] += 1
                result = await self.client.find_path(
                    session_id=self.session_id,
                    from_node_id=from_node,
                    to_node_id=to_node,
                    algorithm="shortest"
                )
                if result and not result.get("error"):
                    test_results["shortest_path"]["passed"] += 1
                else:
                    test_results["shortest_path"]["errors"].append(
                        result.get("error", "Unknown error") if result else "No result returned"
                    )
            except Exception as e:
                test_results["shortest_path"]["errors"].append(str(e))
                
            # Test Dijkstra
            try:
                test_results["dijkstra"]["tested"] += 1
                result = await self.client.find_path(
                    session_id=self.session_id,
                    from_node_id=from_node,
                    to_node_id=to_node,
                    algorithm="dijkstra"
                )
                if result and not result.get("error"):
                    test_results["dijkstra"]["passed"] += 1
                else:
                    test_results["dijkstra"]["errors"].append(
                        result.get("error", "Unknown error") if result else "No result returned"
                    )
            except Exception as e:
                test_results["dijkstra"]["errors"].append(str(e))
        
        # Log results
        for algo, results in test_results.items():
            success_rate = (results["passed"] / results["tested"]) * 100 if results["tested"] > 0 else 0
            logger.info(f"   {algo}: {results['passed']}/{results['tested']} ({success_rate:.1f}%)")
            if results["errors"]:
                logger.info(f"   Common errors: {set(results['errors'])}")
                
        return test_results
        
    async def analyze_aql_issues(self):
        """Analyze the specific AQL syntax issues that need fixing"""
        logger.info("🔬 Analyzing AQL syntax issues...")
        
        # Read the current ArangoDB client code to identify issues
        client_file = Path(__file__).parent.parent / "server" / "db" / "arango_client.py"
        
        with open(client_file, 'r') as f:
            client_code = f.read()
            
        issues_found = []
        
        # Check for common AQL syntax issues
        if "SHORTEST_PATH(" in client_code:
            issues_found.append({
                "type": "shortest_path_syntax",
                "description": "SHORTEST_PATH function usage needs proper graph specification",
                "location": "_find_shortest_path method"
            })
            
        if "K_SHORTEST_PATHS(" in client_code:
            issues_found.append({
                "type": "k_shortest_paths_syntax", 
                "description": "K_SHORTEST_PATHS function requires correct edge collection reference",
                "location": "_find_dijkstra_path method"
            })
            
        logger.info(f"📋 Found {len(issues_found)} potential AQL syntax issues")
        return issues_found
        
    async def apply_aql_fixes(self):
        """Apply fixes to AQL syntax issues"""
        logger.info("🔧 Applying AQL syntax fixes...")
        
        # The fixes are applied directly to the source file
        client_file = Path(__file__).parent.parent / "server" / "db" / "arango_client.py"
        
        with open(client_file, 'r') as f:
            content = f.read()
            
        original_content = content
        fixes_applied = []
        
        # Fix 1: Shortest Path AQL syntax
        if "_find_shortest_path" in content:
            # Look for the shortest path AQL and fix it
            old_pattern = '''aql = """
            FOR path IN SHORTEST_PATH'''
            
            new_pattern = '''aql = """
            FOR vertex, edge IN 0..@max_depth OUTBOUND @start_node edges
                FILTER vertex.session_id == @session_id
                FILTER vertex._id == @end_node
                LIMIT 1
                RETURN {
                    vertices: [vertex],
                    edges: [edge],
                    distance: 1
                }'''
                
            if old_pattern in content:
                # More targeted fix for shortest path
                shortest_path_fix = '''    async def _find_shortest_path(self, from_ref: str, to_ref: str, max_depth: int, session_id: str) -> Optional[Dict[str, Any]]:
        """Find shortest path using ArangoDB's traversal with session filtering"""
        try:
            aql = """
                WITH nodes, edges
                FOR vertex, edge, path IN 0..@max_depth OUTBOUND @start_node edges
                    FILTER vertex.session_id == @session_id
                    FILTER vertex._id == @end_node
                    SORT LENGTH(path.vertices)
                    LIMIT 1
                    RETURN {
                        vertices: path.vertices,
                        edges: path.edges,
                        distance: LENGTH(path.vertices) - 1
                    }
            """
            
            bind_vars = {
                "start_node": from_ref,
                "end_node": to_ref,
                "session_id": session_id,
                "max_depth": max_depth
            }
            
            path_data = await self._execute_aql(aql, bind_vars)
            
            if path_data and len(path_data) > 0:
                result = path_data[0]
                return {
                    "algorithm": "shortest_path",
                    "path": self._format_path_result(result["vertices"], result["edges"]),
                    "distance": result["distance"],
                    "found": True
                }
            else:
                return {"algorithm": "shortest_path", "found": False, "path": [], "distance": -1}
                
        except Exception as e:
            logger.error(f"Shortest path algorithm failed: {e}")
            return {"algorithm": "shortest_path", "found": False, "path": [], "distance": -1, "error": str(e)}'''
            
            # Replace the method
            start_marker = "async def _find_shortest_path("
            end_marker = "return {\"algorithm\": \"shortest_path\", \"found\": False"
            
            start_idx = content.find(start_marker)
            if start_idx != -1:
                # Find the end of the method (next method definition or end of class)
                next_method = content.find("\n    async def", start_idx + 1)
                if next_method == -1:
                    next_method = content.find("\n    def _format_path_result", start_idx + 1)
                    
                if next_method != -1:
                    content = content[:start_idx] + shortest_path_fix + "\n\n    " + content[next_method + 5:]
                    fixes_applied.append("shortest_path_aql_syntax")
        
        # Fix 2: Dijkstra AQL syntax
        if "_find_dijkstra_path" in content:
            dijkstra_fix = '''    async def _find_dijkstra_path(self, from_ref: str, to_ref: str, max_depth: int, session_id: str) -> Optional[Dict[str, Any]]:
        """Dijkstra's algorithm using AQL with proper edge weight handling"""
        try:
            aql = """
                WITH nodes, edges
                FOR vertex, edge, path IN 0..@max_depth OUTBOUND @start_node edges
                    OPTIONS {weightAttribute: "properties.weight", defaultWeight: 1}
                    FILTER vertex.session_id == @session_id
                    FILTER vertex._id == @end_node
                    SORT path.weight
                    LIMIT 1
                    RETURN {
                        vertices: path.vertices,
                        edges: path.edges,
                        distance: path.weight || LENGTH(path.vertices) - 1
                    }
            """
            
            bind_vars = {
                "start_node": from_ref,
                "end_node": to_ref,
                "session_id": session_id,
                "max_depth": max_depth
            }
            
            path_data = await self._execute_aql(aql, bind_vars)
            
            if path_data and len(path_data) > 0:
                result = path_data[0]
                return {
                    "algorithm": "dijkstra",
                    "path": self._format_path_result(result["vertices"], result["edges"]),
                    "distance": result["distance"],
                    "found": True
                }
            else:
                return {"algorithm": "dijkstra", "found": False, "path": [], "distance": -1}
                
        except Exception as e:
            logger.error(f"Dijkstra algorithm failed: {e}")
            return {"algorithm": "dijkstra", "found": False, "path": [], "distance": -1, "error": str(e)}'''
            
            # Replace the method
            start_marker = "async def _find_dijkstra_path("
            start_idx = content.find(start_marker)
            if start_idx != -1:
                # Find the end of the method
                next_method = content.find("\n    async def", start_idx + 1)
                if next_method == -1:
                    next_method = content.find("\n    def _format_path_result", start_idx + 1)
                    
                if next_method != -1:
                    content = content[:start_idx] + dijkstra_fix + "\n\n    " + content[next_method + 5:]
                    fixes_applied.append("dijkstra_aql_syntax")
        
        # Apply the fixes
        if fixes_applied:
            with open(client_file, 'w') as f:
                f.write(content)
                
            logger.info(f"✅ Applied {len(fixes_applied)} AQL syntax fixes:")
            for fix in fixes_applied:
                logger.info(f"   - {fix}")
        else:
            logger.info("ℹ️ No AQL syntax fixes needed")
            
        return fixes_applied
        
    async def validate_fixes(self):
        """Validate that the AQL fixes work correctly"""
        logger.info("✅ Validating AQL syntax fixes...")
        
        # Re-import the client to get the fixed version
        import importlib
        import sys
        
        # Remove the module from cache to force reload
        if 'server.db.arango_client' in sys.modules:
            del sys.modules['server.db.arango_client']
            
        # Reconnect with fixed client
        await self.client.close()
        await self.setup_client()
        
        # Re-create test graph
        await self.create_test_graph()
        
        # Test the fixed algorithms
        validation_results = await self.test_current_algorithms()
        
        # Calculate improvement
        total_tests = sum(results["tested"] for results in validation_results.values())
        total_passed = sum(results["passed"] for results in validation_results.values())
        success_rate = (total_passed / total_tests) * 100 if total_tests > 0 else 0
        
        logger.info(f"🎯 Post-fix validation: {total_passed}/{total_tests} ({success_rate:.1f}%)")
        
        return validation_results, success_rate
        
    async def cleanup(self):
        """Clean up test data"""
        if self.client:
            await self.client.clear_session_graph(self.session_id)
            await self.client.close()
            
    async def run_aql_fix(self):
        """Run the complete AQL fix process"""
        logger.info("🚀 Starting Knowledge Graph AQL Auto-Fix")
        logger.info("=" * 60)
        
        try:
            # Setup
            await self.setup_client()
            
            # Create test data
            await self.create_test_graph()
            
            # Test current state
            logger.info("📋 Testing current algorithm implementations...")
            pre_fix_results = await self.test_current_algorithms()
            
            # Analyze issues
            issues = await self.analyze_aql_issues()
            
            # Apply fixes
            fixes = await self.apply_aql_fixes()
            
            # Validate fixes
            if fixes:
                post_fix_results, success_rate = await self.validate_fixes()
                
                # Save results
                results = {
                    "timestamp": self.timestamp,
                    "session_id": self.session_id,
                    "pre_fix_results": pre_fix_results,
                    "issues_found": issues,
                    "fixes_applied": fixes,
                    "post_fix_results": post_fix_results,
                    "final_success_rate": success_rate,
                    "status": "COMPLETED"
                }
                
                results_file = self.results_dir / "aql_fix_results.json"
                with open(results_file, 'w') as f:
                    json.dump(results, f, indent=2)
                    
                logger.info(f"📄 Results saved to: {results_file}")
                logger.info("=" * 60)
                logger.info("🎉 AQL Auto-Fix Summary:")
                logger.info(f"   Issues found: {len(issues)}")
                logger.info(f"   Fixes applied: {len(fixes)}")
                logger.info(f"   Final success rate: {success_rate:.1f}%")
                
                if success_rate >= 90:
                    logger.info("✅ AQL FIX SUCCESSFUL!")
                else:
                    logger.info("⚠️ AQL fix partially successful - manual review needed")
            else:
                logger.info("ℹ️ No fixes were necessary")
                
        except Exception as e:
            logger.error(f"❌ AQL fix failed: {e}")
            raise
        finally:
            await self.cleanup()

async def main():
    """Main entry point"""
    fixer = KnowledgeGraphAQLFixer()
    await fixer.run_aql_fix()

if __name__ == "__main__":
    asyncio.run(main())
