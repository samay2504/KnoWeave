"""Google OAuth 2.0 authentication implementation."""

import json
import secrets
import time
from typing import Dict, Optional
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, Request, Response
from jose import JWTError, jwt
from pydantic import BaseModel

from server_config import config


class GoogleUserInfo(BaseModel):
    """Google user information model."""

    id: str
    email: str
    name: str
    picture: Optional[str] = None
    email_verified: bool = True


class AuthTokens(BaseModel):
    """Authentication tokens model."""

    access_token: str
    id_token: str
    refresh_token: Optional[str] = None
    expires_in: int


class GoogleOAuth:
    """Google OAuth 2.0 client implementation."""

    def __init__(self):
        self.client_id = config.GOOGLE_OAUTH_CLIENT_ID
        self.client_secret = config.GOOGLE_OAUTH_CLIENT_SECRET
        self.redirect_uri = config.OAUTH_REDIRECT_URI
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"

    def generate_auth_url(self, state: str) -> str:
        """Generate Google OAuth authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "select_account",  # Changed from 'consent' to reduce friction
            "include_granted_scopes": "true",  # Include previously granted scopes
        }
        return f"{self.auth_url}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str, state: str) -> AuthTokens:
        """Exchange authorization code for tokens."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }

        # Add timeout and retry logic for better reliability
        timeout_config = httpx.Timeout(30.0, connect=10.0)  # 30s total, 10s connect
        
        async with httpx.AsyncClient(timeout=timeout_config) as client:
            try:
                response = await client.post(self.token_url, data=data)
            except httpx.TimeoutException:
                raise HTTPException(
                    status_code=408, 
                    detail="Request timeout while exchanging authorization code. Please try again."
                )
            except httpx.ConnectError:
                raise HTTPException(
                    status_code=503, 
                    detail="Unable to connect to Google's servers. Please try again later."
                )

        if response.status_code == 400:
            error_data = response.json()
            error_description = error_data.get("error_description", "")
            if "expired" in error_description.lower() or "invalid_grant" in error_data.get("error", ""):
                raise HTTPException(
                    status_code=400, 
                    detail="Authorization code has expired or been used. Please try logging in again."
                )
            
        if response.status_code != 200:
            raise HTTPException(
                status_code=400, detail=f"Token exchange failed: {response.text}"
            )

        token_data = response.json()
        return AuthTokens(**token_data)

    async def get_user_info(self, access_token: str) -> GoogleUserInfo:
        """Fetch user information from Google."""
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(self.userinfo_url, headers=headers)

        if response.status_code != 200:
            raise HTTPException(
                status_code=400, detail=f"Failed to fetch user info: {response.text}"
            )

        user_data = response.json()
        return GoogleUserInfo(**user_data)

    async def refresh_access_token(self, refresh_token: str) -> AuthTokens:
        """Refresh access token using refresh token."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_url, data=data)

        if response.status_code != 200:
            raise HTTPException(
                status_code=400, detail=f"Token refresh failed: {response.text}"
            )

        token_data = response.json()
        return AuthTokens(**token_data)


class JWTManager:
    """JWT token management."""

    def __init__(self):
        self.secret_key = config.JWT_SECRET
        self.algorithm = config.JWT_ALGORITHM
        self.expire_seconds = config.JWT_EXPIRE_SECONDS

    def create_jwt_token(self, user_data: Dict) -> str:
        """Create JWT token for user."""
        payload = {
            "user_id": user_data["id"],
            "email": user_data["email"],
            "name": user_data["name"],
            "exp": time.time() + self.expire_seconds,
            "iat": time.time(),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_jwt_token(self, token: str) -> Dict:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            if payload.get("exp", 0) < time.time():
                raise HTTPException(status_code=401, detail="Token expired")
            return payload
        except JWTError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


# Global instances
google_oauth = GoogleOAuth()
jwt_manager = JWTManager()


def generate_state() -> str:
    """Generate secure random state for OAuth."""
    return secrets.token_urlsafe(32)


def set_auth_cookie(response: Response, token: str) -> None:
    """Set secure authentication cookie with environment-aware flags."""
    # Determine secure flag based on environment
    # In development/localhost with http, secure must be False
    is_dev = config.environment.lower() in ('development', 'dev', 'local')
    cookie_secure = False if is_dev else config.cookie_secure
    
    # SameSite should be Lax for localhost, can be stricter in production
    cookie_samesite = "lax" if is_dev else config.cookie_samesite.lower()
    
    response.set_cookie(
        key="auth_token",
        value=token,
        max_age=config.JWT_EXPIRE_SECONDS,
        httponly=True,
        secure=cookie_secure,
        samesite=cookie_samesite,
        domain=config.cookie_domain if hasattr(config, 'cookie_domain') and config.cookie_domain else None,
    )


def clear_auth_cookie(response: Response) -> None:
    """Clear authentication cookie with environment-aware flags."""
    # Match the same environment-aware logic as set_auth_cookie
    is_dev = config.environment.lower() in ('development', 'dev', 'local')
    cookie_secure = False if is_dev else config.cookie_secure
    cookie_samesite = "lax" if is_dev else config.cookie_samesite.lower()
    
    response.delete_cookie(
        key="auth_token",
        httponly=True,
        secure=cookie_secure,
        samesite=cookie_samesite,
        domain=config.cookie_domain if hasattr(config, 'cookie_domain') and config.cookie_domain else None,
    )


def get_current_user_from_request(request: Request) -> Optional[Dict]:
    """Extract current user from request cookies."""
    token = request.cookies.get("auth_token")
    if not token:
        return None

    try:
        return jwt_manager.verify_jwt_token(token)
    except HTTPException:
        return None
