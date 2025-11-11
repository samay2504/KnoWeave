"""
Graph Manager Agent - Human-AI Co-Creation System
Blueprint-compliant knowledge graph management agent
Agent 4 of 6: Manages relationships and dependencies
"""

import asyncio
import logging
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime
from collections import defaultdict, deque

from utils.logging_cfg import get_agent_logger

logger = get_agent_logger("graph_manager")


class GraphNode:
    """Represents a node in the knowledge graph"""

    def __init__(
        self,
        node_id: str,
        node_type: str,
        content: str,
        metadata: Dict[str, Any] = None,
    ):
        self.id = node_id
        self.type = node_type
        self.content = content
        self.metadata = metadata or {}
        # Ensure domain is part of metadata for new nodes
        if 'domain' not in self.metadata:
            self.metadata['domain'] = 'unknown'
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.connections = set()
        self.properties = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary representation"""
        return {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "connections": list(self.connections),
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphNode":
        """Create node from dictionary representation"""
        node = cls(data["id"], data["type"], data["content"], data.get("metadata", {}))
        node.created_at = data.get("created_at", node.created_at)
        node.updated_at = data.get("updated_at", node.updated_at)
        node.connections = set(data.get("connections", []))
        node.properties = data.get("properties", {})
        return node


class GraphEdge:
    """Represents an edge/relationship in the knowledge graph"""

    def __init__(
        self,
        edge_id: str,
        source_id: str,
        target_id: str,
        relation_type: str,
        weight: float = 1.0,
        metadata: Dict[str, Any] = None,
    ):
        self.id = edge_id
        self.source_id = source_id
        self.target_id = target_id
        self.relation_type = relation_type
        self.weight = weight
        self.metadata = metadata or {}
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert edge to dictionary representation"""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type,
            "weight": self.weight,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphEdge":
        """Create edge from dictionary representation"""
        edge = cls(
            data["id"],
            data["source_id"],
            data["target_id"],
            data["relation_type"],
            data.get("weight", 1.0),
            data.get("metadata", {}),
        )
        edge.created_at = data.get("created_at", edge.created_at)
        edge.updated_at = data.get("updated_at", edge.updated_at)
        return edge


class GraphManagerAgent:
    """
    Graph Manager Agent - Fourth of the 6 blueprint agents
    Manages knowledge graph: nodes, edges, relationships, dependencies
    Uses dynamic prompts from PTG, no hardcoded topic logic
    """

    def __init__(self, config: Dict[str, Any], llm_provider=None):
        self.config = config
        self.llm_provider = llm_provider

        # In-memory graph storage (would use database in production)
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[str, GraphEdge] = {}
        self.adjacency_list: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)

        # Node type hierarchies and relationships, now extended for multi-domain support
        self.node_types = {
            "story": ["character", "setting", "event", "theme", "plot_point", "conflict"],
            "education": ["objective", "activity", "material", "assessment", "concept", "learning_objective"],
            "research": ["hypothesis", "method_step", "data_source", "finding", "citation"],
            "product": ["feature", "user_story", "epic", "task", "bug_report", "success_metric"],
            "marketing": ["campaign_task", "kpi", "target_audience", "channel", "creative_asset"],
            "engineering": ["component", "service", "dependency", "test_case", "deployment_task"],
            "generic": ["node", "entity", "event", "concept"] # Fallback types
        }

        # Relationship types for different content domains
        self.relation_types = {
            "structural": ["contains", "part_of", "follows", "precedes", "depends_on"],
            "semantic": ["related_to", "similar_to", "opposite_of", "example_of", "causes"],
            "narrative": ["character_in", "setting_for", "conflicts_with", "resolves"],
            "educational": ["teaches", "requires", "builds_on", "demonstrates", "assesses"],
            "product": ["implements", "verifies", "blocked_by"],
            "generic": ["connects_to"] # Fallback relation
        }

        # Graph analysis algorithms
        self.analysis_methods = {
            "centrality": self._calculate_centrality,
            "clustering": self._detect_clusters,
            "paths": self._find_paths,
            "dependencies": self._analyze_dependencies,
        }

    async def initialize(self):
        """Initialize the graph manager agent"""
        logger.info("Initializing Graph Manager Agent")
        # Initialize graph structures
        self.nodes.clear()
        self.edges.clear()
        self.adjacency_list.clear()
        self.reverse_adjacency.clear()
        logger.info("Graph Manager Agent initialized successfully")

    async def cleanup(self):
        """Cleanup graph manager agent resources"""
        logger.info("Cleaning up Graph Manager Agent")
        # Clear graph data
        self.nodes.clear()
        self.edges.clear()
        self.adjacency_list.clear()
        self.reverse_adjacency.clear()
        logger.info("Graph Manager Agent cleanup completed")

    async def invoke(
        self, workspace, agent_config
    ) -> Dict[str, Any]:
        """
        Main agent invoke method - manages knowledge graph for workspace
        Uses dynamic prompts from Session Manager's PTG
        """
        # Accept both dict and Pydantic model input for workspace and agent_config
        from server.utils.schemas import WorkspaceSchema
        if not isinstance(workspace, dict) and hasattr(workspace, 'dict'):
            workspace = workspace.dict()
        if not isinstance(agent_config, dict) and hasattr(agent_config, 'dict'):
            agent_config = agent_config.dict()
        # Optionally validate workspace schema
        try:
            workspace = WorkspaceSchema.parse_obj(workspace).dict()
        except Exception:
            pass
        # Get workspace data
        topic_content = workspace.get("topic_content", "")
        perception_data = workspace.get("perception_analysis", {})
        planning_data = workspace.get("planner_analysis", {})

        # Load existing graph if available
        existing_graph = workspace.get("knowledge_graph", {})
        if existing_graph:
            await self._load_graph(existing_graph)

        # Extract entities and relationships from current content
        await self._extract_entities(perception_data, planning_data)
        await self._extract_relationships(topic_content, perception_data, planning_data)

        # Analyze graph structure
        graph_analysis = await self._analyze_graph()

        # Generate recommendations
        recommendations = await self._generate_recommendations(
            workspace, graph_analysis
        )

        # Create visualization data
        visualization_data = await self._create_visualization_data()

        # Export graph for persistence
        graph_export = await self._export_graph()

        result = {
            "graph_analysis": graph_analysis,
            "recommendations": recommendations,
            "visualization": visualization_data,
            "graph_data": graph_export,
            "metadata": {
                "node_count": len(self.nodes),
                "edge_count": len(self.edges),
                "graph_density": self._calculate_density(),
                "timestamp": datetime.now().isoformat(),
            },
        }

        logger.debug(
            f"Graph analysis complete - {len(self.nodes)} nodes, {len(self.edges)} edges"
        )
        return result

    async def get_graph_structure(self, session_id: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Production-ready method to get graph structure for API consumption
        Returns nodes and edges formatted for frontend visualization
        
        This method is called by the /api/session/{id}/graph endpoint
        """
        nodes = []
        edges = []
        
        # Convert internal nodes to API format
        for node_id, node in self.nodes.items():
            node_dict = {
                "id": node.id,
                "type": node.node_type,
                "title": node.content[:50] if len(node.content) > 50 else node.content,
                "text": node.content,
                "confidence": node.importance,
                "metadata": node.metadata or {},
                "created_at": node.created_at.isoformat() if hasattr(node.created_at, 'isoformat') else str(node.created_at)
            }
            
            # Add actor if it's a character or event node
            if node.node_type == "character":
                node_dict["actor"] = node.content
            elif "actor" in node.metadata:
                node_dict["actor"] = node.metadata["actor"]
                
            nodes.append(node_dict)
        
        # Convert internal edges to API format
        for edge_id, edge in self.edges.items():
            edge_dict = {
                "id": edge.id,
                "source": edge.source_id,
                "target": edge.target_id,
                "type": edge.relation_type,
                "confidence": edge.confidence,
                "metadata": edge.metadata or {}
            }
            edges.append(edge_dict)
        
        logger.info(f"Returning graph structure: {len(nodes)} nodes, {len(edges)} edges for session {session_id}")
        return nodes, edges

    async def _load_graph(self, graph_data: Dict[str, Any]) -> None:
        """Load existing graph from workspace data"""
        # Load nodes
        for node_data in graph_data.get("nodes", []):
            node = GraphNode.from_dict(node_data)
            self.nodes[node.id] = node

        # Load edges and rebuild adjacency lists
        for edge_data in graph_data.get("edges", []):
            edge = GraphEdge.from_dict(edge_data)
            self.edges[edge.id] = edge
            self.adjacency_list[edge.source_id].add(edge.target_id)
            self.reverse_adjacency[edge.target_id].add(edge.source_id)

            # Update node connections
            if edge.source_id in self.nodes:
                self.nodes[edge.source_id].connections.add(edge.target_id)
            if edge.target_id in self.nodes:
                self.nodes[edge.target_id].connections.add(edge.source_id)

        logger.info(
            f"Loaded graph with {len(self.nodes)} nodes and {len(self.edges)} edges"
        )

    async def _extract_entities(
        self, perception_data: Dict[str, Any], planning_data: Dict[str, Any]
    ) -> None:
        """Extract entities from perception and planning data to create nodes"""

        # Get domain information from perception data metadata
        perception_metadata = perception_data.get("metadata", {})
        topic_family = perception_metadata.get("topic_family", "unknown")
        topic_role = perception_metadata.get("topic_role", "unknown")

        # Extract entities from perception data
        entities = perception_data.get("entities", [])
        for entity in entities:
            node_id = self._generate_node_id(entity["text"])
            if node_id not in self.nodes:
                node_type = self._map_entity_to_node_type(entity["label"])
                node = GraphNode(
                    node_id,
                    node_type,
                    entity["text"],
                    {
                        "entity_type": entity["label"],
                        "confidence": entity.get("confidence", 1.0),
                        "source": "perception",
                        "domain": topic_family,  # Add domain metadata
                        "topic_role": topic_role,
                        "node_category": self._get_domain_node_category(entity["label"], topic_family),
                    },
                )
                self.nodes[node_id] = node

        # Extract characters as specialized nodes
        characters = perception_data.get("characters", [])
        for character in characters:
            node_id = self._generate_node_id(character["name"])
            if node_id not in self.nodes:
                node = GraphNode(
                    node_id,
                    "character",
                    character["name"],
                    {
                        "traits": character.get("traits", []),
                        "mentions": character.get("mentions", 0),
                        "confidence": character.get("confidence", 1.0),
                        "source": "perception",
                    },
                )
                self.nodes[node_id] = node

        # Extract events as nodes
        events = perception_data.get("events", [])
        for i, event in enumerate(events):
            node_id = self._generate_node_id(f"event_{i}")
            if node_id not in self.nodes:
                node = GraphNode(
                    node_id,
                    "event",
                    event["summary"],
                    {
                        "actors": event.get("actors", []),
                        "confidence": event.get("confidence", 1.0),
                        "sentence_index": event.get("sentence_index", i),
                        "source": "perception",
                    },
                )
                self.nodes[node_id] = node

        # Extract planning elements as nodes
        content_plan = planning_data.get("content_plan", {})
        outline = planning_data.get("outline", [])

        for outline_item in outline:
            section = outline_item.get("section", "")
            if section:
                node_id = self._generate_node_id(f"section_{section}")
                if node_id not in self.nodes:
                    node = GraphNode(
                        node_id,
                        "section",
                        section,
                        {
                            "order": outline_item.get("order", 0),
                            "estimated_length": outline_item.get("estimated_length", 0),
                            "key_points": outline_item.get("key_points", []),
                            "source": "planning",
                        },
                    )
                    self.nodes[node_id] = node

    def _map_entity_to_node_type(self, entity_label: str) -> str:
        """Map NER entity labels to graph node types"""
        mapping = {
            "PERSON": "character",
            "PER": "character",
            "LOCATION": "setting",
            "LOC": "setting",
            "GPE": "setting",
            "TIME": "temporal",
            "DATE": "temporal",
            "EVENT": "event",
            "ORG": "organization",
            "PRODUCT": "object",
            "WORK_OF_ART": "object",
            # Additional mappings for multi-domain support
            "CONCEPT": "concept",
            "EDUCATION_LEVEL": "demographic",
            "HEALTH_TOPIC": "concept",
            "TARGET_AUDIENCE": "demographic",
            "HEALTH_CONDITION": "medical_concept",
            "METHODOLOGY": "process",
            "TREATMENT": "intervention",
            "METRIC": "measurement",
            "POPULATION": "demographic",
            "ARCHITECTURE_PATTERN": "technical_concept",
            "SYSTEM_TYPE": "technical_artifact",
            "PERFORMANCE_REQUIREMENT": "constraint",
            "INTEGRATION": "technical_component",
            "DATA_SOURCE": "information_source",
            "OBJECTIVE": "goal",
            "LEGAL_CONCEPT": "legal_framework",
            "REGULATION": "policy",
            "TIMEFRAME": "temporal",
            "CERTIFICATION": "credential",
            "CONSTRAINT": "limitation",
            "DELIVERABLE": "artifact",
            "TECHNOLOGY": "tool",
            "STANDARD": "framework",
            "ASSISTIVE_TECH": "accessibility_tool",
            "INTERACTION_MODE": "interface_method",
        }
        return mapping.get(entity_label, "entity")

    def _get_domain_node_category(self, entity_label: str, topic_family: str) -> str:
        """Get domain-specific node category for enhanced graph organization"""
        # Domain-specific categorizations
        domain_categories = {
            "story": {
                "PERSON": "character",
                "LOCATION": "setting", 
                "EVENT": "plot_point",
                "CONCEPT": "theme",
                "PRODUCT": "story_element"
            },
            "education": {
                "CONCEPT": "learning_concept",
                "PERSON": "learner_or_instructor",
                "EDUCATION_LEVEL": "audience",
                "OBJECTIVE": "learning_objective",
                "EVENT": "learning_activity"
            },
            "research": {
                "METHODOLOGY": "research_method",
                "POPULATION": "study_population",
                "METRIC": "research_metric",
                "CONCEPT": "research_concept",
                "OBJECTIVE": "research_question"
            },
            "product": {
                "PRODUCT": "product_entity",
                "METRIC": "success_metric",
                "TARGET_AUDIENCE": "user_segment",
                "CONCEPT": "product_concept",
                "CONSTRAINT": "product_constraint"
            },
            "healthcare_nonclinical": {
                "HEALTH_TOPIC": "wellness_concept",
                "HEALTH_CONDITION": "health_indicator",
                "TARGET_AUDIENCE": "health_demographic",
                "CONCEPT": "health_principle"
            },
            "engineering": {
                "ARCHITECTURE_PATTERN": "system_pattern",
                "TECHNOLOGY": "technical_tool",
                "PERFORMANCE_REQUIREMENT": "system_requirement",
                "SYSTEM_TYPE": "system_component"
            }
        }
        
        domain_map = domain_categories.get(topic_family, {})
        return domain_map.get(entity_label, entity_label.lower())

    def _generate_node_id(self, content: str) -> str:
        """Generate unique node ID from content"""
        # Normalize content for ID generation
        normalized = content.lower().replace(" ", "_").replace("-", "_")
        normalized = "".join(c for c in normalized if c.isalnum() or c == "_")
        return f"node_{normalized}_{str(uuid.uuid4())[:8]}"

    async def _extract_relationships(
        self,
        topic_content: str,
        perception_data: Dict[str, Any],
        planning_data: Dict[str, Any],
    ) -> None:
        """Extract relationships between entities to create edges"""

        # Extract character-event relationships
        await self._extract_character_event_relationships(perception_data)

        # Extract sequential relationships from outline
        await self._extract_sequential_relationships(planning_data)

        # Extract co-occurrence relationships
        await self._extract_cooccurrence_relationships(topic_content)

        # Use LLM for advanced relationship extraction if available
        if self.llm_provider:
            try:
                await self._extract_llm_relationships(topic_content, perception_data)
            except Exception as e:
                logger.warning(f"LLM relationship extraction failed: {e}")

    async def _extract_character_event_relationships(
        self, perception_data: Dict[str, Any]
    ) -> None:
        """Extract relationships between characters and events"""
        characters = perception_data.get("characters", [])
        events = perception_data.get("events", [])

        character_nodes = {
            node.content: node
            for node in self.nodes.values()
            if node.type == "character"
        }
        event_nodes = [node for node in self.nodes.values() if node.type == "event"]

        for event_node in event_nodes:
            event_actors = event_node.metadata.get("actors", [])
            for actor_name in event_actors:
                if actor_name in character_nodes:
                    character_node = character_nodes[actor_name]
                    edge_id = f"edge_{character_node.id}_{event_node.id}"

                    if edge_id not in self.edges:
                        edge = GraphEdge(
                            edge_id,
                            character_node.id,
                            event_node.id,
                            "participates_in",
                            1.0,
                            {"relationship": "character_event"},
                        )
                        self._add_edge(edge)

    async def _extract_sequential_relationships(
        self, planning_data: Dict[str, Any]
    ) -> None:
        """Extract sequential relationships from outline structure"""
        outline = planning_data.get("outline", [])

        # Sort outline by order
        sorted_outline = sorted(outline, key=lambda x: x.get("order", 0))

        section_nodes = []
        for outline_item in sorted_outline:
            section = outline_item.get("section", "")
            section_node = self._find_node_by_content(section)
            if section_node:
                section_nodes.append(section_node)

        # Create sequential relationships
        for i in range(len(section_nodes) - 1):
            current_node = section_nodes[i]
            next_node = section_nodes[i + 1]

            edge_id = f"edge_{current_node.id}_{next_node.id}"
            if edge_id not in self.edges:
                edge = GraphEdge(
                    edge_id,
                    current_node.id,
                    next_node.id,
                    "precedes",
                    1.0,
                    {"relationship": "sequential"},
                )
                self._add_edge(edge)

    async def _extract_cooccurrence_relationships(self, topic_content: str) -> None:
        """Extract co-occurrence relationships from text"""
        # Simple co-occurrence within sentences
        sentences = topic_content.split(".")

        for sentence in sentences:
            sentence_entities = []
            for node in self.nodes.values():
                if node.content.lower() in sentence.lower():
                    sentence_entities.append(node)

            # Create relationships between co-occurring entities
            for i, node1 in enumerate(sentence_entities):
                for node2 in sentence_entities[i + 1 :]:
                    edge_id = f"edge_{node1.id}_{node2.id}"
                    reverse_edge_id = f"edge_{node2.id}_{node1.id}"

                    if edge_id not in self.edges and reverse_edge_id not in self.edges:
                        edge = GraphEdge(
                            edge_id,
                            node1.id,
                            node2.id,
                            "co_occurs_with",
                            0.5,
                            {"relationship": "cooccurrence"},
                        )
                        self._add_edge(edge)

    async def _extract_llm_relationships(
        self, topic_content: str, perception_data: Dict[str, Any]
    ) -> None:
        """Use LLM to extract sophisticated relationships"""
        if not self.llm_provider:
            return

        # Get node list for context
        node_list = [
            {"id": node.id, "type": node.type, "content": node.content}
            for node in self.nodes.values()
        ]

        prompt = f"""
        Analyze this content and identify relationships between entities:
        
        Content: {topic_content[:1000]}
        
        Entities: {json.dumps(node_list[:20])}  # Limit for prompt size
        
        Identify semantic relationships like:
        - causes/effects
        - conflicts
        - similarities/differences  
        - hierarchical relationships
        - dependencies
        
        Return JSON list of relationships with source_id, target_id, relation_type, confidence.
        """

        try:
            response = await self.llm_provider.invoke(prompt)
            # Parse and add relationships (simplified for now)
            # In real implementation, would parse JSON response
            logger.info("LLM relationship extraction completed")
        except Exception as e:
            logger.error(f"LLM relationship extraction failed: {e}")

    def _find_node_by_content(self, content: str) -> Optional[GraphNode]:
        """Find node by content match"""
        for node in self.nodes.values():
            if node.content.lower() == content.lower():
                return node
        return None

    def _add_edge(self, edge: GraphEdge) -> None:
        """Add edge to graph and update adjacency lists"""
        self.edges[edge.id] = edge
        self.adjacency_list[edge.source_id].add(edge.target_id)
        self.reverse_adjacency[edge.target_id].add(edge.source_id)

        # Update node connections
        if edge.source_id in self.nodes:
            self.nodes[edge.source_id].connections.add(edge.target_id)
        if edge.target_id in self.nodes:
            self.nodes[edge.target_id].connections.add(edge.source_id)

    async def _analyze_graph(self) -> Dict[str, Any]:
        """Perform graph analysis using various algorithms"""
        analysis = {}

        # Calculate centrality measures
        centrality = await self.analysis_methods["centrality"]()
        analysis["centrality"] = centrality

        # Detect clusters/communities
        clusters = await self.analysis_methods["clustering"]()
        analysis["clusters"] = clusters

        # Analyze dependency chains
        dependencies = await self.analysis_methods["dependencies"]()
        analysis["dependencies"] = dependencies

        # Find important paths
        paths = await self.analysis_methods["paths"]()
        analysis["paths"] = paths

        # Calculate graph metrics
        analysis["metrics"] = {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "density": self._calculate_density(),
            "avg_degree": self._calculate_average_degree(),
            "connected_components": self._count_connected_components(),
        }

        return analysis

    async def _calculate_centrality(self) -> Dict[str, Any]:
        """Calculate node centrality measures"""
        centrality = {}

        # Degree centrality
        degree_centrality = {}
        for node_id in self.nodes:
            degree = len(self.adjacency_list[node_id]) + len(
                self.reverse_adjacency[node_id]
            )
            degree_centrality[node_id] = degree

        # Normalize degree centrality
        max_degree = max(degree_centrality.values()) if degree_centrality else 1
        for node_id in degree_centrality:
            degree_centrality[node_id] /= max_degree

        centrality["degree"] = degree_centrality

        # Simple betweenness centrality approximation
        betweenness = {node_id: 0.0 for node_id in self.nodes}
        # Simplified calculation - in practice would use proper algorithm
        centrality["betweenness"] = betweenness

        # Identify hub nodes (high degree centrality)
        hubs = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:5]
        centrality["hubs"] = [
            {"node_id": node_id, "centrality": score} for node_id, score in hubs
        ]

        return centrality

    async def _detect_clusters(self) -> Dict[str, Any]:
        """Detect clusters/communities in the graph"""
        clusters = []
        visited = set()

        # Simple connected component clustering
        for node_id in self.nodes:
            if node_id not in visited:
                cluster = self._get_connected_component(node_id, visited)
                if len(cluster) > 1:  # Only include multi-node clusters
                    clusters.append(
                        {
                            "id": f"cluster_{len(clusters)}",
                            "nodes": list(cluster),
                            "size": len(cluster),
                            "density": self._calculate_cluster_density(cluster),
                        }
                    )

        return {
            "clusters": clusters,
            "cluster_count": len(clusters),
            "largest_cluster": (
                max(clusters, key=lambda x: x["size"]) if clusters else None
            ),
        }

    def _get_connected_component(self, start_node: str, visited: Set[str]) -> Set[str]:
        """Get connected component starting from a node using BFS"""
        component = set()
        queue = deque([start_node])

        while queue:
            node_id = queue.popleft()
            if node_id not in visited:
                visited.add(node_id)
                component.add(node_id)

                # Add neighbors to queue
                neighbors = (
                    self.adjacency_list[node_id] | self.reverse_adjacency[node_id]
                )
                for neighbor in neighbors:
                    if neighbor not in visited:
                        queue.append(neighbor)

        return component

    def _calculate_cluster_density(self, cluster: Set[str]) -> float:
        """Calculate density within a cluster"""
        if len(cluster) <= 1:
            return 0.0

        internal_edges = 0
        for edge in self.edges.values():
            if edge.source_id in cluster and edge.target_id in cluster:
                internal_edges += 1

        max_edges = len(cluster) * (len(cluster) - 1)
        return internal_edges / max_edges if max_edges > 0 else 0.0

    async def _analyze_dependencies(self) -> Dict[str, Any]:
        """Analyze dependency relationships"""
        dependency_chains = []

        # Find nodes with dependency relationships
        dependency_edges = [
            edge
            for edge in self.edges.values()
            if edge.relation_type in ["depends_on", "requires", "builds_on"]
        ]

        # Build dependency graph
        dep_graph = defaultdict(list)
        for edge in dependency_edges:
            dep_graph[edge.source_id].append(edge.target_id)

        # Find dependency chains
        for start_node in dep_graph:
            chain = self._find_dependency_chain(start_node, dep_graph)
            if len(chain) > 1:
                dependency_chains.append(chain)

        return {
            "dependency_chains": dependency_chains,
            "critical_dependencies": self._find_critical_dependencies(dep_graph),
            "circular_dependencies": self._detect_circular_dependencies(dep_graph),
        }

    def _find_dependency_chain(
        self, start_node: str, dep_graph: Dict[str, List[str]]
    ) -> List[str]:
        """Find longest dependency chain from a start node"""
        visited = set()

        def dfs(node: str) -> List[str]:
            if node in visited:
                return [node]

            visited.add(node)
            longest_chain = [node]

            for dependent in dep_graph.get(node, []):
                chain = dfs(dependent)
                if len([node] + chain) > len(longest_chain):
                    longest_chain = [node] + chain

            visited.remove(node)
            return longest_chain

        return dfs(start_node)

    def _find_critical_dependencies(self, dep_graph: Dict[str, List[str]]) -> List[str]:
        """Find nodes that are critical dependencies (many things depend on them)"""
        dependency_count = defaultdict(int)

        for dependencies in dep_graph.values():
            for dep in dependencies:
                dependency_count[dep] += 1

        # Return nodes with high dependency count
        critical = sorted(dependency_count.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]
        return [node_id for node_id, count in critical if count > 1]

    def _detect_circular_dependencies(
        self, dep_graph: Dict[str, List[str]]
    ) -> List[List[str]]:
        """Detect circular dependencies"""
        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(node: str, path: List[str]) -> None:
            if node in rec_stack:
                # Found cycle
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)

            for dependent in dep_graph.get(node, []):
                dfs(dependent, path + [node])

            rec_stack.remove(node)

        for start_node in dep_graph:
            if start_node not in visited:
                dfs(start_node, [])

        return cycles

    async def _find_paths(self) -> Dict[str, Any]:
        """Find important paths in the graph"""
        paths = {}

        # Find shortest paths between important nodes
        centrality_data = await self._calculate_centrality()
        hub_nodes = [hub["node_id"] for hub in centrality_data["hubs"][:3]]

        important_paths = []
        for i, start_node in enumerate(hub_nodes):
            for end_node in hub_nodes[i + 1 :]:
                path = self._find_shortest_path(start_node, end_node)
                if path:
                    important_paths.append(
                        {
                            "start": start_node,
                            "end": end_node,
                            "path": path,
                            "length": len(path) - 1,
                        }
                    )

        paths["important_paths"] = important_paths
        return paths

    def _find_shortest_path(self, start: str, end: str) -> Optional[List[str]]:
        """Find shortest path between two nodes using BFS"""
        if start == end:
            return [start]

        visited = set()
        queue = deque([(start, [start])])

        while queue:
            node, path = queue.popleft()

            if node in visited:
                continue

            visited.add(node)

            # Check neighbors
            neighbors = self.adjacency_list[node] | self.reverse_adjacency[node]
            for neighbor in neighbors:
                if neighbor == end:
                    return path + [neighbor]

                if neighbor not in visited:
                    queue.append((neighbor, path + [neighbor]))

        return None  # No path found

    def _calculate_density(self) -> float:
        """Calculate graph density"""
        n = len(self.nodes)
        if n <= 1:
            return 0.0

        m = len(self.edges)
        max_edges = n * (n - 1)  # Directed graph
        return (2 * m) / max_edges if max_edges > 0 else 0.0

    def _calculate_average_degree(self) -> float:
        """Calculate average node degree"""
        if not self.nodes:
            return 0.0

        total_degree = sum(
            len(self.adjacency_list[node_id]) + len(self.reverse_adjacency[node_id])
            for node_id in self.nodes
        )
        return total_degree / len(self.nodes)

    def _count_connected_components(self) -> int:
        """Count number of connected components"""
        visited = set()
        components = 0

        for node_id in self.nodes:
            if node_id not in visited:
                self._get_connected_component(node_id, visited)
                components += 1

        return components

    async def _generate_recommendations(
        self, workspace: Dict[str, Any], graph_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate recommendations based on graph analysis"""
        recommendations = []

        # Missing connection recommendations
        recommendations.extend(self._recommend_missing_connections(graph_analysis))

        # Content gap recommendations
        recommendations.extend(self._recommend_content_gaps(graph_analysis))

        # Structure improvement recommendations
        recommendations.extend(self._recommend_structure_improvements(graph_analysis))

        return recommendations[:10]  # Limit to top 10 recommendations

    def _recommend_missing_connections(
        self, graph_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Recommend missing connections based on graph structure"""
        recommendations = []

        # Find isolated nodes
        isolated_nodes = [
            node_id
            for node_id in self.nodes
            if len(self.adjacency_list[node_id]) == 0
            and len(self.reverse_adjacency[node_id]) == 0
        ]

        for node_id in isolated_nodes:
            node = self.nodes[node_id]
            recommendations.append(
                {
                    "type": "missing_connection",
                    "priority": "high",
                    "suggestion": f"Connect isolated {node.type}: {node.content}",
                    "details": f"The {node.type} '{node.content}' has no connections to other elements",
                    "implementation": f"Consider how '{node.content}' relates to other story elements",
                }
            )

        return recommendations

    def _recommend_content_gaps(
        self, graph_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Recommend content to fill structural gaps"""
        recommendations = []

        # Check for missing key node types
        existing_types = set(node.type for node in self.nodes.values())

        # Determine expected types based on content
        if "character" in existing_types and "event" in existing_types:
            if "setting" not in existing_types:
                recommendations.append(
                    {
                        "type": "content_gap",
                        "priority": "medium",
                        "suggestion": "Add setting information",
                        "details": "Characters and events exist but setting is not well defined",
                        "implementation": "Describe where and when the story takes place",
                    }
                )

        return recommendations

    def _recommend_structure_improvements(
        self, graph_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Recommend structural improvements"""
        recommendations = []

        # Check graph connectivity
        metrics = graph_analysis.get("metrics", {})
        density = metrics.get("density", 0)

        if density < 0.1:
            recommendations.append(
                {
                    "type": "structure_improvement",
                    "priority": "medium",
                    "suggestion": "Increase connections between elements",
                    "details": f"Graph density is {density:.2f}, indicating sparse connections",
                    "implementation": "Add more relationships between characters, events, and settings",
                }
            )

        return recommendations

    async def _create_visualization_data(self) -> Dict[str, Any]:
        """Create data for graph visualization"""
        # Convert nodes and edges to visualization format
        vis_nodes = []
        for node in self.nodes.values():
            vis_nodes.append(
                {
                    "id": node.id,
                    "label": (
                        node.content[:20] + "..."
                        if len(node.content) > 20
                        else node.content
                    ),
                    "type": node.type,
                    "size": len(node.connections) + 5,  # Size based on connections
                    "metadata": node.metadata,
                }
            )

        vis_edges = []
        for edge in self.edges.values():
            vis_edges.append(
                {
                    "id": edge.id,
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "type": edge.relation_type,
                    "weight": edge.weight,
                    "metadata": edge.metadata,
                }
            )

        return {
            "nodes": vis_nodes,
            "edges": vis_edges,
            "layout": "force-directed",  # Suggested layout algorithm
            "settings": {
                "node_color_by": "type",
                "edge_width_by": "weight",
                "show_labels": True,
            },
        }

    async def _export_graph(self) -> Dict[str, Any]:
        """Export graph for persistence"""
        return {
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges.values()],
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "node_count": len(self.nodes),
                "edge_count": len(self.edges),
            },
        }


# Factory function for agent creation
async def create_graph_manager_agent(
    config: Dict[str, Any], llm_provider=None
) -> GraphManagerAgent:
    """Create and initialize graph manager agent"""
    return GraphManagerAgent(config, llm_provider)
