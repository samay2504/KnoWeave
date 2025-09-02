"""Session routes dependencies for testing."""

from typing import Dict
from fastapi import Request, Depends

# Import from db module
from db.mongo_client import MongoClient


from dependencies import get_mongo_client


# Note: get_mongo_client is now imported from dependencies module
# This provides proper dependency injection through the DI container


def get_current_user_dependency(request: Request) -> Dict:
    """Get current user from request for dependency injection."""
    # Import here to avoid circular import
    from auth.google_oauth import get_current_user_from_request
    
    user = get_current_user_from_request(request)
    if not user:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user
