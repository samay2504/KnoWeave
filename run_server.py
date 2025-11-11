#!/usr/bin/env python3
"""
Production-grade server launcher for Human-AI Co-Creation System
Handles import paths and environment setup properly
"""

# CRITICAL: Suppress PyTorch warnings BEFORE any imports
import os
import warnings
import sys

# Comprehensive PyTorch warning suppression
os.environ['PYTORCH_DISABLE_WARNING'] = '1'
os.environ['TORCH_DISABLE_WARNING'] = '1'
os.environ['PYTORCH_WARNINGS'] = 'ignore'
os.environ['TORCH_WARNINGS'] = 'ignore'

# Suppress specific torch warnings
warnings.filterwarnings("ignore", message=".*Redirects are currently not supported.*")
warnings.filterwarnings("ignore", category=UserWarning, module="torch")
warnings.filterwarnings("ignore", message=".*multiprocessing.*redirects.*")

# Suppress at the module level before torch is imported anywhere
if 'torch' not in sys.modules:
    # Pre-emptive torch warning suppression
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            import torch.distributed.elastic.multiprocessing.redirects
            # Monkey patch the warning function
            original_warn = warnings.warn
            def silent_warn(message, category=UserWarning, stacklevel=1, source=None):
                if "Redirects are currently not supported" not in str(message):
                    original_warn(message, category, stacklevel, source)
            warnings.warn = silent_warn
        except ImportError:
            pass

import sys
from pathlib import Path

# Add server directory to Python path for proper imports
server_dir = Path(__file__).parent / "server"
sys.path.insert(0, str(server_dir))

# Initialize production warning suppression
try:

    from server.utils.warning_suppression import initialize_production_environment
    initialize_production_environment()
except ImportError:
    # Fallback: robust local warning suppression and logging config
    def suppress_production_warnings():
        os.environ['PYTORCH_DISABLE_WARNING'] = '1'
        os.environ['TORCH_DISABLE_WARNING'] = '1'
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
        warnings.filterwarnings("ignore", category=UserWarning, module="torch")
        warnings.filterwarnings("ignore", message=".*Redirects are currently not supported.*")
        warnings.filterwarnings("ignore", message=".*NOTE: Redirects.*")
        warnings.filterwarnings("ignore", message=".*multiprocessing.*redirects.*")
        if os.getenv('ENVIRONMENT', '').lower() == 'production':
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
        warnings.filterwarnings("ignore", module="transformers")
        warnings.filterwarnings("ignore", module="huggingface_hub")
        warnings.filterwarnings("ignore", module="langchain")
        import logging
        torch_logger = logging.getLogger('torch')
        torch_logger.setLevel(logging.ERROR)

    def setup_production_logging():
        import logging
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('transformers').setLevel(logging.WARNING)
        logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
        logging.getLogger('torch').setLevel(logging.ERROR)
        logging.getLogger('torch.distributed').setLevel(logging.ERROR)

    suppress_production_warnings()
    setup_production_logging()

# Set environment variables for production
os.environ.setdefault("PYTHONPATH", str(server_dir))

if __name__ == "__main__":
    try:
        print("🚀 Starting Human-AI Co-Creation Server...")
        # Change to server directory for consistent imports
        os.chdir(str(server_dir))

        # PRODUCTION FIX: Suppress Windows asyncio socket cleanup errors
        # These are harmless but pollute logs on Windows systems
        import asyncio
        import socket
        
        def custom_exception_handler(loop, context):
            """Suppress harmless Windows socket cleanup errors"""
            exception = context.get('exception')
            
            # Windows socket cleanup error - harmless, suppress it
            if isinstance(exception, (ConnectionResetError, ConnectionAbortedError)):
                error_msg = str(exception)
                # WinError 10054: Connection forcibly closed by remote host
                if 'WinError 10054' in error_msg or 'forcibly closed' in error_msg:
                    # This happens when client closes connection during cleanup
                    # It's a Windows asyncio quirk, not a real error
                    return
            
            # For other exceptions, use default handling
            if exception:
                loop.default_exception_handler(context)
        
        # Apply custom exception handler to asyncio loop
        try:
            loop = asyncio.get_event_loop()
            loop.set_exception_handler(custom_exception_handler)
        except RuntimeError:
            # Loop not available yet, will be set when uvicorn starts
            pass

        # Import and run the server
        from server.app import app
        import uvicorn

        # Get configuration
        port = int(os.getenv("BACKEND_PORT", 8000))
        host = os.getenv("SERVER_HOST", "0.0.0.0")
        debug = os.getenv("DEBUG", "false").lower() == "true"

        print(f"📡 Server starting on http://{host}:{port}")
        print(f"🔧 Debug mode: {debug}")
        print(f"📊 Health Check: http://localhost:{port}/api/status")
        print(f"🔍 API Docs: http://localhost:{port}/docs")

        # Start the server with reload disabled for production stability
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=False,  # Disable reload to prevent import issues
            access_log=True,
            log_level="info"
        )
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
