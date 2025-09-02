"""
API Package - Human-AI Co-Creation System
REST API endpoints and middleware
"""

# Import health router and main router
from .health import get_health_router
from .routes import router

__all__ = ["get_health_router", "router"]
