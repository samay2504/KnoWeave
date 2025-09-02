"""Tests for protected endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi import status


class TestProtectedEndpoints:
    """Test authentication-protected endpoints."""

    def test_get_current_user_authenticated(self, test_client, authenticated_headers):
        """Test /api/me with valid authentication."""
        response = test_client.get("/api/me", headers=authenticated_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "name" in data

    def test_get_current_user_unauthenticated(self, test_client):
        """Test /api/me without authentication."""
        response = test_client.get("/api/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_invalid_token(self, test_client):
        """Test /api/me with invalid token."""
        headers = {"Cookie": "auth_token=invalid_token"}
        response = test_client.get("/api/me", headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_success(self, test_client):
        """Test successful logout."""
        response = test_client.post("/auth/logout")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

        # Check that cookie is cleared
        set_cookie = response.headers.get("set-cookie")
        assert "auth_token=" in set_cookie
        assert "Max-Age=0" in set_cookie or "expires=" in set_cookie

    def test_refresh_token_success(
        self, test_client, authenticated_headers, db_user_fixture
    ):
        """Test successful token refresh."""
        # Mock database response
        mock_collection = AsyncMock()
        mock_collection.find_one.return_value = db_user_fixture
        mock_client = AsyncMock()
        mock_client.human_ai.users = mock_collection
        
        # Override the dependency
        def get_mock_mongo_client():
            return mock_client
        
        # Override the dependency in the app
        from server.dependencies import get_mongo_client
        app = test_client.app
        app.dependency_overrides[get_mongo_client] = get_mock_mongo_client

        with patch(
            "server.auth.google_oauth.google_oauth.refresh_access_token"
        ) as mock_refresh:
            mock_refresh.return_value = AsyncMock(
                access_token="new_access_token", refresh_token="new_refresh_token"
            )

            response = test_client.post(
                "/auth/google/token_refresh", headers=authenticated_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "access_token" in data

    def test_refresh_token_unauthenticated(self, test_client):
        """Test token refresh without authentication."""
        response = test_client.post("/auth/google/token_refresh")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
