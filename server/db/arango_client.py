"""
ArangoDB async client with fallback to MongoDB
"""

import asyncio
import logging
import time
import warnings
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

# Suppress deprecation warnings for cleaner output
warnings.filterwarnings("ignore", message=".*pkg_resources.*", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")

# Initialize availability flags
AIOARANGO_AVAILABLE = False
ARANGO_AVAILABLE = False

# Type stubs for proper IDE support
ArangoClient = None
StandardDatabase = None
ArangoError = Exception
SyncArangoClient = None
SyncStandardDatabase = None
SyncArangoError = Exception

# Try python-arango (sync client) - this is working and stable
try:
    from arango import ArangoClient as SyncArangoClient  # type: ignore
    from arango.database import StandardDatabase as SyncStandardDatabase  # type: ignore
    from arango.exceptions import ArangoError as SyncArangoError  # type: ignore
    ARANGO_AVAILABLE = True
    logging.debug("python-arango successfully imported")
except ImportError as e:
    logging.debug(f"python-arango not available: {e}")
    # Define fallback classes to prevent NameError
    SyncArangoClient = None
    SyncStandardDatabase = None
    SyncArangoError = Exception

# Try aioarango (async client) - currently has dependency conflicts, optional
try:
    from aioarango import ArangoClient  # type: ignore
    from aioarango.database import StandardDatabase  # type: ignore
    from aioarango.exceptions import ArangoError  # type: ignore
    AIOARANGO_AVAILABLE = True
    logging.debug("aioarango successfully imported")
except ImportError as e:
    logging.debug(f"aioarango not available (using sync fallback): {e}")
    # Define fallback classes to prevent NameError
    ArangoClient = None
    StandardDatabase = None
    ArangoError = Exception

# Ensure we have at least one working client
if not AIOARANGO_AVAILABLE and not ARANGO_AVAILABLE:
    logging.error("No ArangoDB client libraries available. Install python-arango")
    raise ImportError("ArangoDB client libraries not found. Please install 'python-arango'.")

# Log the configuration
if ARANGO_AVAILABLE:
    logging.info("Using python-arango (sync) for ArangoDB operations")
if AIOARANGO_AVAILABLE:
    logging.info("Using aioarango (async) for ArangoDB operations")
else:
    logging.info("aioarango not available, using sync client with async wrapper")

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    """Graph node representation"""

    id: str
    type: str  # 'event' or 'entity'
    summary: str
    properties: Dict[str, Any]
    embedding: Optional[List[float]] = None
    confidence: float = 1.0
    timestamp: Optional[str] = None


@dataclass
class GraphEdge:
    """Graph edge representation"""

    from_node: str
    to_node: str
    type: str  # 'causal', 'temporal', 'co_ref', 'attribute'
    properties: Dict[str, Any]
    confidence: float = 1.0


class ArangoGraphClient:
    """Async ArangoDB client for knowledge graph operations"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = None
        self.db = None
        self.nodes_collection = None
        self.edges_collection = None
        self.connected = False
        self.use_sync = False

    async def connect(self) -> bool:
        """Connect to ArangoDB with fallback handling"""
        try:
            if AIOARANGO_AVAILABLE:
                await self._connect_async()
            elif ARANGO_AVAILABLE:
                await self._connect_sync()
            else:
                logger.warning("No ArangoDB library available")
                return False

            await self._initialize_collections()
            self.connected = True
            logger.info("Connected to ArangoDB successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to ArangoDB: {e}")
            return False

    async def _connect_async(self) -> None:
        """Connect using async ArangoDB client"""
        self.client = ArangoClient(hosts=self.config["url"])
        self.db = await self.client.db(
            name=self.config["database"],
            username=self.config["user"],
            password=self.config["password"],
        )
        self.use_sync = False

    async def _connect_sync(self) -> None:
        """Connect using sync ArangoDB client in thread"""

        def _sync_connect():
            client = SyncArangoClient(hosts=self.config["url"])
            return client.db(
                name=self.config["database"],
                username=self.config["user"],
                password=self.config["password"],
            )

        loop = asyncio.get_event_loop()
        self.db = await loop.run_in_executor(None, _sync_connect)
        self.use_sync = True

    async def _initialize_collections(self) -> None:
        """Initialize node and edge collections"""
        if self.use_sync:
            await self._initialize_collections_sync()
        else:
            await self._initialize_collections_async()

    async def _initialize_collections_async(self) -> None:
        """Initialize collections using async client"""
        # Create nodes collection
        if not await self.db.has_collection("nodes"):
            self.nodes_collection = await self.db.create_collection("nodes")
        else:
            self.nodes_collection = self.db.collection("nodes")

        # Create edges collection
        if not await self.db.has_collection("edges"):
            self.edges_collection = await self.db.create_collection("edges", edge=True)
        else:
            self.edges_collection = self.db.collection("edges")

    async def _initialize_collections_sync(self) -> None:
        """Initialize collections using sync client in thread"""

        def _sync_init():
            # Create nodes collection
            if not self.db.has_collection("nodes"):
                nodes_collection = self.db.create_collection("nodes")
            else:
                nodes_collection = self.db.collection("nodes")

            # Create edges collection
            if not self.db.has_collection("edges"):
                edges_collection = self.db.create_collection("edges", edge=True)
            else:
                edges_collection = self.db.collection("edges")

            return nodes_collection, edges_collection

        loop = asyncio.get_event_loop()
        self.nodes_collection, self.edges_collection = await loop.run_in_executor(
            None, _sync_init
        )

    async def add_node(self, session_id: str, node: GraphNode) -> bool:
        """Add a node to the graph"""
        try:
            document = {
                "_key": f"{session_id}_{node.id}",
                "session_id": session_id,
                "node_id": node.id,
                "type": node.type,
                "summary": node.summary,
                "properties": node.properties,
                "embedding": node.embedding,
                "confidence": node.confidence,
                "timestamp": node.timestamp,
            }

            if self.use_sync:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, lambda: self.nodes_collection.insert(document)
                )
            else:
                await self.nodes_collection.insert(document)

            logger.debug(f"Added node {node.id} for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to add node {node.id}: {e}")
            return False

    async def add_edge(self, session_id: str, edge: GraphEdge) -> bool:
        """Add an edge to the graph"""
        try:
            document = {
                "session_id": session_id,
                "_from": f"nodes/{session_id}_{edge.from_node}",
                "_to": f"nodes/{session_id}_{edge.to_node}",
                "type": edge.type,
                "properties": edge.properties,
                "confidence": edge.confidence,
            }

            if self.use_sync:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, lambda: self.edges_collection.insert(document)
                )
            else:
                await self.edges_collection.insert(document)

            logger.debug(
                f"Added edge {edge.from_node} -> {edge.to_node} for session {session_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to add edge {edge.from_node} -> {edge.to_node}: {e}")
            return False

    async def get_nodes(
        self, session_id: str, node_type: Optional[str] = None
    ) -> List[GraphNode]:
        """Get nodes for a session"""
        try:
            aql = "FOR node IN nodes FILTER node.session_id == @session_id"
            bind_vars = {"session_id": session_id}

            if node_type:
                aql += " AND node.type == @node_type"
                bind_vars["node_type"] = node_type

            aql += " RETURN node"

            if self.use_sync:
                loop = asyncio.get_event_loop()
                cursor = await loop.run_in_executor(
                    None, lambda: self.db.aql.execute(aql, bind_vars=bind_vars)
                )
                documents = list(cursor)
            else:
                cursor = await self.db.aql.execute(aql, bind_vars=bind_vars)
                documents = [doc async for doc in cursor]

            nodes = []
            for doc in documents:
                node = GraphNode(
                    id=doc["node_id"],
                    type=doc["type"],
                    summary=doc["summary"],
                    properties=doc["properties"],
                    embedding=doc.get("embedding"),
                    confidence=doc.get("confidence", 1.0),
                    timestamp=doc.get("timestamp"),
                )
                nodes.append(node)

            return nodes

        except Exception as e:
            logger.error(f"Failed to get nodes for session {session_id}: {e}")
            return []

    async def get_edges(
        self, session_id: str, edge_type: Optional[str] = None
    ) -> List[GraphEdge]:
        """Get edges for a session"""
        try:
            aql = "FOR edge IN edges FILTER edge.session_id == @session_id"
            bind_vars = {"session_id": session_id}

            if edge_type:
                aql += " AND edge.type == @edge_type"
                bind_vars["edge_type"] = edge_type

            aql += " RETURN edge"

            if self.use_sync:
                loop = asyncio.get_event_loop()
                cursor = await loop.run_in_executor(
                    None, lambda: self.db.aql.execute(aql, bind_vars=bind_vars)
                )
                documents = list(cursor)
            else:
                cursor = await self.db.aql.execute(aql, bind_vars=bind_vars)
                documents = [doc async for doc in cursor]

            edges = []
            for doc in documents:
                # Extract node IDs from _from and _to
                from_node = doc["_from"].split("/")[-1].replace(f"{session_id}_", "")
                to_node = doc["_to"].split("/")[-1].replace(f"{session_id}_", "")

                edge = GraphEdge(
                    from_node=from_node,
                    to_node=to_node,
                    type=doc["type"],
                    properties=doc["properties"],
                    confidence=doc.get("confidence", 1.0),
                )
                edges.append(edge)

            return edges

        except Exception as e:
            logger.error(f"Failed to get edges for session {session_id}: {e}")
            return []

    async def delete_node(self, session_id: str, node_id: str) -> bool:
        """Delete a node and its edges"""
        try:
            key = f"{session_id}_{node_id}"

            # Delete the node
            if self.use_sync:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, lambda: self.nodes_collection.delete(key)
                )
            else:
                await self.nodes_collection.delete(key)

            # Delete associated edges
            aql = """
                FOR edge IN edges 
                FILTER edge.session_id == @session_id 
                AND (edge._from == @from_ref OR edge._to == @to_ref)
                REMOVE edge IN edges
            """
            bind_vars = {
                "session_id": session_id,
                "from_ref": f"nodes/{key}",
                "to_ref": f"nodes/{key}",
            }

            if self.use_sync:
                await loop.run_in_executor(
                    None, lambda: self.db.aql.execute(aql, bind_vars=bind_vars)
                )
            else:
                await self.db.aql.execute(aql, bind_vars=bind_vars)

            logger.debug(
                f"Deleted node {node_id} and its edges for session {session_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to delete node {node_id}: {e}")
            return False

    async def get_graph_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of the graph for a session"""
        try:
            nodes = await self.get_nodes(session_id)
            edges = await self.get_edges(session_id)

            node_types = {}
            edge_types = {}

            for node in nodes:
                node_types[node.type] = node_types.get(node.type, 0) + 1

            for edge in edges:
                edge_types[edge.type] = edge_types.get(edge.type, 0) + 1

            return {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "node_types": node_types,
                "edge_types": edge_types,
                "nodes": [
                    {"id": n.id, "type": n.type, "summary": n.summary}
                    for n in nodes[:10]
                ],
                "edges": [
                    {"from": e.from_node, "to": e.to_node, "type": e.type}
                    for e in edges[:10]
                ],
            }

        except Exception as e:
            logger.error(f"Failed to get graph summary for session {session_id}: {e}")
            return {
                "total_nodes": 0,
                "total_edges": 0,
                "node_types": {},
                "edge_types": {},
                "nodes": [],
                "edges": [],
            }

    async def clear_session_graph(self, session_id: str) -> bool:
        """Clear all graph data for a session"""
        try:
            # Delete all nodes for the session
            aql_nodes = "FOR node IN nodes FILTER node.session_id == @session_id REMOVE node IN nodes"
            # Delete all edges for the session
            aql_edges = "FOR edge IN edges FILTER edge.session_id == @session_id REMOVE edge IN edges"

            if self.use_sync:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.db.aql.execute(
                        aql_nodes, bind_vars={"session_id": session_id}
                    ),
                )
                await loop.run_in_executor(
                    None,
                    lambda: self.db.aql.execute(
                        aql_edges, bind_vars={"session_id": session_id}
                    ),
                )
            else:
                await self.db.aql.execute(
                    aql_nodes, bind_vars={"session_id": session_id}
                )
                await self.db.aql.execute(
                    aql_edges, bind_vars={"session_id": session_id}
                )

            logger.info(f"Cleared graph data for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to clear graph for session {session_id}: {e}")
            return False

    async def find_path(self, session_id: str, from_node_id: str, to_node_id: str, max_depth: int = 5, algorithm: str = "shortest") -> Optional[Dict[str, Any]]:
        """
        Find path between two nodes using production-ready algorithms
        
        Args:
            session_id: Session identifier
            from_node_id: Starting node ID
            to_node_id: Target node ID
            max_depth: Maximum search depth
            algorithm: 'shortest', 'all_paths', 'dijkstra', 'bfs', 'dfs', 'astar'
            
        Returns:
            Dict with path info, distance, algorithm used, and metadata
        """
        try:
            # Construct node keys with session prefix
            from_key = f"{session_id}_{from_node_id}"
            to_key = f"{session_id}_{to_node_id}"
            from_ref = f"nodes/{from_key}"
            to_ref = f"nodes/{to_key}"
            
            if algorithm == "shortest":
                return await self._find_shortest_path(from_ref, to_ref, max_depth, session_id)
            elif algorithm == "all_paths":
                return await self._find_all_paths(from_ref, to_ref, max_depth, session_id)
            elif algorithm == "dijkstra":
                return await self._find_dijkstra_path(from_ref, to_ref, max_depth, session_id)
            elif algorithm == "bfs":
                return await self._find_bfs_path(from_ref, to_ref, max_depth, session_id)
            elif algorithm == "dfs":
                return await self._find_dfs_path(from_ref, to_ref, max_depth, session_id)
            elif algorithm == "astar":
                return await self._find_astar_path(from_ref, to_ref, max_depth, session_id)
            else:
                # Default to shortest path
                return await self._find_shortest_path(from_ref, to_ref, max_depth, session_id)
                
        except Exception as e:
            logger.error(f"Failed to find path from {from_node_id} to {to_node_id} using {algorithm}: {e}")
            return None

    async def _find_shortest_path(self, from_ref: str, to_ref: str, max_depth: int, session_id: str) -> Optional[Dict[str, Any]]:
        """Find shortest path using ArangoDB's built-in shortest path algorithm"""
        try:
            # Use ArangoDB's SHORTEST_PATH function with collection names
            aql = """
                FOR v, e IN OUTBOUND SHORTEST_PATH @from TO @to edges
                FILTER v.session_id == @session_id
                RETURN {
                    vertices: v,
                    edges: e
                }
            """
            
            bind_vars = {
                "from": from_ref,
                "to": to_ref,
                "session_id": session_id
            }

            path_data = await self._execute_aql(aql, bind_vars)
            
            if path_data and len(path_data) > 0:
                vertices = [item["vertices"] for item in path_data if item["vertices"]]
                edges = [item["edges"] for item in path_data if item["edges"]]
                
                if vertices:
                    return {
                        "algorithm": "shortest_path",
                        "path": self._format_path_result(vertices, edges),
                        "distance": len(vertices) - 1,
                        "weight": sum(edge.get("confidence", 1) for edge in edges if edge),
                        "found": True
                    }
            
            return {"algorithm": "shortest_path", "found": False, "path": [], "distance": -1}
                
        except Exception as e:
            logger.error(f"Shortest path algorithm failed: {e}")
            return {"algorithm": "shortest_path", "found": False, "path": [], "distance": -1, "error": str(e)}

    async def _find_bfs_path(self, from_ref: str, to_ref: str, max_depth: int, session_id: str) -> Optional[Dict[str, Any]]:
        """Breadth-First Search implementation using AQL"""
        try:
            # BFS using AQL traversal with breadth-first ordering
            aql = """
                FOR vertex, edge, path IN 1..@max_depth OUTBOUND @from edges
                    OPTIONS {order: "bfs", uniqueVertices: "global"}
                    FILTER vertex._id == @to AND vertex.session_id == @session_id
                    LIMIT 1
                    RETURN {
                        vertices: path.vertices,
                        edges: path.edges,
                        distance: LENGTH(path.vertices) - 1
                    }
            """
            
            bind_vars = {
                "from": from_ref,
                "to": to_ref,
                "max_depth": max_depth,
                "session_id": session_id
            }

            path_data = await self._execute_aql(aql, bind_vars)
            
            if path_data:
                result = path_data[0]
                return {
                    "algorithm": "bfs",
                    "path": self._format_path_result(result["vertices"], result["edges"]),
                    "distance": result["distance"],
                    "found": True
                }
            else:
                return {"algorithm": "bfs", "found": False, "path": [], "distance": -1}
                
        except Exception as e:
            logger.error(f"BFS algorithm failed: {e}")
            return {"algorithm": "bfs", "found": False, "path": [], "distance": -1, "error": str(e)}

    async def _find_dfs_path(self, from_ref: str, to_ref: str, max_depth: int, session_id: str) -> Optional[Dict[str, Any]]:
        """Depth-First Search with backtracking implementation"""
        try:
            # DFS using AQL traversal with depth-first ordering and backtracking
            aql = """
                FOR vertex, edge, path IN 1..@max_depth OUTBOUND @from edges
                    OPTIONS {order: "dfs", uniqueVertices: "path"}
                    FILTER vertex._id == @to AND vertex.session_id == @session_id
                    LIMIT 1
                    RETURN {
                        vertices: path.vertices,
                        edges: path.edges,
                        distance: LENGTH(path.vertices) - 1,
                        visited_nodes: LENGTH(path.vertices)
                    }
            """
            
            bind_vars = {
                "from": from_ref,
                "to": to_ref,
                "max_depth": max_depth,
                "session_id": session_id
            }

            path_data = await self._execute_aql(aql, bind_vars)
            
            if path_data:
                result = path_data[0]
                return {
                    "algorithm": "dfs_backtracking",
                    "path": self._format_path_result(result["vertices"], result["edges"]),
                    "distance": result["distance"],
                    "nodes_visited": result["visited_nodes"],
                    "found": True
                }
            else:
                return {"algorithm": "dfs_backtracking", "found": False, "path": [], "distance": -1}
                
        except Exception as e:
            logger.error(f"DFS with backtracking failed: {e}")
            return {"algorithm": "dfs_backtracking", "found": False, "path": [], "distance": -1, "error": str(e)}

    async def _find_dijkstra_path(self, from_ref: str, to_ref: str, max_depth: int, session_id: str) -> Optional[Dict[str, Any]]:
        """Dijkstra's algorithm for weighted shortest path"""
        try:
            # Dijkstra using ArangoDB's weighted shortest path with collection names 
            aql = """
                FOR v, e IN OUTBOUND SHORTEST_PATH @from TO @to edges
                OPTIONS {
                    weightAttribute: 'confidence', 
                    defaultWeight: 1
                }
                FILTER v.session_id == @session_id
                RETURN {
                    vertices: v,
                    edges: e
                }
            """
            
            bind_vars = {
                "from": from_ref,
                "to": to_ref,
                "session_id": session_id
            }

            path_data = await self._execute_aql(aql, bind_vars)
            
            if path_data and len(path_data) > 0:
                vertices = [item["vertices"] for item in path_data if item["vertices"]]
                edges = [item["edges"] for item in path_data if item["edges"]]
                
                if vertices:
                    edge_confidences = [edge.get("confidence", 1) for edge in edges if edge]
                    total_confidence = sum(edge_confidences)
                    avg_confidence = total_confidence / len(edge_confidences) if edge_confidences else 0
                    
                    return {
                        "algorithm": "dijkstra",
                        "path": self._format_path_result(vertices, edges),
                        "distance": len(vertices) - 1,
                        "total_confidence": total_confidence,
                        "avg_confidence": avg_confidence,
                        "found": True
                    }
            
            return {"algorithm": "dijkstra", "found": False, "path": [], "distance": -1}
                
        except Exception as e:
            logger.error(f"Dijkstra algorithm failed: {e}")
            return {"algorithm": "dijkstra", "found": False, "path": [], "distance": -1, "error": str(e)}

    async def _find_astar_path(self, from_ref: str, to_ref: str, max_depth: int, session_id: str) -> Optional[Dict[str, Any]]:
        """A* algorithm implementation using AQL with heuristic-based pathfinding"""
        try:
            # A* requires heuristic function - using embedding similarity as heuristic
            aql = """
                LET target_node = DOCUMENT(@to)
                FOR vertex, edge, path IN 1..@max_depth OUTBOUND @from edges
                    OPTIONS {order: "bfs", uniqueVertices: "path"}
                    FILTER vertex.session_id == @session_id
                    LET path_cost = LENGTH(path.vertices) - 1
                    LET heuristic = (
                        target_node.embedding != null AND vertex.embedding != null ? 
                        (1 - COSINE_SIMILARITY(vertex.embedding, target_node.embedding)) * @heuristic_weight : 
                        1
                    )
                    LET f_score = path_cost + heuristic
                    FILTER vertex._id == @to
                    SORT f_score
                    LIMIT 1
                    RETURN {
                        vertices: path.vertices,
                        edges: path.edges,
                        distance: path_cost,
                        heuristic_score: heuristic,
                        f_score: f_score
                    }
            """
            
            bind_vars = {
                "from": from_ref,
                "to": to_ref,
                "max_depth": max_depth,
                "session_id": session_id,
                "heuristic_weight": 2.0  # Adjustable heuristic weight
            }

            path_data = await self._execute_aql(aql, bind_vars)
            
            if path_data and len(path_data) > 0:
                result = path_data[0]
                return {
                    "algorithm": "astar",
                    "path": self._format_path_result(result["vertices"], result["edges"]),
                    "distance": result["distance"],
                    "heuristic_score": result.get("heuristic_score", 0),
                    "f_score": result.get("f_score", result["distance"]),
                    "found": True
                }
            else:
                return {"algorithm": "astar", "found": False, "path": [], "distance": -1}
                
        except Exception as e:
            logger.error(f"A* algorithm failed: {e}")
            return {"algorithm": "astar", "found": False, "path": [], "distance": -1, "error": str(e)}

    async def _find_all_paths(self, from_ref: str, to_ref: str, max_depth: int, session_id: str) -> Optional[Dict[str, Any]]:
        """Find all possible paths (use with caution - can be expensive)"""
        try:
            # Find multiple paths with different lengths
            aql = """
                FOR vertex, edge, path IN 1..@max_depth OUTBOUND @from edges
                    OPTIONS {uniqueVertices: "path"}
                    FILTER vertex._id == @to AND vertex.session_id == @session_id
                    RETURN {
                        vertices: path.vertices,
                        edges: path.edges,
                        distance: LENGTH(path.vertices) - 1
                    }
            """
            
            bind_vars = {
                "from": from_ref,
                "to": to_ref,
                "max_depth": max_depth,
                "session_id": session_id
            }

            path_data = await self._execute_aql(aql, bind_vars)
            
            if path_data:
                paths = []
                for result in path_data:
                    paths.append({
                        "path": self._format_path_result(result["vertices"], result["edges"]),
                        "distance": result["distance"]
                    })
                
                # Sort by distance (shortest first)
                paths.sort(key=lambda x: x["distance"])
                
                return {
                    "algorithm": "all_paths",
                    "paths": paths,
                    "count": len(paths),
                    "shortest_distance": paths[0]["distance"] if paths else -1,
                    "found": len(paths) > 0
                }
            else:
                return {"algorithm": "all_paths", "found": False, "paths": [], "count": 0}
                
        except Exception as e:
            logger.error(f"All paths algorithm failed: {e}")
            return {"algorithm": "all_paths", "found": False, "paths": [], "count": 0, "error": str(e)}

    def _format_path_result(self, vertices: List[Dict], edges: List[Dict]) -> List[Dict[str, Any]]:
        """Format path result for consistent output"""
        formatted_path = []
        
        for i, vertex in enumerate(vertices):
            step = {
                "node_id": vertex.get("node_id", vertex.get("_key", "")),
                "type": vertex.get("type", "unknown"),
                "summary": vertex.get("summary", ""),
                "properties": vertex.get("properties", {}),
                "step": i
            }
            
            # Add edge information if not the last vertex
            if i < len(edges):
                edge = edges[i]
                step["edge"] = {
                    "type": edge.get("type", "unknown"),
                    "confidence": edge.get("confidence", 1.0),
                    "properties": edge.get("properties", {})
                }
            
            formatted_path.append(step)
        
        return formatted_path

    async def _execute_aql(self, aql: str, bind_vars: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute AQL query with proper async/sync handling"""
        if self.use_sync:
            loop = asyncio.get_event_loop()
            cursor = await loop.run_in_executor(
                None, lambda: self.db.aql.execute(aql, bind_vars=bind_vars)
            )
            return list(cursor)
        else:
            cursor = await self.db.aql.execute(aql, bind_vars=bind_vars)
            return [doc async for doc in cursor]

    async def get_neighbors(self, session_id: str, node_id: str, direction: str = "both") -> List[Dict[str, Any]]:
        """Get neighboring nodes (connected via edges)"""
        try:
            node_key = f"{session_id}_{node_id}"
            node_ref = f"nodes/{node_key}"
            
            # Build AQL query based on direction
            if direction.lower() == "outbound":
                aql = """
                    FOR vertex, edge IN 1..1 OUTBOUND @node_ref edges
                        FILTER vertex.session_id == @session_id
                        RETURN {
                            node: vertex,
                            edge: edge,
                            direction: "outbound"
                        }
                """
            elif direction.lower() == "inbound":
                aql = """
                    FOR vertex, edge IN 1..1 INBOUND @node_ref edges
                        FILTER vertex.session_id == @session_id
                        RETURN {
                            node: vertex,
                            edge: edge,
                            direction: "inbound"
                        }
                """
            else:  # both directions - use simpler approach
                aql = """
                    FOR vertex, edge IN 1..1 ANY @node_ref edges
                        FILTER vertex.session_id == @session_id
                        RETURN {
                            node: vertex,
                            edge: edge,
                            direction: "both"
                        }
                """

            bind_vars = {
                "node_ref": node_ref,
                "session_id": session_id
            }

            if self.use_sync:
                loop = asyncio.get_event_loop()
                cursor = await loop.run_in_executor(
                    None, lambda: self.db.aql.execute(aql, bind_vars=bind_vars)
                )
                neighbors_data = list(cursor)
            else:
                cursor = await self.db.aql.execute(aql, bind_vars=bind_vars)
                neighbors_data = [doc async for doc in cursor]

            # Format neighbor data
            neighbors = []
            for neighbor_info in neighbors_data:
                node_data = neighbor_info['node']
                edge_data = neighbor_info['edge']
                
                neighbors.append({
                    'node_id': node_data['node_id'],
                    'type': node_data['type'],
                    'summary': node_data['summary'],
                    'properties': node_data.get('properties', {}),
                    'relationship': {
                        'type': edge_data['type'],
                        'direction': neighbor_info['direction'],
                        'properties': edge_data.get('properties', {})
                    }
                })

            logger.debug(f"Found {len(neighbors)} neighbors for node {node_id} (direction: {direction})")
            return neighbors

        except Exception as e:
            logger.error(f"Failed to get neighbors for node {node_id}: {e}")
            return []

    async def get_connected_subgraph(self, session_id: str, start_node_id: str, max_depth: int = 3) -> Dict[str, Any]:
        """Get a connected subgraph starting from a specific node"""
        try:
            node_key = f"{session_id}_{start_node_id}"
            node_ref = f"nodes/{node_key}"
            
            # AQL query to traverse and collect connected nodes and edges
            aql = """
                FOR vertex, edge, path IN 0..@max_depth ANY @start_node edges
                    FILTER vertex.session_id == @session_id
                    COLLECT node = vertex, edges = edge INTO groups
                    RETURN {
                        node: node,
                        edges: edges[* FILTER CURRENT != null]
                    }
            """
            
            bind_vars = {
                "start_node": node_ref,
                "session_id": session_id,
                "max_depth": max_depth
            }

            if self.use_sync:
                loop = asyncio.get_event_loop()
                cursor = await loop.run_in_executor(
                    None, lambda: self.db.aql.execute(aql, bind_vars=bind_vars)
                )
                subgraph_data = list(cursor)
            else:
                cursor = await self.db.aql.execute(aql, bind_vars=bind_vars)
                subgraph_data = [doc async for doc in cursor]

            # Process the subgraph data
            nodes = []
            edges = []
            
            for item in subgraph_data:
                if item['node']:
                    node_data = item['node']
                    nodes.append({
                        'id': node_data['node_id'],
                        'type': node_data['type'],
                        'summary': node_data['summary'],
                        'properties': node_data.get('properties', {}),
                        'confidence': node_data.get('confidence', 1.0)
                    })
                
                for edge_data in item.get('edges', []):
                    if edge_data:
                        # Extract node IDs from _from and _to
                        from_node = edge_data['_from'].split('/')[-1].replace(f"{session_id}_", "")
                        to_node = edge_data['_to'].split('/')[-1].replace(f"{session_id}_", "")
                        
                        edges.append({
                            'from': from_node,
                            'to': to_node,
                            'type': edge_data['type'],
                            'properties': edge_data.get('properties', {}),
                            'confidence': edge_data.get('confidence', 1.0)
                        })

            subgraph = {
                'start_node': start_node_id,
                'max_depth': max_depth,
                'nodes': nodes,
                'edges': edges,
                'node_count': len(nodes),
                'edge_count': len(edges)
            }

            logger.debug(f"Generated subgraph from {start_node_id}: {len(nodes)} nodes, {len(edges)} edges")
            return subgraph

        except Exception as e:
            logger.error(f"Failed to get connected subgraph from {start_node_id}: {e}")
            return {
                'start_node': start_node_id,
                'max_depth': max_depth,
                'nodes': [],
                'edges': [],
                'node_count': 0,
                'edge_count': 0
            }

    # ===== GRAPH PRUNING AND MEMORY MANAGEMENT =====
    
    async def prune_graph(self, session_id: str, max_nodes: int = 1000, similarity_threshold: float = 0.9) -> Dict[str, Any]:
        """
        Enhanced prune graph for aggressive memory efficiency using blueprint specifications:
        - Merge similar nodes (embedding cosine similarity > threshold)
        - Summarize low-importance event chains
        - Archive low-utility branches with actual deletion
        - Remove duplicate/redundant nodes by type
        """
        try:
            pruning_stats = {
                "nodes_before": 0,
                "nodes_after": 0,
                "merged_nodes": 0,
                "archived_nodes": 0,
                "summarized_chains": 0
            }
            
            # Get current graph statistics
            current_nodes = await self.get_nodes(session_id)
            pruning_stats["nodes_before"] = len(current_nodes)
            
            if len(current_nodes) <= max_nodes:
                logger.info(f"Graph size ({len(current_nodes)}) within limits, no pruning needed")
                pruning_stats["nodes_after"] = len(current_nodes)
                return pruning_stats
            
            # Step 1: Merge similar nodes based on enhanced similarity
            merged_count = await self._merge_similar_nodes(session_id, similarity_threshold)
            pruning_stats["merged_nodes"] = merged_count
            
            # Step 2: Summarize low-importance event chains
            summarized_count = await self._summarize_event_chains(session_id)
            pruning_stats["summarized_chains"] = summarized_count
            
            # Step 3: Remove duplicate nodes by type and properties
            duplicate_count = await self._remove_duplicate_nodes(session_id)
            pruning_stats["archived_nodes"] += duplicate_count
            
            # Step 4: Archive low-utility branches with aggressive deletion
            archived_count = await self._archive_low_utility_branches(session_id, max_nodes)
            pruning_stats["archived_nodes"] += archived_count
            
            # Get final statistics
            final_nodes = await self.get_nodes(session_id)
            pruning_stats["nodes_after"] = len(final_nodes)
            
            logger.info(f"Graph pruning completed for session {session_id}: {pruning_stats}")
            return pruning_stats
            
        except Exception as e:
            logger.error(f"Graph pruning failed for session {session_id}: {e}")
            return {"error": str(e)}
    
    async def _remove_duplicate_nodes(self, session_id: str) -> int:
        """Remove duplicate nodes with identical properties"""
        try:
            # Find nodes with identical summaries and types - simplified approach
            aql = """
                FOR node1 IN nodes
                    FILTER node1.session_id == @session_id
                    FOR node2 IN nodes
                        FILTER node2.session_id == @session_id
                        FILTER node1._id < node2._id
                        FILTER node1.type == node2.type
                        FILTER node1.summary == node2.summary
                        RETURN node2
            """
            
            duplicate_nodes = await self._execute_aql(aql, {
                "session_id": session_id
            })
            
            removed_count = 0
            for node in duplicate_nodes:
                try:
                    await self._archive_node(node, session_id)
                    removed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to remove duplicate node: {e}")
                    continue
                    
            if removed_count > 0:
                logger.info(f"Removed {removed_count} duplicate nodes")
            return removed_count
            
        except Exception as e:
            logger.error(f"Duplicate removal failed: {e}")
            return 0
    
    async def _merge_similar_nodes(self, session_id: str, similarity_threshold: float) -> int:
        """Merge nodes with high similarity (both embedding and semantic)"""
        try:
            # Enhanced similarity detection using multiple criteria
            aql = """
                FOR node1 IN nodes
                    FILTER node1.session_id == @session_id
                    FOR node2 IN nodes
                        FILTER node2.session_id == @session_id
                        FILTER node1._id < node2._id
                        FILTER node1.type == node2.type  // Only merge same types
                        
                        // Calculate multiple similarity metrics
                        LET embedding_sim = node1.embedding != null AND node2.embedding != null ? 
                            COSINE_SIMILARITY(node1.embedding, node2.embedding) : 0
                        LET text_sim = TOKENS(LOWER(node1.summary), "text_en") && TOKENS(LOWER(node2.summary), "text_en") ?
                            LENGTH(INTERSECTION(TOKENS(LOWER(node1.summary), "text_en"), TOKENS(LOWER(node2.summary), "text_en"))) / 
                            LENGTH(UNION(TOKENS(LOWER(node1.summary), "text_en"), TOKENS(LOWER(node2.summary), "text_en"))) : 0
                        LET combined_sim = (embedding_sim * 0.7) + (text_sim * 0.3)
                        
                        FILTER combined_sim > @threshold
                        SORT combined_sim DESC
                        LIMIT 20  // Process top 20 similar pairs to avoid overwhelming
                        RETURN {
                            node1: node1,
                            node2: node2,
                            similarity: combined_sim
                        }
            """
            
            similar_pairs = await self._execute_aql(aql, {
                "session_id": session_id,
                "threshold": similarity_threshold * 0.8  # Lower threshold for more aggressive merging
            })
            
            merged_count = 0
            for pair in similar_pairs:
                try:
                    # Merge node2 into node1 and remove node2
                    await self._merge_nodes(pair["node1"], pair["node2"], session_id)
                    merged_count += 1
                except Exception as e:
                    logger.warning(f"Failed to merge nodes: {e}")
                    continue
                
            logger.info(f"Merged {merged_count} similar node pairs")
            return merged_count
            
        except Exception as e:
            logger.error(f"Node merging failed: {e}")
            return 0
    
    async def _merge_nodes(self, primary_node: Dict, secondary_node: Dict, session_id: str):
        """Merge secondary node into primary node with enhanced robustness"""
        try:
            # Create enhanced combined information
            primary_summary = primary_node.get('summary', '')
            secondary_summary = secondary_node.get('summary', '')
            
            # Intelligent summary combination (avoid duplication)
            if primary_summary and secondary_summary:
                if secondary_summary not in primary_summary:
                    combined_summary = f"{primary_summary}; {secondary_summary}"
                else:
                    combined_summary = primary_summary
            else:
                combined_summary = primary_summary or secondary_summary
            
            # Combine confidence scores intelligently
            primary_conf = primary_node.get('confidence', 1.0)
            secondary_conf = secondary_node.get('confidence', 1.0)
            combined_confidence = (primary_conf + secondary_conf) / 2  # Average for stability
            
            # Update primary node with merged information
            aql_update = """
                UPDATE @node_key WITH {
                    summary: @new_summary,
                    confidence: @new_confidence,
                    merged_from: PUSH(@merged_list, @secondary_id, true),
                    last_updated: @timestamp
                } IN nodes
            """
            
            await self._execute_aql(aql_update, {
                "node_key": primary_node["_key"],
                "new_summary": combined_summary[:1000],  # Limit summary length
                "new_confidence": combined_confidence,
                "merged_list": primary_node.get("merged_from", []),
                "secondary_id": secondary_node["_id"],
                "timestamp": datetime.now().isoformat()
            })
            
            # Update edges pointing to secondary node to point to primary
            aql_edges = """
                FOR edge IN edges
                    FILTER edge.session_id == @session_id
                    FILTER edge._to == @secondary_ref OR edge._from == @secondary_ref
                    UPDATE edge WITH {
                        _to: edge._to == @secondary_ref ? @primary_ref : edge._to,
                        _from: edge._from == @secondary_ref ? @primary_ref : edge._from
                    } IN edges
            """
            
            await self._execute_aql(aql_edges, {
                "session_id": session_id,
                "secondary_ref": secondary_node["_id"],
                "primary_ref": primary_node["_id"]
            })
            
            # Remove secondary node completely
            secondary_node_id = secondary_node.get("node_id", secondary_node.get("_key", ""))
            await self.delete_node(session_id, secondary_node_id)
            
            logger.debug(f"Successfully merged node {secondary_node_id} into {primary_node.get('node_id', primary_node.get('_key', ''))}")
            
        except Exception as e:
            logger.error(f"Failed to merge nodes: {e}")
            raise  # Re-raise to allow caller to handle
    
    async def _summarize_event_chains(self, session_id: str) -> int:
        """Summarize chains of low-importance events"""
        try:
            # Find chains of events with low confidence
            aql = """
                FOR node IN nodes
                    FILTER node.session_id == @session_id
                    FILTER node.type == "event"
                    FILTER node.confidence < @low_confidence_threshold
                    COLLECT parent = node.properties.parent_event INTO chain_nodes
                    FILTER LENGTH(chain_nodes) >= @min_chain_length
                    RETURN {
                        parent_event: parent,
                        chain: chain_nodes
                    }
            """
            
            chains = await self._execute_aql(aql, {
                "session_id": session_id,
                "low_confidence_threshold": 0.7,
                "min_chain_length": 3
            })
            
            summarized_count = 0
            for chain in chains:
                # Create summary node
                await self._create_summary_node(chain, session_id)
                summarized_count += 1
                
            return summarized_count
            
        except Exception as e:
            logger.error(f"Event chain summarization failed: {e}")
            return 0
    
    async def _create_summary_node(self, chain: Dict, session_id: str):
        """Create a summary node from event chain"""
        try:
            chain_summaries = [node["summary"] for node in chain["chain"]]
            combined_summary = f"Summary of {len(chain_summaries)} events: " + "; ".join(chain_summaries[:3])
            
            # Create summary node
            summary_node = GraphNode(
                id=f"summary_{int(time.time())}",
                type="event_summary",
                summary=combined_summary,
                properties={
                    "original_count": len(chain_summaries),
                    "summarized_events": [node["node_id"] for node in chain["chain"]],
                    "confidence": 0.8
                }
            )
            
            await self.add_node(session_id, summary_node)
            
            # Remove original nodes
            for node in chain["chain"]:
                await self.delete_node(session_id, node["node_id"])
                
        except Exception as e:
            logger.error(f"Failed to create summary node: {e}")
    
    async def _archive_low_utility_branches(self, session_id: str, target_max_nodes: int) -> int:
        """Archive low-utility branches to meet node limit with improved efficiency"""
        try:
            # Get current node count
            current_nodes = await self.get_nodes(session_id)
            current_count = len(current_nodes)
            nodes_to_remove = max(0, current_count - target_max_nodes)
            
            if nodes_to_remove == 0:
                return 0
            
            # Enhanced utility scoring that considers multiple factors
            aql = """
                FOR node IN nodes
                    FILTER node.session_id == @session_id
                    FILTER node.type != "core"  // Protect core nodes
                    LET edge_count = LENGTH(FOR edge IN edges 
                                          FILTER (edge._from == node._id OR edge._to == node._id)
                                          AND edge.session_id == @session_id
                                          RETURN 1)
                    LET confidence = node.confidence || 0.5
                    LET recency = node.created_at ? 
                        (DATE_NOW() - DATE_TIMESTAMP(node.created_at)) / (1000 * 60 * 60 * 24) : 999
                    LET utility_score = (confidence * 0.4) + 
                                       (edge_count * 0.3) + 
                                       (1 / (recency + 1) * 0.3)  // More recent = higher score
                    SORT utility_score ASC
                    LIMIT @nodes_to_remove
                    RETURN node
            """
            
            low_utility_nodes = await self._execute_aql(aql, {
                "session_id": session_id,
                "nodes_to_remove": nodes_to_remove
            })
            
            archived_count = 0
            for node in low_utility_nodes:
                # Actually delete the node for true memory reduction
                await self._archive_node(node, session_id)
                archived_count += 1
                
            logger.info(f"Archived {archived_count} low-utility nodes for memory efficiency")
            return archived_count
            
        except Exception as e:
            logger.error(f"Branch archiving failed: {e}")
            return 0
    
    async def _archive_node(self, node: Dict, session_id: str):
        """Archive a node by actually removing it from the database for memory efficiency"""
        try:
            # Actually delete the node and its edges for true memory reduction
            node_id = node.get("node_id", node.get("_key", ""))
            
            # First remove all edges connected to this node
            aql_remove_edges = """
                FOR edge IN edges
                    FILTER edge.session_id == @session_id
                    FILTER edge._from == @node_ref OR edge._to == @node_ref
                    REMOVE edge IN edges
            """
            
            await self._execute_aql(aql_remove_edges, {
                "session_id": session_id,
                "node_ref": node["_id"]
            })
            
            # Then remove the node itself
            aql_remove_node = """
                REMOVE @node_key IN nodes
            """
            
            await self._execute_aql(aql_remove_node, {
                "node_key": node["_key"]
            })
            
            logger.debug(f"Successfully archived (deleted) node {node_id} for memory efficiency")
            
        except Exception as e:
            logger.error(f"Failed to archive node: {e}")

    async def close(self) -> None:
        """Close the connection"""
        try:
            if self.client and hasattr(self.client, "close"):
                if self.use_sync:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self.client.close)
                else:
                    await self.client.close()
            self.connected = False
            logger.info("Closed ArangoDB connection")
        except Exception as e:
            logger.error(f"Error closing ArangoDB connection: {e}")


async def create_arango_client(config: Dict[str, Any]) -> Optional[ArangoGraphClient]:
    """Factory function to create ArangoDB client"""
    client = ArangoGraphClient(config)
    if await client.connect():
        return client
    return None
