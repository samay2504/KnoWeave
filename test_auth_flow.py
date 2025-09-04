#!/usr/bin/env python3
"""Test script to verify the authentication flow."""

import httpx
import json
import asyncio
from urllib.parse import urlparse, parse_qs


async def test_auth_flow():
    """Test the complete authentication flow."""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("Testing authentication endpoints...")
        
        # Test 1: Health check
        try:
            response = await client.get(f"{base_url}/health")
            print(f"✓ Health check: {response.status_code}")
        except Exception as e:
            print(f"✗ Health check failed: {e}")
            return
        
        # Test 2: Check if /api/auth/google endpoint exists
        try:
            response = await client.get(f"{base_url}/api/auth/google")
            print(f"✓ /api/auth/google endpoint: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"  Auth URL available: {'auth_url' in data}")
        except Exception as e:
            print(f"✗ /api/auth/google failed: {e}")
        
        # Test 3: Check if /auth/google/login endpoint exists
        try:
            response = await client.get(f"{base_url}/auth/google/login")
            print(f"✓ /auth/google/login endpoint: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"  Auth URL available: {'auth_url' in data}")
        except Exception as e:
            print(f"✗ /auth/google/login failed: {e}")
        
        # Test 4: Test /api/me without authentication
        try:
            response = await client.get(f"{base_url}/api/me")
            print(f"✓ /api/me without auth: {response.status_code} (should be 401)")
        except Exception as e:
            print(f"✗ /api/me test failed: {e}")
        
        # Test 5: Test with invalid token
        try:
            headers = {"Cookie": "auth_token=invalid_token"}
            response = await client.get(f"{base_url}/api/me", headers=headers)
            print(f"✓ /api/me with invalid token: {response.status_code} (should be 401)")
        except Exception as e:
            print(f"✗ /api/me with invalid token failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_auth_flow())
