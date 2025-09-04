#!/usr/bin/env python3
"""
Test script to verify perception_agent.py imports correctly
"""

import sys
import os

# Add the server directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

try:
    # Test imports
    print("Testing perception_agent imports...")
    
    # Import the module directly
    from server.agents import perception_agent
    print("✅ perception_agent module imported successfully")
    
    # Import specific classes
    from server.agents.perception_agent import PerceptionAgent, create_perception_agent
    print("✅ PerceptionAgent and create_perception_agent imported successfully")
    
    # Test that all required libraries are available
    test_config = {
        "temperature": 0.1,
    }
    
    agent = PerceptionAgent(test_config)
    print("✅ PerceptionAgent instance created successfully")
    
    print("\n🎉 All imports working correctly! The warnings have been resolved.")
    
except Exception as e:
    print(f"❌ Import test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
