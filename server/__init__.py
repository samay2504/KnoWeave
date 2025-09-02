"""
Server Package - Human-AI Co-Creation System
Main server package with configuration and utilities - Production Ready
"""

# Use production-ready import system
try:
    from core.imports import import_manager
    from core.config import config as ServerConfig
    PRODUCTION_IMPORTS = True
except ImportError:
    # Fallback during transition
    from .server_config import ServerConfig
    PRODUCTION_IMPORTS = False

# Import app with fallback
try:
    from .app import app
except ImportError:
    # Graceful fallback if app fails to import
    app = None

__all__ = ["ServerConfig", "app"]
