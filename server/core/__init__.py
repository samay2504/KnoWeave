"""
Core package - Centralized import and configuration management
Production-ready import system with dynamic path resolution
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Project root discovery
def get_project_root() -> Path:
    """
    Dynamically discover project root by looking for key files
    This makes the system resilient to file movements
    """
    current = Path(__file__).parent.parent  # Start from server directory (one level up from core)
    
    # Look for key project indicators
    indicators = [
        'pyproject.toml',
        'requirements.txt', 
        '.env',
        'run.py'
    ]
    
    # Walk up the directory tree
    for parent in [current] + list(current.parents):
        if any((parent / indicator).exists() for indicator in indicators):
            return parent
    
    # Fallback to current directory's grandparent (server/core -> server -> project)
    return current

# Initialize project paths
PROJECT_ROOT = get_project_root()
SERVER_ROOT = PROJECT_ROOT / 'server'

# Add paths to sys.path if not already present
def ensure_paths_in_syspath():
    """Ensure all necessary paths are in sys.path"""
    paths_to_add = [
        str(PROJECT_ROOT),
        str(SERVER_ROOT),
    ]
    
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)

ensure_paths_in_syspath()

# Version and environment info
__version__ = "1.0.0"
__environment__ = os.getenv("ENVIRONMENT", "development")

# Export key paths for other modules
__all__ = [
    "PROJECT_ROOT",
    "SERVER_ROOT", 
    "get_project_root",
    "ensure_paths_in_syspath",
    "__version__",
    "__environment__"
]
