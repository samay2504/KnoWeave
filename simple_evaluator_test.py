#!/usr/bin/env python3
"""
Simple evaluator test to isolate the issue
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Set debug logging
logging.basicConfig(level=logging.DEBUG)

# Add server to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
os.chdir(current_dir)

from server.agents.evaluator_agent import EvaluatorAgent

async def simple_test():
    """Simple test to debug the issue"""
    try:
        agent = EvaluatorAgent({})
        
        # Simple test data
        workspace = {
            'session_id': 'test',
            'branches': [
                {
                    'branch_id': 'A',
                    'title': 'Test Branch',
                    'rationale': 'Test rationale',
                    'steps': ['step1'],
                    'cost_estimate': {'tokens': 100, 'time_ms': 1000},
                    'safety_checks': ['ok']
                }
            ]
        }
        
        print(f"Workspace type: {type(workspace)}")
        print(f"Branches type: {type(workspace['branches'])}")
        print(f"First branch type: {type(workspace['branches'][0])}")
        print(f"First branch content: {workspace['branches'][0]}")
        
        result = await agent.invoke(workspace, {})
        print(f"✅ SUCCESS: {result}")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(simple_test())
    print(f"Result: {'PASS' if success else 'FAIL'}")
