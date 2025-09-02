#!/usr/bin/env python3
"""
Human-AI Co-Creation System
Main entry point for the application
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from server.utils.logging_cfg import get_logger

logger = get_logger("startup")


def main():
    """Main entry point"""
    logger.info("Human-AI Co-Creation System - Starting up")

    # Check environment
    if not os.path.exists(".env"):
        logger.warning("No .env file found - using default configuration")
        logger.info("Copy .env.example to .env and configure your settings")

    # Run the development server with uvicorn
    try:
        import uvicorn

        logger.info("Starting development server with uvicorn")
        uvicorn.run(
            "server.app:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
        )
    except ImportError:
        logger.error("uvicorn not installed - install with: pip install uvicorn")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application failed to start: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
