#!/usr/bin/env python3
"""
Comprehensive Warning Suppression Module
Use this to suppress all warnings across the project for clean test output
"""

import warnings
import os
import sys
import logging

def suppress_all_warnings():
    """Suppress all warnings and configure clean logging"""
    
    # Comprehensive warning suppression
    warnings.filterwarnings("ignore")
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
    warnings.filterwarnings("ignore", category=ImportWarning)
    warnings.filterwarnings("ignore", category=ResourceWarning)
    
    # Specific package warnings
    warnings.filterwarnings("ignore", message=".*pkg_resources.*")
    warnings.filterwarnings("ignore", module="pkg_resources")
    warnings.filterwarnings("ignore", module="aioarango")
    warnings.filterwarnings("ignore", module="arango")
    warnings.filterwarnings("ignore", module="urllib3")
    warnings.filterwarnings("ignore", module="httpx")
    warnings.filterwarnings("ignore", module="httpcore")
    warnings.filterwarnings("ignore", module="requests")
    
    # Environment variables to suppress warnings
    os.environ['PYTHONWARNINGS'] = 'ignore'
    os.environ['URLLIB3_DISABLE_WARNINGS'] = '1'
    
    # Suppress urllib3 warnings
    try:
        import urllib3
        urllib3.disable_warnings()
    except ImportError:
        pass
    
    # Suppress requests warnings
    try:
        import requests
        from requests.packages.urllib3.exceptions import InsecureRequestWarning
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    except (ImportError, AttributeError):
        pass

def configure_clean_logging(logger_name: str = __name__, level: int = logging.INFO):
    """Configure clean logging with suppressed third-party noise"""
    
    # Suppress all warnings first
    suppress_all_warnings()
    
    # Setup clean logging format
    logging.basicConfig(
        level=logging.WARNING,  # Set root logger to WARNING to reduce noise
        format='%(levelname)s:%(name)s:%(message)s',
        handlers=[logging.StreamHandler()],
        force=True  # Override any existing configuration
    )
    
    # Create our specific logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    
    # Suppress noisy third-party loggers
    noisy_loggers = [
        "urllib3", "httpx", "httpcore", "aioarango", "arango",
        "requests", "asyncio", "dotenv", "pkg_resources",
        "db.arango_client", "server_config", "multipart"
    ]
    
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    return logger

def silent_import(import_statement: str):
    """Execute an import statement silently, suppressing all output"""
    import io
    from contextlib import redirect_stderr, redirect_stdout
    
    try:
        f = io.StringIO()
        with redirect_stderr(f), redirect_stdout(f):
            exec(import_statement)
        return True
    except Exception:
        return False

# Auto-suppress warnings when this module is imported
suppress_all_warnings()
