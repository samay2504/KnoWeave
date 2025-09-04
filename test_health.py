#!/usr/bin/env python3
"""Quick test for health endpoints"""

import httpx
import asyncio
import json

async def test_health_endpoints():
    """Test the health endpoints"""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Test basic health
        try:
            response = await client.get(f"{base_url}/api/health")
            print(f"✅ Basic Health: {response.status_code}")
            print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"❌ Basic Health: {e}")
        
        # Test database health
        try:
            response = await client.get(f"{base_url}/api/health/database")
            print(f"✅ Database Health: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   MongoDB: {data.get('mongodb', {}).get('status', 'unknown')}")
                print(f"   ArangoDB: {data.get('arangodb', {}).get('status', 'unknown')}")
            else:
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"❌ Database Health: {e}")
        
        # Test agents health
        try:
            response = await client.get(f"{base_url}/api/health/agents")
            print(f"✅ Agents Health: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                agents = data.get('agents', {})
                for agent_name, status_info in agents.items():
                    status = status_info.get('status', 'unknown')
                    print(f"   {agent_name}: {status}")
            else:
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"❌ Agents Health: {e}")

if __name__ == "__main__":
    asyncio.run(test_health_endpoints())
