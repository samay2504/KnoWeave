"""Tests for session endpoints - Production Ready."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status

# Use production-ready imports for tests
try:
    from core.imports import import_manager
    PRODUCTION_IMPORTS = True
except ImportError:
    PRODUCTION_IMPORTS = False


class TestSessionEndpoints:
    """Test session management endpoints."""

    @patch("server.app.session_manager")
    def test_create_session_success(
        self, mock_session_manager, test_client, db_user_fixture
    ):
        """Test successful session creation."""
        # Mock session manager with AsyncMock for async methods
        mock_session_manager.create_session = AsyncMock(return_value="test-session-001")
        
        # Mock workspace that would be returned
        mock_workspace = {
            "session_id": "test-session-001",
            "user_id": "123456789",
            "topic": "story",
            "topic_content": "Once upon a time...",
            "events": [],
            "characters": {},
            "kb_triples": [],
            "projections": {},
            "history": [],
            "graph": {},
            "policy": {},
            "metadata": {}
        }
        mock_session_manager.load_workspace = AsyncMock(return_value=mock_workspace)
        
        payload = {
            "user_id": "123456789",
            "topic": "story",
            "topic_descriptor": "A fantasy adventure story",
            "initial_content": "Once upon a time...",
        }

        response = test_client.post("/api/session/new", json=payload)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "session_id" in data
        assert data["status"] == "created"
        assert "workspace" in data

    def test_create_session_unauthenticated(self, test_client):
        """Test session creation without session manager."""
        payload = {
            "user_id": "123456789",
            "topic": "story", 
            "topic_descriptor": "A fantasy adventure story",
            "initial_content": "Once upon a time...",
        }

        # Test with no session manager (simulates server error)
        response = test_client.post("/api/session/new", json=payload)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @patch("server.app.session_manager")
    def test_invoke_suggest_success(
        self, mock_session_manager, test_client
    ):
        """Test successful suggestion invocation."""
        # Mock session manager
        mock_workspace = {
            "session_id": "test-session-001",
            "topic_content": "Once upon a time...",
            "topic": "story",
            "user_id": "123456789",
            "events": [],
            "characters": {},
            "kb_triples": [],
            "projections": {},
            "history": [],
            "graph": {},
            "policy": {},
            "metadata": {}
        }
        mock_session_manager.load_workspace = AsyncMock(return_value=mock_workspace)
        mock_session_manager.save_projections = AsyncMock(return_value=None)

        # Mock agents results
        mock_agents_dict = {
            "perception": MagicMock(),
            "graph_manager": MagicMock(),
            "planner": MagicMock(),
            "verifier": MagicMock(),
            "evaluator": MagicMock()
        }
        
        # Configure their run methods to be AsyncMock
        mock_agents_dict["perception"].run = AsyncMock(return_value={"entities": [], "themes": []})
        mock_agents_dict["graph_manager"].run = AsyncMock(return_value={"status": "updated"})
        mock_agents_dict["planner"].run = AsyncMock(return_value={
            "branches": [
                {
                    "title": "Option A", 
                    "paragraph": "First choice...",
                    "events": [],
                    "flags": {},
                    "branch_type": "balanced"
                },
                {
                    "title": "Option B", 
                    "paragraph": "Second choice...",
                    "events": [],
                    "flags": {},
                    "branch_type": "balanced"
                },
            ]
        })
        mock_agents_dict["verifier"].run = AsyncMock(return_value={"verified": True})
        mock_agents_dict["evaluator"].run = AsyncMock(return_value={"branch_scores": [0.8, 0.9]})

        with patch("server.app.agents", mock_agents_dict):

            session_id = "test-session-001"
            payload = {"mode": "on_demand", "options": {}}

            response = test_client.post(
                f"/api/session/{session_id}/invoke_suggest", json=payload
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "projections" in data

    @patch("server.app.session_manager")
    def test_get_session_snapshot(
        self, mock_session_manager, test_client
    ):
        """Test getting session snapshot."""
        # Mock session manager
        mock_workspace = {
            "session_id": "test-session-001",
            "story_so_far": "Once upon a time...",
            "topic": "story"
        }
        mock_session_manager.load_workspace = AsyncMock(return_value=mock_workspace)

        session_id = "test-session-001"
        response = test_client.get(f"/api/session/{session_id}/snapshot")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "snapshot" in data

    def test_get_session_snapshot_not_found(self, test_client):
        """Test getting snapshot for non-existent session."""
        # Test with no session manager 
        session_id = "non-existent-session"
        response = test_client.get(f"/api/session/{session_id}/snapshot")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @patch("server.app.session_manager")
    def test_accept_branch_success(
        self, mock_session_manager, test_client
    ):
        """Test accepting a suggestion branch."""
        # Mock session manager
        mock_result = {
            "session_id": "test-session-001",
            "status": "updated"
        }
        mock_session_manager.accept_branch = AsyncMock(return_value=mock_result)
        
        # Mock workspace that would be returned
        mock_workspace = {
            "session_id": "test-session-001",
            "user_id": "123456789",
            "topic": "story",
            "topic_content": "Once upon a time... [updated with branch A]",
            "events": [],
            "characters": {},
            "kb_triples": [],
            "projections": {},
            "history": [],
            "graph": {},
            "policy": {},
            "metadata": {}
        }
        mock_session_manager.load_workspace = AsyncMock(return_value=mock_workspace)

        session_id = "test-session-001"
        payload = {"branch_id": "A"}

        response = test_client.post(
            f"/api/session/{session_id}/accept_branch", json=payload
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "accepted"
        assert "workspace" in data


class TestArangoDBIntegration:
    """Test ArangoDB integration with session endpoints."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        True,  # Skip by default since ArangoDB may not be running
        reason="ArangoDB container must be running for this test"
    )
    async def test_arangodb_data_persistence(self):
        """Test that session data is properly saved to and retrieved from ArangoDB."""
        # This test verifies that ArangoDB is properly activated and data persistence works
        
        # Import required modules
        from server.db.arango_client import create_arango_client, GraphNode, GraphEdge
        from server_config import ServerConfig
        
        # Get configuration
        config = ServerConfig()
        arango_config = config.get_database_config()["arango"]
        
        # Create client
        client = await create_arango_client(arango_config)
        assert client is not None, "ArangoDB client should be created successfully"
        
        # Test session ID
        test_session_id = "test-session-arangodb-persistence"
        
        # Test data - Create sample story elements
        test_nodes = [
            GraphNode(
                id="character_001",
                type="entity",
                summary="Main protagonist - a brave knight",
                properties={
                    "name": "Sir Galahad",
                    "role": "protagonist",
                    "attributes": ["brave", "noble", "determined"],
                    "session_id": test_session_id
                },
                confidence=0.95
            ),
            GraphNode(
                id="location_001",
                type="entity", 
                summary="Mystical forest where the adventure begins",
                properties={
                    "name": "Enchanted Forest",
                    "type": "location",
                    "mood": "mysterious",
                    "session_id": test_session_id
                },
                confidence=0.90
            ),
            GraphNode(
                id="event_001",
                type="event",
                summary="The knight enters the forest to begin his quest",
                properties={
                    "action": "entering",
                    "location": "Enchanted Forest",
                    "session_id": test_session_id,
                    "sequence": 1
                },
                confidence=0.88
            )
        ]
        
        # Save nodes to ArangoDB
        saved_node_ids = []
        for node in test_nodes:
            result = await client.add_node(test_session_id, node)
            assert result, f"Should successfully save node {node.id}"
            saved_node_ids.append(node.id)
        
        # Create relationships between story elements
        test_edges = [
            GraphEdge(
                from_node="character_001",
                to_node="location_001",
                type="visits",
                properties={
                    "context": "Sir Galahad enters the Enchanted Forest",
                    "session_id": test_session_id
                },
                confidence=0.85
            ),
            GraphEdge(
                from_node="character_001", 
                to_node="event_001",
                type="performs",
                properties={
                    "context": "Sir Galahad performs the action of entering",
                    "session_id": test_session_id
                },
                confidence=0.90
            )
        ]
        
        # Save edges to ArangoDB
        saved_edge_count = 0
        for edge in test_edges:
            result = await client.add_edge(test_session_id, edge)
            assert result, f"Should successfully save edge {edge.from_node} -> {edge.to_node}"
            saved_edge_count += 1
        
        # Verify data persistence by retrieving data
        
        # Test 1: Retrieve all nodes for the session
        retrieved_nodes = await client.get_nodes(test_session_id)
        assert len(retrieved_nodes) == len(test_nodes), "Should retrieve all saved nodes"
        
        # Verify node content
        retrieved_node_ids = {node.id for node in retrieved_nodes}
        expected_node_ids = {node.id for node in test_nodes}
        assert retrieved_node_ids == expected_node_ids, "Retrieved nodes should match saved nodes"
        
        # Test 2: Retrieve all edges for the session  
        retrieved_edges = await client.get_edges(test_session_id)
        assert len(retrieved_edges) == len(test_edges), "Should retrieve all saved edges"
        
        # Test 3: Get graph summary
        graph_summary = await client.get_graph_summary(test_session_id)
        assert graph_summary["total_nodes"] == len(test_nodes), "Graph summary should show correct node count"
        assert graph_summary["total_edges"] == len(test_edges), "Graph summary should show correct edge count"
        
        # Verify that node types are correctly categorized
        expected_entity_count = sum(1 for node in test_nodes if node.type == "entity")
        expected_event_count = sum(1 for node in test_nodes if node.type == "event")
        assert graph_summary["node_types"]["entity"] == expected_entity_count
        assert graph_summary["node_types"]["event"] == expected_event_count
        
        # Test 4: Verify data integrity - check specific node properties
        character_node = next((node for node in retrieved_nodes if node.id == "character_001"), None)
        assert character_node is not None, "Character node should be retrieved"
        assert character_node.properties["name"] == "Sir Galahad", "Character name should be preserved"
        assert "brave" in character_node.properties["attributes"], "Character attributes should be preserved"
        
        # Test 5: Verify session isolation - nodes should be session-specific
        other_session_nodes = await client.get_nodes("different-session-id")
        assert len(other_session_nodes) == 0, "Other session should have no nodes"
        
        # Cleanup: Remove test data
        cleanup_success = await client.clear_session_graph(test_session_id)
        assert cleanup_success, "Should successfully clean up test data"
        
        # Verify cleanup
        nodes_after_cleanup = await client.get_nodes(test_session_id)
        edges_after_cleanup = await client.get_edges(test_session_id)
        assert len(nodes_after_cleanup) == 0, "All nodes should be cleaned up"
        assert len(edges_after_cleanup) == 0, "All edges should be cleaned up"
        
        # Close connection
        await client.close()
        
        print("✅ ArangoDB Integration Test PASSED - Data persistence verified!")
        print(f"   - Successfully saved and retrieved {len(test_nodes)} nodes")
        print(f"   - Successfully saved and retrieved {len(test_edges)} edges")
        print(f"   - Graph operations and session isolation working correctly")
        print(f"   - Data cleanup successful")
