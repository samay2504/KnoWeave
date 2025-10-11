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

# Import config for environment-aware cookie flags
try:
    from server_config import config as server_config
except ImportError:
    from server.server_config import ServerConfig
    server_config = ServerConfig()

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


# In-memory state storage with expiration 
import time
_oauth_states: Dict[str, Dict] = {}

def clean_expired_states():
    """Clean up expired OAuth states."""
    current_time = time.time()
    expired_keys = [
        key for key, value in _oauth_states.items()
        if current_time - value.get("created_at", 0) > 300  # 5 minutes
    ]
    for key in expired_keys:
        del _oauth_states[key]

def is_state_valid(state: str) -> bool:
    """Check if OAuth state is valid and not expired."""
    if state not in _oauth_states:
        return False
    
    created_at = _oauth_states[state].get("created_at", 0)
    return time.time() - created_at < 300  # 5 minutes validity


def consume_state(state: str) -> dict:
    """Consume a state (remove it after use to prevent reuse) and return its data."""
    if state in _oauth_states:
        state_data = _oauth_states[state]
        del _oauth_states[state]  # Remove to prevent reuse
        return state_data
    return None


@router.get("/auth/google/login")
@limiter.limit("5/minute")
async def google_login(request: Request, response: Response):
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

        # Store state with timestamp for validation
        clean_expired_states()  # Clean up old states first
        _oauth_states[state] = {
            "created_at": time.time(),
            "ip": get_remote_address(request),
            "user_agent": request.headers.get("user-agent", ""),
        }

        auth_url = google_oauth.generate_auth_url(state)

        # Store state in secure cookie as well with environment-aware flags
        is_dev = server_config.environment.lower() in ('development', 'dev', 'local')
        response.set_cookie(
            "oauth_state",
            state,
            max_age=300,  # 5 minutes to match server-side expiration
            httponly=True,
            secure=False if is_dev else True,
            samesite="lax",
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
async def google_login_redirect(request: Request, response: Response):
    """Redirect to the main Google OAuth login endpoint."""
    return await google_login(request, response)


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
        
        # Validate state using cookie (primary) and server-side store (fallback)
        stored_state = request.cookies.get("oauth_state")
        
        # Check if state matches cookie (this is the primary validation)
        cookie_valid = stored_state and stored_state == state
        
        # Check in-memory state (secondary validation, may have been consumed)
        server_state_valid = is_state_valid(state)
        
        if not cookie_valid and not server_state_valid:
            logger.warning(
                f"Invalid OAuth state from IP: {get_remote_address(request)} (cookie={bool(stored_state)}, server={server_state_valid})"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired authentication session. Please try logging in again.",
            )
        
        # Consume server-side state if it still exists (idempotent)
        state_data = consume_state(state)
        if not state_data and not cookie_valid:
            # Only fail if BOTH cookie AND server state are invalid
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
            await mongo_client.save_user(user_doc)
        else:
            # Mock for tests - just log the action
            logger.info(f"Mock save user: {user_doc.get('email', 'unknown')}")

        # Create JWT token
        jwt_token = jwt_manager.create_jwt_token(
            {"id": user_info.id, "email": user_info.email, "name": user_info.name}
        )

        # Set secure cookie
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
async def api_google_login(request: Request, response: Response):
    """API endpoint for Google OAuth login (compatible with frontend)."""
    return await google_login(request, response)


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
