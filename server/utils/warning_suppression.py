#!/usr/bin/env python3
"""
Production Warning Suppression Module
Centralized warning management for Human-AI Co-Creation System
"""

import warnings
import os
import sys
import logging

def suppress_production_warnings():
    """
    Suppress all non-critical warnings for production deployment
    """
    # Suppress PyTorch distributed warnings
    os.environ['PYTORCH_DISABLE_WARNING'] = '1'
    os.environ['TORCH_DISABLE_WARNING'] = '1'
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # TensorFlow warnings
    
    # Filter specific warning categories
    warnings.filterwarnings("ignore", category=UserWarning, module="torch")
    warnings.filterwarnings("ignore", message=".*Redirects are currently not supported.*")
    warnings.filterwarnings("ignore", message=".*NOTE: Redirects.*")
    warnings.filterwarnings("ignore", message=".*multiprocessing.*redirects.*")
    
    # Suppress deprecation warnings in production
    if os.getenv('ENVIRONMENT', '').lower() == 'production':
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
    
    # Suppress specific library warnings
    warnings.filterwarnings("ignore", module="transformers")
    warnings.filterwarnings("ignore", module="huggingface_hub")
    warnings.filterwarnings("ignore", module="langchain")
    
    # Redirect torch warnings to logger instead of stderr
    torch_logger = logging.getLogger('torch')
    torch_logger.setLevel(logging.ERROR)

def setup_production_logging():
    """
    Configure logging for production environment
    """
    # Reduce verbosity of external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('transformers').setLevel(logging.WARNING)
    logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
    
    # Set torch logging to ERROR only
    logging.getLogger('torch').setLevel(logging.ERROR)
    logging.getLogger('torch.distributed').setLevel(logging.ERROR)

def initialize_production_environment():
    """
    Initialize production environment with proper warning suppression
    """
    suppress_production_warnings()
    setup_production_logging()
    
    # Verify suppression worked
    logger = logging.getLogger(__name__)
    logger.info("Production warning suppression initialized")

if __name__ == "__main__":
    initialize_production_environment()
