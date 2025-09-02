"""Test configuration and fixtures."""

import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient
import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

try:
    from server.app import create_app, FASTAPI_AVAILABLE
    from server.auth.google_oauth import jwt_manager
    from server.dependencies import setup_container, cleanup_container
except ImportError:
    # Fallback for different import paths
    try:
        import server.app as app_module
        create_app = app_module.create_app
        FASTAPI_AVAILABLE = app_module.FASTAPI_AVAILABLE
        jwt_manager = None
        setup_container = None
        cleanup_container = None
    except AttributeError:
        # If app is None (FastAPI not available), create a mock
        create_app = None
        FASTAPI_AVAILABLE = False
        jwt_manager = None
        setup_container = None
        cleanup_container = None


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    # Initialize dependency container for tests
    if setup_container:
        setup_container()
    
    # Create app with dependencies properly set up
    app = create_app() if create_app and FASTAPI_AVAILABLE else None
    if not app:
        raise ImportError("FastAPI is required but not available")
    
    client = TestClient(app)
    
    yield client
    
    # Cleanup dependency container after tests
    if cleanup_container:
        cleanup_container()


@pytest.fixture
async def mock_mongo_client():
    """Create a mock MongoDB client."""
    client = MagicMock(name="MongoClientMock")
    return client

@pytest.fixture
def mock_google_token():
    """Mock Google OAuth token response."""
    return {
        "access_token": "mock_access_token",
        "id_token": "mock_id_token",
        "refresh_token": "mock_refresh_token",
        "expires_in": 3600,
        "token_type": "Bearer",
    }


@pytest.fixture
def mock_userinfo():
    """Mock Google userinfo response."""
    return {
        "id": "123456789",
        "email": "test@example.com",
        "name": "Test User",
        "picture": "https://example.com/avatar.jpg",
        "email_verified": True,
    }


@pytest.fixture
def valid_jwt_token():
    """Create a valid JWT token for testing."""
    user_data = {"id": "123456789", "email": "test@example.com", "name": "Test User"}
    return jwt_manager.create_jwt_token(user_data)


@pytest.fixture
def authenticated_headers(valid_jwt_token):
    """Create headers with authentication cookie."""
    return {"Cookie": f"auth_token={valid_jwt_token}"}


@pytest.fixture
def db_user_fixture():
    """Sample user document for database tests."""
    return {
        "google_id": "123456789",
        "email": "test@example.com",
        "name": "Test User",
        "picture": "https://example.com/avatar.jpg",
        "email_verified": True,
        "refresh_token": "mock_refresh_token",
    }


@pytest.fixture
async def mock_llm_provider():
    """Mock LLM provider for testing."""
    provider = AsyncMock()
    provider.generate_response = AsyncMock(
        return_value={"text": "Mock LLM response", "usage": {"total_tokens": 100}}
    )
    return provider


@pytest.fixture
def sample_workspace():
    """Sample workspace data for testing."""
    return {
        "session_id": "test-session-001",
        "topic": "story",
        "story_so_far": "Once upon a time, there was a brave knight...",
        "events": [
            {"id": "e1", "summary": "Knight begins journey", "confidence": 0.95}
        ],
        "characters": {"Knight": {"name": "Sir Galahad", "traits": ["brave", "noble"]}},
        "graph": {"nodes": [], "edges": []},
    }
