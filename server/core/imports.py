"""
Import utilities - Production-ready import management
Handles dynamic imports, optional dependencies, and path resolution
"""

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any, Optional, Type, Dict, List, Union
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class ImportManager:
    """Centralized import management with fallbacks and error handling"""
    
    def __init__(self):
        self._import_cache: Dict[str, Any] = {}
        self._failed_imports: Dict[str, str] = {}
    
    def safe_import(self, module_name: str, package: Optional[str] = None) -> Optional[Any]:
        """
        Safely import a module with caching and error handling
        
        Args:
            module_name: Name of module to import
            package: Package name for relative imports
            
        Returns:
            Imported module or None if import fails
        """
        cache_key = f"{package}.{module_name}" if package else module_name
        
        # Return cached result
        if cache_key in self._import_cache:
            return self._import_cache[cache_key]
            
        # Skip if we know it failed before
        if cache_key in self._failed_imports:
            return None
            
        try:
            module = importlib.import_module(module_name, package)
            self._import_cache[cache_key] = module
            return module
        except ImportError as e:
            self._failed_imports[cache_key] = str(e)
            logger.debug(f"Failed to import {cache_key}: {e}")
            return None
    
    def import_from_path(self, module_path: Path, module_name: str) -> Optional[Any]:
        """
        Import a module from a specific file path
        
        Args:
            module_path: Path to the Python file
            module_name: Name to assign to the module
            
        Returns:
            Imported module or None if import fails
        """
        if not module_path.exists():
            return None
            
        try:
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None or spec.loader is None:
                return None
                
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            self._import_cache[module_name] = module
            return module
        except Exception as e:
            logger.debug(f"Failed to import {module_name} from {module_path}: {e}")
            return None
    
    def get_attribute(self, module_name: str, attr_name: str, 
                     default: Any = None, package: Optional[str] = None) -> Any:
        """
        Get an attribute from a module with fallback
        
        Args:
            module_name: Name of module
            attr_name: Name of attribute to get
            default: Default value if import or attribute lookup fails
            package: Package name for relative imports
            
        Returns:
            Attribute value or default
        """
        module = self.safe_import(module_name, package)
        if module is None:
            return default
            
        return getattr(module, attr_name, default)
    
    def clear_cache(self):
        """Clear import cache"""
        self._import_cache.clear()
        self._failed_imports.clear()

# Global import manager instance
import_manager = ImportManager()

def optional_import(module_name: str, package: Optional[str] = None):
    """
    Decorator for optional imports with graceful fallbacks
    
    Usage:
        @optional_import('some.optional.module')
        def use_optional_feature():
            # This only runs if the module is available
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            module = import_manager.safe_import(module_name, package)
            if module is None:
                logger.warning(f"Optional module {module_name} not available, skipping {func.__name__}")
                return None
            return func(*args, **kwargs)
        return wrapper
    return decorator

def require_import(module_name: str, package: Optional[str] = None, 
                  error_msg: Optional[str] = None):
    """
    Decorator that requires a module to be importable
    
    Usage:
        @require_import('required.module')
        def critical_function():
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            module = import_manager.safe_import(module_name, package)
            if module is None:
                msg = error_msg or f"Required module {module_name} is not available"
                raise ImportError(msg)
            return func(*args, **kwargs)
        return wrapper
    return decorator

def get_available_modules(module_names: List[str], package: Optional[str] = None) -> Dict[str, Any]:
    """
    Get all available modules from a list
    
    Args:
        module_names: List of module names to try importing
        package: Package name for relative imports
        
    Returns:
        Dictionary of module_name -> module for successfully imported modules
    """
    available = {}
    for module_name in module_names:
        module = import_manager.safe_import(module_name, package)
        if module is not None:
            available[module_name] = module
    return available

__all__ = [
    'ImportManager',
    'import_manager', 
    'optional_import',
    'require_import',
    'get_available_modules'
]
