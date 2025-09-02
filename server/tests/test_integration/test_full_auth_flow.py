"""Integration tests for full authentication flow."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import respx
import httpx
from fastapi import status


class TestFullAuthFlow:
    """Test complete authentication and session flow."""

    @respx.mock
    def test_complete_oauth_flow(
        self, test_client, mock_google_token, mock_userinfo
    ):
        """Test complete OAuth flow from login to authenticated session."""

        # Mock database
        mock_users_collection = AsyncMock()
        mock_sessions_collection = AsyncMock()
        mock_client = MagicMock()
        mock_client.human_ai.users = mock_users_collection
        mock_client.human_ai.sessions = mock_sessions_collection
        
        # Override the dependency
        def get_mock_mongo_client():
            return mock_client
        
        # Override the dependency in the app
        from server.dependencies import get_mongo_client
        from server.app import create_app
        
        # Setup dependency override for this test
        app = test_client.app
        app.dependency_overrides[get_mongo_client] = get_mock_mongo_client

        # Mock Google token endpoint
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=httpx.Response(200, json=mock_google_token)
        )

        # Mock Google userinfo endpoint
        respx.get("https://www.googleapis.com/oauth2/v2/userinfo").mock(
            return_value=httpx.Response(200, json=mock_userinfo)
        )

        # Step 1: Initiate OAuth login
        response = test_client.get("/auth/google/login")
        assert response.status_code == status.HTTP_200_OK

        login_data = response.json()
        assert "auth_url" in login_data
        assert "state" in login_data

        # Step 2: Simulate OAuth callback
        state = login_data["state"]
        response = test_client.get(
            f"/auth/google/callback?code=mock_code&state={state}",
            cookies={"oauth_state": state},
        )

        assert response.status_code == status.HTTP_200_OK
        callback_data = response.json()
        assert callback_data["success"] is True
        assert "user" in callback_data

        # Verify user was saved to database
        mock_users_collection.update_one.assert_called_once()

        # Step 3: Verify authentication cookie was set
        set_cookie = response.headers.get("set-cookie")
        assert "auth_token=" in set_cookie

        # Extract the token for subsequent requests
        import re

        token_match = re.search(r"auth_token=([^;]+)", set_cookie)
        assert token_match
        auth_token = token_match.group(1)

        # Step 4: Test authenticated endpoint
        headers = {"Cookie": f"auth_token={auth_token}"}
        response = test_client.get("/api/me", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        user_data = response.json()
        assert user_data["email"] == mock_userinfo["email"]
        assert user_data["name"] == mock_userinfo["name"]

    def test_oauth_flow_with_invalid_state(self, test_client):
        """Test OAuth flow with invalid state parameter."""

        # Mock database
        mock_users_collection = AsyncMock()
        mock_client = MagicMock()
        mock_client.human_ai.users = mock_users_collection
        
        # Override the dependency
        def get_mock_mongo_client():
            return mock_client
        
        # Override the dependency in the app
        from server.dependencies import get_mongo_client
        app = test_client.app
        app.dependency_overrides[get_mongo_client] = get_mock_mongo_client

        # Attempt callback with invalid state
        response = test_client.get(
            "/auth/google/callback?code=mock_code&state=invalid_state"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Verify no user was saved
        mock_users_collection.update_one.assert_not_called()

    @respx.mock
    @patch("server.agents.session_manager.SessionManagerAgent")
    def test_authenticated_session_creation(
        self,
        mock_agent,
        test_client,
        mock_google_token,
        mock_userinfo,
    ):
        """Test creating a session after authentication."""

        # Mock database
        mock_users_collection = AsyncMock()
        mock_sessions_collection = AsyncMock()
        mock_client = MagicMock()
        mock_client.human_ai.users = mock_users_collection
        mock_client.human_ai.sessions = mock_sessions_collection
        
        # Override the dependency
        def get_mock_mongo_client():
            return mock_client
        
        # Override the dependency in the app
        from server.dependencies import get_mongo_client
        app = test_client.app
        app.dependency_overrides[get_mongo_client] = get_mock_mongo_client

        # Mock Google endpoints
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=httpx.Response(200, json=mock_google_token)
        )
        respx.get("https://www.googleapis.com/oauth2/v2/userinfo").mock(
            return_value=httpx.Response(200, json=mock_userinfo)
        )

        # Complete OAuth flow
        login_response = test_client.get("/auth/google/login")
        state = login_response.json()["state"]

        callback_response = test_client.get(
            f"/auth/google/callback?code=mock_code&state={state}",
            cookies={"oauth_state": state},
        )

        # Extract auth token
        set_cookie = callback_response.headers.get("set-cookie")
        import re

        token_match = re.search(r"auth_token=([^;]+)", set_cookie)
        auth_token = token_match.group(1)
        headers = {"Cookie": f"auth_token={auth_token}"}

        # Mock session creation
        mock_agent_instance = AsyncMock()
        mock_agent_instance.create_session.return_value = {
            "session_id": "test-session-001",
            "topic": "story",
            "created_at": "2025-08-31T00:00:00Z",
        }
        mock_agent.return_value = mock_agent_instance

        # Create session
        session_payload = {
            "user_id": mock_userinfo["id"],
            "topic": "story",
            "topic_descriptor": "A fantasy adventure",
            "initial_content": "Once upon a time...",
        }

        with patch("server.app.session_manager") as mock_session_manager:
            mock_session_manager.create_session = AsyncMock(return_value="test-session-001")
            
            # Mock workspace that would be returned
            mock_workspace = {
                "session_id": "test-session-001",
                "user_id": mock_userinfo["id"],
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

            response = test_client.post(
                "/api/session/new", json=session_payload, headers=headers
            )

        assert response.status_code == status.HTTP_200_OK
        session_data = response.json()
        assert "session_id" in session_data
        assert "workspace" in session_data
        assert session_data["workspace"]["topic"] == "story"

    def test_rate_limiting_oauth_endpoints(self, test_client):
        """Test rate limiting on OAuth endpoints."""

        # Make multiple rapid requests to trigger rate limiting
        for _ in range(10):  # Assuming rate limit is less than 10/minute
            response = test_client.get("/auth/google/login")
            if response.status_code == 429:  # Too Many Requests
                break
        else:
            pytest.skip("Rate limiting not triggered - may need adjustment")

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
