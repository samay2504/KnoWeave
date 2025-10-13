"""Tests for Google OAuth authentication."""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import respx
import httpx
from fastapi import status

# Import using absolute paths
try:
    from server.auth.google_oauth import google_oauth, jwt_manager, generate_state
except ImportError:
    # Fallback import
    google_oauth = None
    jwt_manager = None
    generate_state = None


class TestGoogleOAuth:
    """Test Google OAuth implementation."""

    def test_generate_auth_url(self):
        """Test Google auth URL generation."""
        state = "test_state_123"
        auth_url = google_oauth.generate_auth_url(state)

        assert "accounts.google.com/o/oauth2/v2/auth" in auth_url
        assert "client_id" in auth_url
        assert f"state={state}" in auth_url
        assert "scope=openid+email+profile" in auth_url

    @respx.mock
    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_success(self, mock_google_token):
        """Test successful token exchange."""
        # Mock the token endpoint
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=httpx.Response(200, json=mock_google_token)
        )

        tokens = await google_oauth.exchange_code_for_tokens("mock_code", "test_state")

        assert tokens.access_token == mock_google_token["access_token"]
        assert tokens.id_token == mock_google_token["id_token"]
        assert tokens.refresh_token == mock_google_token["refresh_token"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_failure(self):
        """Test failed token exchange."""
        # Mock failed response
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=httpx.Response(400, json={"error": "invalid_grant"})
        )

        with pytest.raises(Exception) as exc_info:
            await google_oauth.exchange_code_for_tokens("invalid_code", "test_state")

        # Updated: check for new user-friendly error message
        error_msg = str(exc_info.value)
        assert "Authorization code has expired" in error_msg or "Token exchange failed" in error_msg

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_user_info_success(self, mock_userinfo):
        """Test successful user info retrieval."""
        # Mock the userinfo endpoint
        respx.get("https://www.googleapis.com/oauth2/v2/userinfo").mock(
            return_value=httpx.Response(200, json=mock_userinfo)
        )

        user_info = await google_oauth.get_user_info("mock_access_token")

        assert user_info.id == mock_userinfo["id"]
        assert user_info.email == mock_userinfo["email"]
        assert user_info.name == mock_userinfo["name"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_user_info_failure(self):
        """Test failed user info retrieval."""
        # Mock failed response
        respx.get("https://www.googleapis.com/oauth2/v2/userinfo").mock(
            return_value=httpx.Response(401, json={"error": "invalid_token"})
        )

        with pytest.raises(Exception) as exc_info:
            await google_oauth.get_user_info("invalid_token")

        assert "Failed to fetch user info" in str(exc_info.value)


class TestJWTManager:
    """Test JWT token management."""

    def test_create_jwt_token(self):
        """Test JWT token creation."""
        user_data = {
            "id": "123456789",
            "email": "test@example.com",
            "name": "Test User",
        }

        token = jwt_manager.create_jwt_token(user_data)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_jwt_token_valid(self):
        """Test valid JWT token verification."""
        user_data = {
            "id": "123456789",
            "email": "test@example.com",
            "name": "Test User",
        }

        token = jwt_manager.create_jwt_token(user_data)
        payload = jwt_manager.verify_jwt_token(token)

        assert payload["user_id"] == user_data["id"]
        assert payload["email"] == user_data["email"]
        assert payload["name"] == user_data["name"]

    def test_verify_jwt_token_invalid(self):
        """Test invalid JWT token verification."""
        with pytest.raises(Exception) as exc_info:
            jwt_manager.verify_jwt_token("invalid_token")

        assert "Invalid token" in str(exc_info.value)

    def test_generate_state(self):
        """Test OAuth state generation."""
        state1 = generate_state()
        state2 = generate_state()

        assert isinstance(state1, str)
        assert isinstance(state2, str)
        assert len(state1) > 20  # Should be reasonably long
        assert state1 != state2  # Should be unique
