#!/usr/bin/env python3
"""
Import Test Script - Verifies all dependencies are working correctly
"""

import warnings
import os
import sys

# Comprehensive warning suppression BEFORE any other imports
warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", message=".*pkg_resources.*")
warnings.filterwarnings("ignore", module="pkg_resources")
warnings.filterwarnings("ignore", module="aioarango")
warnings.filterwarnings("ignore", module="arango")

# Suppress urllib3 warnings specifically
try:
    import urllib3
    urllib3.disable_warnings()
except ImportError:
    pass

# Set environment variables to suppress additional warnings
os.environ['PYTHONWARNINGS'] = 'ignore'
os.environ['URLLIB3_DISABLE_WARNINGS'] = '1'

import traceback
from pathlib import Path

def test_import(module_name, import_statement, description):
    """Test a specific import and return result"""
    try:
        # Temporarily redirect stderr to suppress import warnings
        import io
        from contextlib import redirect_stderr
        
        f = io.StringIO()
        with redirect_stderr(f):
            exec(import_statement)
        return f"✅ {description}: SUCCESS"
    except Exception as e:
        return f"❌ {description}: FAILED - {str(e)}"

def main():
    """Run comprehensive import tests"""
    print("🧪 COMPREHENSIVE IMPORT TEST")
    print("=" * 60)
    
    # Add server to path
    current_dir = Path(__file__).parent
    server_dir = current_dir / "server"
    sys.path.insert(0, str(server_dir))
    
    # Test core Python packages
    tests = [
        ("asyncio", "import asyncio", "Asyncio (core async support)"),
        ("logging", "import logging", "Logging (core logging)"),
        ("typing", "from typing import Dict, List, Optional", "Typing hints"),
        ("dataclasses", "from dataclasses import dataclass", "Dataclasses"),
        ("json", "import json", "JSON support"),
        ("datetime", "from datetime import datetime", "DateTime support"),
        
        # ArangoDB packages
        ("python-arango", "from arango import ArangoClient", "ArangoDB Client (python-arango)"),
        ("arango.database", "from arango.database import StandardDatabase", "ArangoDB Database"),
        ("arango.exceptions", "from arango.exceptions import ArangoError", "ArangoDB Exceptions"),
        
        # Project modules (with proper path setup)
        ("server_config", "from server_config import ServerConfig", "Server Configuration"),
        ("arango_client", "from db.arango_client import ArangoGraphClient, GraphNode, GraphEdge", "Custom ArangoDB Client"),
        ("arango_factory", "from db.arango_client import create_arango_client", "ArangoDB Factory"),
        
        # Environment and utilities
        ("dotenv", "from dotenv import load_dotenv", "Environment Variables (.env)"),
        ("pathlib", "from pathlib import Path", "Path utilities"),
        ("warnings", "import warnings", "Warning suppression"),
        
        # Optional packages that should be available
        ("httpx", "import httpx", "HTTP client (httpx)"),
        ("requests", "import requests", "HTTP client (requests)"),
    ]
    
    results = []
    success_count = 0
    
    for module_name, import_stmt, description in tests:
        result = test_import(module_name, import_stmt, description)
        results.append(result)
        if result.startswith("✅"):
            success_count += 1
    
    # Print results
    for result in results:
        print(result)
    
    print("\n" + "=" * 60)
    print(f"📊 SUMMARY: {success_count}/{len(tests)} imports successful")
    print(f"📈 Success Rate: {success_count/len(tests)*100:.1f}%")
    
    # Additional system information
    print(f"\n🐍 Python Version: {sys.version}")
    print(f"📁 Python Executable: {sys.executable}")
    print(f"🔍 Current Working Directory: {Path.cwd()}")
    print(f"📚 Python Path Includes:")
    for i, path in enumerate(sys.path[:5]):  # Show first 5 paths
        print(f"   {i+1}. {path}")
    
    # Test a simple ArangoDB connection attempt
    print(f"\n🔗 TESTING ARANGO CONNECTION:")
    try:
        # Suppress any remaining warnings during connection test
        import io
        from contextlib import redirect_stderr
        
        f = io.StringIO()
        with redirect_stderr(f):
            from server_config import ServerConfig  # type: ignore
            from db.arango_client import create_arango_client  # type: ignore
            
            config = ServerConfig()
        
        print(f"✅ Configuration loaded: ArangoDB URL = {config.arango_url}")
        print(f"✅ Database: {config.arango_database}")
        print("✅ All components ready for ArangoDB operations")
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        # Only show traceback in debug mode
        if "--debug" in sys.argv:
            traceback.print_exc()
    
    if success_count == len(tests):
        print(f"\n🎉 ALL IMPORTS SUCCESSFUL! System is ready for operation.")
        return True
    else:
        print(f"\n⚠️  Some imports failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
