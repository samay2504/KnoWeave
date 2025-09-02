#!/usr/bin/env python3
"""
Simple test runner to validate basic functionality without complex conftest
"""

import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that core modules can be imported"""
    try:
        from server.app import app
        print("PASS: FastAPI app imports successfully")
        
        from server.agents.session_manager import SessionManager
        print("PASS: SessionManager imports successfully")
        
        from server.utils.schemas import SessionResponse
        print("PASS: Schemas import successfully")
        
        return True
    except Exception as e:
        print(f"FAIL: Import test failed: {e}")
        return False

def test_config():
    """Test configuration loading"""
    try:
        from server.server_config import ServerConfig
        config = ServerConfig()
        # Check available attributes
        available_attrs = [attr for attr in dir(config) if not attr.startswith('_')]
        print(f"PASS: Config loaded - Available attrs: {available_attrs[:5]}...")  # Show first 5
        return True
    except Exception as e:
        print(f"FAIL: Config test failed: {e}")
        return False

async def test_session_manager():
    """Test basic SessionManager functionality"""
    try:
        from server.server_config import ServerConfig
        from server.agents.session_manager import SessionManager
        
        config = ServerConfig()
        session_manager = SessionManager(config)
        
        # Check available methods
        methods = [method for method in dir(session_manager) if not method.startswith('_')]
        print(f"PASS: SessionManager created - Available methods: {methods[:5]}...")
        
        return True
    except Exception as e:
        print(f"FAIL: SessionManager test failed: {e}")
        return False

def main():
    print("=== Simple Backend Tests ===")
    
    tests = [
        ("Import Tests", test_imports),
        ("Config Tests", test_config),
        ("SessionManager Tests", lambda: asyncio.run(test_session_manager())),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\nRunning {test_name}...")
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"FAIL: {test_name} failed with exception: {e}")
            failed += 1
    
    print(f"\n=== Results ===")
    print(f"Passed: {passed}, Failed: {failed}")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
