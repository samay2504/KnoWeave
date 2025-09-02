#!/usr/bin/env python3
"""
Run script for Human-AI Co-Creation Server
Handles proper Python path setup for module imports
"""

import sys
import os
from pathlib import Path

# Add the project root and server directory to Python path
project_root = Path(__file__).parent
server_dir = project_root / "server"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(server_dir))

# Now we can import and run the server
if __name__ == "__main__":
    try:
        # Change to server directory so relative paths work
        os.chdir(str(server_dir))
        
        # Import from the server module
        from app import app
        from utils.logging_cfg import get_api_logger
        
        import uvicorn
        from server_config import config
        
        logger = get_api_logger()
        
        logger.info("🚀 Starting Human-AI Co-Creation Server...")
        logger.info(f"📊 Health Check: http://localhost:{config.port}/health")
        logger.info(f"🔍 API Docs: http://localhost:{config.port}/docs")
        logger.info(f"🌐 Frontend URL: {config.frontend_url}")
        
        uvicorn.run(
            "app:app",  # Use import string for reload support
            host=config.host,
            port=config.port,
            reload=config.debug,
            log_level=config.log_level.lower()
        )
        
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
