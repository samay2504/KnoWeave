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
    from utils.warning_suppression import initialize_production_environment
    initialize_production_environment()
except ImportError:
    # Fallback basic warning suppression
    warnings.filterwarnings("ignore", message=".*multiprocessing.*redirects.*")

# Set environment variables for production
os.environ.setdefault("PYTHONPATH", str(server_dir))

if __name__ == "__main__":
    try:
        print("🚀 Starting Human-AI Co-Creation Server...")
        
        # Change to server directory for consistent imports
        os.chdir(str(server_dir))
        
        # Import and run the server
        from app import app
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
