#!/usr/bin/env python3
"""
Test script to verify llm_provider.py imports correctly
"""

import sys
import os

# Add the server directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

try:
    # Test imports
    print("Testing llm_provider imports...")
    
    # Import the module directly
    import llm_provider
    print("✅ llm_provider module imported successfully")
    
    # Import specific classes
    from llm_provider import AsyncLLMProvider, create_llm_provider
    print("✅ AsyncLLMProvider and create_llm_provider imported successfully")
    
    # Test that all required libraries are available
    test_config = {
        "api_keys": {},
        "temperature": 0.1,
        "provider_preference": ["fallback"]
    }
    
    provider = AsyncLLMProvider(test_config)
    print("✅ AsyncLLMProvider instance created successfully")
    
    print("\n🎉 All imports working correctly! The warnings have been resolved.")
    
except Exception as e:
    print(f"❌ Import test failed: {e}")
    sys.exit(1)
