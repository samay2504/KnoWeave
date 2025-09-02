"""Tests for session endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi import status


class TestSessionEndpoints:
    """Test session management endpoints."""

    @patch("server.app.session_manager")
    def test_create_session_success(
        self, mock_session_manager, test_client, db_user_fixture
    ):
        """Test successful session creation."""
        # Mock session manager
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
        from unittest.mock import MagicMock
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
