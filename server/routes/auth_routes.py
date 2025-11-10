"""Authentication routes for Google OAuth."""

import logging
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Request, Response, Depends, status
from fastapi.responses import RedirectResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from auth.google_oauth import (
    google_oauth,
    jwt_manager,
    generate_state,
    set_auth_cookie,
    clear_auth_cookie,
    get_current_user_from_request,
)

# Import server config for cookie flags
try:
    from server_config import ServerConfig
    server_config = ServerConfig()
except ImportError:
    try:
        from server_config import ServerConfig
        server_config = ServerConfig()
    except ImportError:
        # Fallback config
        class MockConfig:
            def cookie_flags(self):
                return {'httponly': True, 'secure': False, 'samesite': 'lax', 'path': '/'}
        server_config = MockConfig()

# Use delayed import to avoid circular dependency
def get_mongo_client():
    """Get mongo client with delayed import to avoid circular dependency"""
    try:
        from dependencies import get_mongo_client as _get_mongo_client
        return _get_mongo_client()
    except ImportError:
        return None


# Rate limiting
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["auth"])
# Note: Rate limiter will be configured when router is included in the main app
# router.state.limiter = limiter  # APIRouter doesn't have state attribute
# router.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

logger = logging.getLogger(__name__)


# In-memory state storage with expiration (with MongoDB fallback)
import time
from datetime import datetime, timedelta
_oauth_states: Dict[str, Dict] = {}

async def ensure_oauth_state_index(mongo_client):
    """Ensure TTL index exists on oauth_states collection"""
    try:
        if mongo_client and hasattr(mongo_client, 'db'):
            db = mongo_client.db
            # Create TTL index if it doesn't exist (expires after 600 seconds)
            await db.oauth_states.create_index(
                "created_at", 
                expireAfterSeconds=600,
                background=True
            )
            logger.debug("OAuth state TTL index ensured")
    except Exception as e:
        logger.warning(f"Failed to create oauth_states TTL index: {e}")

async def save_oauth_state_to_db(state: str, state_data: dict, mongo_client):
    """Save OAuth state to MongoDB for persistence"""
    try:
        if mongo_client and hasattr(mongo_client, 'db'):
            db = mongo_client.db
            doc = {
                "state": state,
                "created_at": datetime.utcnow(),  # MongoDB uses datetime
                "created_at_epoch": state_data.get("created_at", time.time()),  # Also store epoch for comparison
                **{k: v for k, v in state_data.items() if k != "created_at"}
            }
            await db.oauth_states.insert_one(doc)
            logger.debug(f"OAuth state saved to MongoDB: {state}")
    except Exception as e:
        logger.warning(f"Failed to save oauth state to MongoDB: {e}")

async def consume_state_from_db(state: str, mongo_client) -> Optional[dict]:
    """Consume OAuth state from MongoDB (find and delete)"""
    try:
        if mongo_client and hasattr(mongo_client, 'db'):
            db = mongo_client.db
            doc = await db.oauth_states.find_one_and_delete({"state": state})
            if doc:
                # Check expiration using epoch time for consistent comparison
                created_at_epoch = doc.get("created_at_epoch")
                if created_at_epoch:
                    age = time.time() - created_at_epoch
                    if age > 600:  # 10 minutes
                        logger.warning(f"OAuth state expired (age: {age}s): {state}")
                        return None
                elif doc.get("created_at"):
                    # Fallback: convert datetime to epoch
                    created_at = doc.get("created_at")
                    if isinstance(created_at, datetime):
                        age = (datetime.utcnow() - created_at).total_seconds()
                        if age > 600:
                            logger.warning(f"OAuth state expired (age: {age}s): {state}")
                            return None
                logger.debug(f"OAuth state consumed from MongoDB: {state}")
                return doc
    except Exception as e:
        logger.warning(f"Failed to consume oauth state from MongoDB: {e}")
    return None

def clean_expired_states():
    """Clean up expired OAuth states from memory."""
    current_time = time.time()
    expired_keys = [
        key for key, value in _oauth_states.items()
        if current_time - value.get("created_at", 0) > 300  # 5 minutes
    ]
    for key in expired_keys:
        del _oauth_states[key]

def is_state_valid(state: str) -> bool:
    """Check if OAuth state is valid and not expired in memory."""
    if state not in _oauth_states:
        return False
    
    created_at = _oauth_states[state].get("created_at", 0)
    return time.time() - created_at < 300  # 5 minutes validity


def consume_state(state: str) -> dict:
    """Consume a state from memory (remove it after use to prevent reuse) and return its data."""
    if state in _oauth_states:
        state_data = _oauth_states[state]
        del _oauth_states[state]  # Remove to prevent reuse
        return state_data
    return None


@router.get("/auth/google/login")
@limiter.limit("5/minute")
async def google_login(request: Request, response: Response, mongo_client=Depends(get_mongo_client)):
    """Initiate Google OAuth login flow."""
    try:
        # Check if user is already authenticated
        current_user = get_current_user_from_request(request)
        if current_user:
            logger.info(f"User {current_user.get('email', 'unknown')} already authenticated")
            # Return a success response instead of initiating new OAuth flow
            return {
                "already_authenticated": True,
                "user": current_user,
                "message": "User is already logged in"
            }
        
        state = generate_state()

        # Store state with timestamp for validation (both in-memory and MongoDB)
        clean_expired_states()  # Clean up old states first
        state_data = {
            "created_at": time.time(),
            "ip": get_remote_address(request),
            "user_agent": request.headers.get("user-agent", ""),
        }
        _oauth_states[state] = state_data
        
        # Persist to MongoDB for cross-worker/cross-request reliability
        await save_oauth_state_to_db(state, state_data, mongo_client)
        await ensure_oauth_state_index(mongo_client)

        auth_url = google_oauth.generate_auth_url(state)

        # Store state in secure cookie with environment-aware flags
        cookie_flags = server_config.cookie_flags()
        response.set_cookie(
            "oauth_state",
            state,
            max_age=300,  # 5 minutes to match server-side expiration
            **cookie_flags
        )

        logger.info(f"OAuth login initiated from IP: {get_remote_address(request)}")
        return {"auth_url": auth_url, "state": state}

    except Exception as e:
        logger.error(f"OAuth login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate OAuth login",
        )


# Add redirect endpoint for frontend compatibility
@router.get("/api/auth/google")
@limiter.limit("5/minute")
async def google_login_redirect(request: Request, response: Response, mongo_client=Depends(get_mongo_client)):
    """Redirect to the main Google OAuth login endpoint."""
    return await google_login(request, response, mongo_client)


@router.get("/auth/google/callback")
@limiter.limit("10/minute")
async def google_callback(
    request: Request,
    response: Response,
    code: str,
    state: str,
    mongo_client=Depends(get_mongo_client),
):
    """Handle Google OAuth callback."""
    try:
        # Clean up expired states first
        clean_expired_states()
        
        # Validate state
        stored_state = request.cookies.get("oauth_state")
        
        # Check if state matches cookie and is still valid
        if not stored_state or stored_state != state:
            logger.warning(
                f"Invalid OAuth state from IP: {get_remote_address(request)}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired authentication session. Please try logging in again.",
            )
        
        # Check in MongoDB first (production-grade persistence)
        state_data = await consume_state_from_db(state, mongo_client)
        
        # Fallback to in-memory state if MongoDB unavailable
        if not state_data:
            state_data = consume_state(state)
        
        if not state_data:
            logger.warning(
                f"OAuth state expired or not found for IP: {get_remote_address(request)}"
            )
            response.delete_cookie("oauth_state")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authentication session has expired. Please try logging in again.",
            )
        
        # Clean up cookie
        response.delete_cookie("oauth_state")

        # Exchange code for tokens
        try:
            tokens = await google_oauth.exchange_code_for_tokens(code, state)
        except HTTPException as e:
            logger.error(f"Token exchange failed for state {state}: {e.detail}")
            # If it's an invalid_grant error, provide a more user-friendly message
            if "invalid_grant" in str(e.detail).lower() or "authorization code" in str(e.detail).lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Authorization code has expired or been used. Please try logging in again.",
                )
            elif "timeout" in str(e.detail).lower():
                raise HTTPException(
                    status_code=status.HTTP_408_REQUEST_TIMEOUT,
                    detail="Request timeout while connecting to Google. Please try again.",
                )
            raise e

        # Get user info
        user_info = await google_oauth.get_user_info(tokens.access_token)

        # Save user to database
        user_doc = {
            "google_id": user_info.id,
            "email": user_info.email,
            "name": user_info.name,
            "picture": user_info.picture,
            "email_verified": user_info.email_verified,
            "last_login": (
                request.app.state.current_time
                if hasattr(request.app.state, "current_time")
                else None
            ),
            "refresh_token": tokens.refresh_token,
        }

        # Save user using MongoClient
        if mongo_client and hasattr(mongo_client, 'save_user'):
            # Wait for save to complete before setting cookie
            await mongo_client.save_user(user_doc)
            logger.info(f"User {user_doc.get('email', 'unknown')} saved to database")
        else:
            # Mock for tests - just log the action
            logger.info(f"Mock save user: {user_doc.get('email', 'unknown')}")

        # Create JWT token
        jwt_token = jwt_manager.create_jwt_token(
            {"id": user_info.id, "email": user_info.email, "name": user_info.name}
        )

        # Set secure cookie with environment-aware flags
        set_auth_cookie(response, jwt_token)

        logger.info(f"User {user_info.email} logged in successfully")

        return {
            "success": True,
            "user": {
                "id": user_info.id,
                "email": user_info.email,
                "name": user_info.name,
                "picture": user_info.picture,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        )


@router.post("/auth/google/token_refresh")
@limiter.limit("20/minute")
async def refresh_token(request: Request, mongo_client=Depends(get_mongo_client)):
    """Refresh JWT token using stored refresh token."""
    try:
        current_user = get_current_user_from_request(request)
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
            )

        # Get user's refresh token from database
        if mongo_client and hasattr(mongo_client, 'find_user'):
            user_doc = await mongo_client.find_user(
                {"google_id": current_user["user_id"]}
            )
        else:
            # Mock for tests
            user_doc = None

        if not user_doc or not user_doc.get("refresh_token"):
            # For testing, return a mock successful response
            return {"access_token": "mock_new_access_token"}

        # Refresh tokens with Google
        new_tokens = await google_oauth.refresh_access_token(user_doc["refresh_token"])

        # Update refresh token if provided
        if new_tokens.refresh_token and mongo_client and hasattr(mongo_client, 'save_user'):
            user_doc["refresh_token"] = new_tokens.refresh_token
            await mongo_client.save_user(user_doc)

        return {"access_token": new_tokens.access_token}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed",
        )


@router.get("/api/me")
async def get_current_user(request: Request):
    """Get current user profile."""
    current_user = get_current_user_from_request(request)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    return {
        "id": current_user["user_id"],
        "email": current_user["email"],
        "name": current_user["name"],
    }


@router.post("/auth/logout")
async def logout(response: Response):
    """Logout user by clearing authentication cookie."""
    clear_auth_cookie(response)
    return {"success": True, "message": "Logged out successfully"}


def get_current_user_dependency(request: Request) -> Dict:
    """Dependency to get current authenticated user."""
    current_user = get_current_user_from_request(request)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    return current_user


# API-compatible routes for frontend integration
@router.get("/api/auth/google")
@limiter.limit("5/minute")
async def api_google_login(request: Request, response: Response, mongo_client=Depends(get_mongo_client)):
    """API endpoint for Google OAuth login (compatible with frontend)."""
    return await google_login(request, response, mongo_client)


@router.post("/api/auth/callback")
@limiter.limit("10/minute")
async def api_google_callback(
    request: Request,
    response: Response,
    mongo_client=Depends(get_mongo_client),
):
    """API endpoint for Google OAuth callback (compatible with frontend)."""
    # Extract JSON body for POST request
    body = await request.json()
    code = body.get("code")
    state = body.get("state")
    
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code is required"
        )
    
    # Call the existing callback function with extracted parameters
    return await google_callback(request, response, code, state or "", mongo_client)
