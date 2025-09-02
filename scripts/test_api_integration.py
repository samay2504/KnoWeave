#!/usr/bin/env python3
"""
API Integration Test Suite
Tests all endpoints used by the frontend UI
"""

import pytest
import asyncio
import json
import httpx
from datetime import datetime
from typing import Dict, Any, Optional
import uuid

# Test configuration
API_BASE_URL = "http://localhost:8001"
TEST_SESSION_ID = f"test_session_{uuid.uuid4().hex[:8]}"

class APIIntegrationTester:
    """Comprehensive API integration test runner"""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.client = None
        self.results = {
            "timestamp": datetime.utcnow().isoformat(),
            "endpoints": {},
            "overall_status": "PASS",
            "errors": []
        }
    
    async def setup(self):
        """Setup test client"""
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0
        )
    
    async def cleanup(self):
        """Cleanup test client"""
        if self.client:
            await self.client.aclose()
    
    async def test_endpoint(self, method: str, path: str, expected_status: int = 200, 
                           payload: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict[str, Any]:
        """Test a single endpoint"""
        endpoint_name = f"{method.upper()} {path}"
        result = {
            "method": method.upper(),
            "path": path,
            "status": "PASS",
            "response_code": None,
            "response_time_ms": None,
            "schema_valid": False,
            "error": None
        }
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            if method.upper() == "GET":
                response = await self.client.get(path, headers=headers)
            elif method.upper() == "POST":
                response = await self.client.post(path, json=payload, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            end_time = asyncio.get_event_loop().time()
            result["response_time_ms"] = round((end_time - start_time) * 1000, 2)
            result["response_code"] = response.status_code
            
            # Check if response code matches expected
            if response.status_code != expected_status:
                result["status"] = "FAIL"
                result["error"] = f"Expected {expected_status}, got {response.status_code}"
                self.results["overall_status"] = "FAIL"
            else:
                # Try to parse JSON and validate basic schema
                try:
                    json_data = response.json()
                    result["schema_valid"] = isinstance(json_data, dict)
                    result["response_sample"] = json_data if len(str(json_data)) < 500 else str(json_data)[:500] + "..."
                except:
                    result["schema_valid"] = False
        
        except Exception as e:
            result["status"] = "FAIL"
            result["error"] = str(e)
            self.results["overall_status"] = "FAIL"
            self.results["errors"].append(f"{endpoint_name}: {str(e)}")
        
        self.results["endpoints"][endpoint_name] = result
        return result
    
    async def run_all_tests(self):
        """Run all API endpoint tests"""
        await self.setup()
        
        try:
            # 1. Health check
            await self.test_endpoint("GET", "/api/health")
            
            # 2. Create new session
            session_payload = {
                "user_id": f"test_user_{uuid.uuid4().hex[:8]}",
                "initial_content": "Once upon a time in a digital realm...",
                "topic": "test_story",
                "policy": {"max_length": 1000}
            }
            session_result = await self.test_endpoint("POST", "/api/session/new", 200, session_payload)
            
            # Extract session ID from response if successful
            test_session_id = TEST_SESSION_ID
            if session_result["status"] == "PASS" and "response_sample" in session_result:
                try:
                    session_data = json.loads(session_result["response_sample"].replace("...", ""))
                    if "session_id" in session_data:
                        test_session_id = session_data["session_id"]
                except:
                    pass
            
            # 3. Get session snapshot
            await self.test_endpoint("GET", f"/api/session/{test_session_id}/snapshot")
            
            # 4. Invoke suggestions
            suggest_payload = {
                "mode": "suggest",
                "options": {"max_branches": 3},
                "context": {"current_position": 0}
            }
            await self.test_endpoint("POST", f"/api/session/{test_session_id}/invoke_suggest", 200, suggest_payload)
            
            # 5. Accept branch
            accept_payload = {
                "branch_id": "branch_0"
            }
            await self.test_endpoint("POST", f"/api/session/{test_session_id}/accept_branch", 200, accept_payload)
            
            # 6. Backtrack
            backtrack_payload = {
                "node_id": "root"
            }
            await self.test_endpoint("POST", f"/api/session/{test_session_id}/backtrack", 200, backtrack_payload)
            
            # 7. Auth endpoints
            await self.test_endpoint("GET", "/auth/google/login")
            await self.test_endpoint("GET", "/api/me", 401)  # Should fail without auth
            
        finally:
            await self.cleanup()
        
        return self.results


async def main():
    """Main test runner"""
    tester = APIIntegrationTester()
    results = await tester.run_all_tests()
    
    # Save results
    timestamp = "20250831T193910Z"  # Use consistent timestamp
    output_dir = f"internal_checks/ui_kg_run_{timestamp}"
    output_file = f"{output_dir}/api_integration_results.json"
    
    # Ensure directory exists
    import os
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"API integration test results saved to: {output_file}")
    print(f"Overall status: {results['overall_status']}")
    
    if results['overall_status'] == "FAIL":
        print("FAILED ENDPOINTS:")
        for endpoint, result in results['endpoints'].items():
            if result['status'] == "FAIL":
                print(f"  - {endpoint}: {result.get('error', 'Unknown error')}")
    
    return results['overall_status'] == "PASS"


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
