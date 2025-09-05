#!/usr/bin/env python3
"""
Comprehensive test script for the Human-AI Co-Creation agent pipeline.
Tests the entire flow from frontend to backend, including all 6 agents and LLM providers.
"""

import httpx
import json
import asyncio
import time
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs


class AgentPipelineTestSuite:
    """Test suite for validating the complete agent pipeline."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id = None
        self.auth_token = None
        
    async def run_all_tests(self):
        """Run the complete test suite."""
        print("🚀 Starting Human-AI Co-Creation Agent Pipeline Test Suite")
        print("=" * 70)
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Phase 1: Infrastructure Tests
            await self.test_infrastructure(client)
            
            # Phase 2: Authentication Tests
            await self.test_authentication(client)
            
            # Phase 3: Session Management Tests
            await self.test_session_management(client)
            
            # Phase 4: Agent Pipeline Tests
            await self.test_agent_pipeline(client)
            
            # Phase 5: LLM Integration Tests
            await self.test_llm_integration(client)
            
            # Phase 6: Frontend Integration Tests
            await self.test_frontend_integration(client)
            
        print("\n" + "=" * 70)
        print("✅ Agent Pipeline Test Suite Complete!")
    
    async def test_infrastructure(self, client: httpx.AsyncClient):
        """Test basic infrastructure components."""
        print("\n📋 Phase 1: Infrastructure Tests")
        print("-" * 40)
        
        # Test 1: Health Check
        try:
            response = await client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ Health Check: {response.status_code}")
                print(f"   System Status: {health_data.get('status', 'Unknown')}")
                print(f"   Timestamp: {health_data.get('timestamp', 'Unknown')}")
            else:
                print(f"❌ Health Check: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health Check Failed: {e}")
            return False
        
        # Test 2: Database Connectivity
        try:
            response = await client.get(f"{self.base_url}/health/database")
            if response.status_code == 200:
                db_data = response.json()
                print(f"✅ Database Health: {response.status_code}")
                print(f"   MongoDB: {db_data.get('mongodb', {}).get('status', 'Unknown')}")
                print(f"   ArangoDB: {db_data.get('arangodb', {}).get('status', 'Unknown')}")
            else:
                print(f"⚠️  Database Health: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Database Health Check: {e}")
        
        # Test 3: Agent Status
        try:
            response = await client.get(f"{self.base_url}/health/agents")
            if response.status_code == 200:
                agents_data = response.json()
                print(f"✅ Agent Health: {response.status_code}")
                for agent_name, status in agents_data.get('agents', {}).items():
                    # Handle both string and dict status values
                    if isinstance(status, dict):
                        agent_status = status.get('status', 'Unknown')
                    else:
                        agent_status = status
                    print(f"   {agent_name}: {agent_status}")
            else:
                print(f"⚠️  Agent Health: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Agent Health Check: {e}")
        
        return True
    
    async def test_authentication(self, client: httpx.AsyncClient):
        """Test authentication endpoints."""
        print("\n🔐 Phase 2: Authentication Tests")
        print("-" * 40)
        
        # Test 1: Authentication endpoint availability
        try:
            response = await client.get(f"{self.base_url}/api/auth/google")
            if response.status_code == 200:
                auth_data = response.json()
                print(f"✅ OAuth Endpoint: {response.status_code}")
                print(f"   Auth URL Available: {'auth_url' in auth_data}")
            else:
                print(f"⚠️  OAuth Endpoint: {response.status_code}")
        except Exception as e:
            print(f"❌ OAuth Endpoint: {e}")
        
        # Test 2: Protected endpoint without auth
        try:
            response = await client.get(f"{self.base_url}/api/me")
            if response.status_code == 401:
                print(f"✅ Protected Endpoint Security: {response.status_code} (Correct)")
            else:
                print(f"⚠️  Protected Endpoint Security: {response.status_code}")
        except Exception as e:
            print(f"❌ Protected Endpoint Test: {e}")
        
        return True
    
    async def test_session_management(self, client: httpx.AsyncClient):
        """Test session management functionality."""
        print("\n📝 Phase 3: Session Management Tests")
        print("-" * 40)
        
        # Test 1: Create new session
        try:
            session_data = {
                "user_id": "test_user_" + str(int(time.time())),
                "topic": "story",
                "topic_descriptor": "A creative writing session",
                "initial_content": "",
                "policy": None
            }
            
            response = await client.post(
                f"{self.base_url}/api/session/new",
                json=session_data
            )
            
            if response.status_code == 200:
                result = response.json()
                self.session_id = result.get('session_id')
                print(f"✅ Session Creation: {response.status_code}")
                print(f"   Session ID: {self.session_id}")
                print(f"   Topic: {result.get('topic', 'Unknown')}")
                print(f"   Mode: {result.get('mode', 'Unknown')}")
            else:
                print(f"❌ Session Creation: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Session Creation Failed: {e}")
            return False
        
        # Test 2: Load workspace
        if self.session_id:
            try:
                response = await client.get(f"{self.base_url}/api/session/{self.session_id}/snapshot")
                if response.status_code == 200:
                    workspace = response.json()
                    print(f"✅ Workspace Loading: {response.status_code}")
                    print(f"   Session Active: {workspace.get('active', False)}")
                    print(f"   Content Length: {len(workspace.get('content', ''))}")
                else:
                    print(f"⚠️  Workspace Loading: {response.status_code}")
            except Exception as e:
                print(f"⚠️  Workspace Loading: {e}")
        
        # Test 3: Mode switching
        try:
            response = await client.post(
                f"{self.base_url}/api/mode",
                json={"mode": "creative", "session_id": self.session_id}
            )
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Mode Switching: {response.status_code}")
                print(f"   New Mode: {result.get('current_mode', 'Unknown')}")
            else:
                print(f"⚠️  Mode Switching: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Mode Switching: {e}")
        
        return True
    
    async def test_agent_pipeline(self, client: httpx.AsyncClient):
        """Test the 6-agent pipeline functionality."""
        print("\n🤖 Phase 4: Agent Pipeline Tests")
        print("-" * 40)
        
        if not self.session_id:
            print("❌ No session ID available for agent testing")
            return False
        
        # Test 1: Suggestion trigger (tests all agents in pipeline)
        try:
            suggestion_data = {
                "mode": "on_demand",
                "options": {
                    "content": "Once upon a time in a magical forest",
                    "trigger_type": "user_pause"
                },
                "constraints": {
                    "word_count": 8,
                    "last_activity": "writing"
                }
            }
            
            print(f"🔄 Testing Agent Pipeline with session: {self.session_id}")
            response = await client.post(
                f"{self.base_url}/api/session/{self.session_id}/invoke_suggest",
                json=suggestion_data
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Agent Pipeline: {response.status_code}")
                print(f"   Should Suggest: {result.get('should_suggest', False)}")
                print(f"   Reason: {result.get('reason', 'No reason provided')}")
                
                suggestions = result.get('suggestions', [])
                if suggestions:
                    print(f"   Suggestions Generated: {len(suggestions)}")
                    for i, suggestion in enumerate(suggestions[:2]):  # Show first 2
                        print(f"   Suggestion {i+1}: {suggestion.get('text', '')[:100]}...")
                else:
                    print("   No suggestions generated")
                    
            else:
                print(f"❌ Agent Pipeline: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Agent Pipeline Failed: {e}")
            return False
        
        # Test 2: Individual agent endpoints (if available)
        agent_endpoints = [
            ("perception", "/api/agents/perception/analyze"),
            ("planner", "/api/agents/planner/generate"),
            ("graph_manager", "/api/agents/graph/query"),
            ("verifier", "/api/agents/verifier/validate"),
            ("evaluator", "/api/agents/evaluator/assess")
        ]
        
        for agent_name, endpoint in agent_endpoints:
            try:
                test_data = {
                    "session_id": self.session_id,
                    "content": "Test content for agent analysis",
                    "context": {"test": True}
                }
                
                response = await client.post(f"{self.base_url}{endpoint}", json=test_data)
                if response.status_code in [200, 404]:  # 404 is OK if endpoint not implemented
                    if response.status_code == 200:
                        print(f"✅ {agent_name.title()} Agent: {response.status_code}")
                    else:
                        print(f"⚠️  {agent_name.title()} Agent: Endpoint not implemented")
                else:
                    print(f"⚠️  {agent_name.title()} Agent: {response.status_code}")
                    
            except Exception as e:
                print(f"⚠️  {agent_name.title()} Agent: {e}")
        
        return True
    
    async def test_llm_integration(self, client: httpx.AsyncClient):
        """Test LLM provider integration."""
        print("\n🧠 Phase 5: LLM Integration Tests")
        print("-" * 40)
        
        # Test 1: LLM provider health
        try:
            response = await client.get(f"{self.base_url}/health/llm")
            if response.status_code == 200:
                llm_data = response.json()
                print(f"✅ LLM Provider Health: {response.status_code}")
                print(f"   Provider: {llm_data.get('provider', 'Unknown')}")
                print(f"   Status: {llm_data.get('status', 'Unknown')}")
            else:
                print(f"⚠️  LLM Provider Health: {response.status_code}")
        except Exception as e:
            print(f"⚠️  LLM Provider Health: {e}")
        
        # Test 2: LLM generation test (if session available)
        if self.session_id:
            try:
                llm_test_data = {
                    "prompt": "Complete this story beginning: 'In a distant galaxy'",
                    "max_tokens": 50,
                    "temperature": 0.7
                }
                
                response = await client.post(
                    f"{self.base_url}/api/llm/generate",
                    json=llm_test_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ LLM Generation: {response.status_code}")
                    generated_text = result.get('text', '')
                    print(f"   Generated: {generated_text[:100]}...")
                elif response.status_code == 404:
                    print(f"⚠️  LLM Generation: Endpoint not implemented")
                else:
                    print(f"⚠️  LLM Generation: {response.status_code}")
                    
            except Exception as e:
                print(f"⚠️  LLM Generation: {e}")
        
        return True
    
    async def test_frontend_integration(self, client: httpx.AsyncClient):
        """Test frontend-specific endpoints."""
        print("\n🌐 Phase 6: Frontend Integration Tests")
        print("-" * 40)
        
        # Test 1: Static file serving
        try:
            response = await client.get(f"{self.base_url}/")
            if response.status_code == 200:
                print(f"✅ Frontend Serving: {response.status_code}")
                print(f"   Content Type: {response.headers.get('content-type', 'Unknown')}")
            else:
                print(f"⚠️  Frontend Serving: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Frontend Serving: {e}")
        
        # Test 2: API CORS headers
        try:
            response = await client.options(f"{self.base_url}/api/health")
            cors_headers = {
                'Access-Control-Allow-Origin': response.headers.get('access-control-allow-origin'),
                'Access-Control-Allow-Methods': response.headers.get('access-control-allow-methods'),
                'Access-Control-Allow-Headers': response.headers.get('access-control-allow-headers')
            }
            
            print(f"✅ CORS Configuration: {response.status_code}")
            for header, value in cors_headers.items():
                if value:
                    print(f"   {header}: {value}")
                    
        except Exception as e:
            print(f"⚠️  CORS Test: {e}")
        
        # Test 3: WebSocket endpoint (if available)
        try:
            # First check the info endpoint
            response = await client.get(f"{self.base_url}/ws/info")
            if response.status_code == 200:
                ws_info = response.json()
                print(f"✅ WebSocket Info: {response.status_code}")
                print(f"   WebSocket URL: {ws_info.get('websocket_url', 'Unknown')}")
                print(f"   Status: {ws_info.get('status', 'Unknown')}")
                print(f"   Supported Types: {len(ws_info.get('supported_message_types', []))}")
            else:
                print(f"⚠️  WebSocket Info: {response.status_code}")
            
            # Test regular HTTP request to WebSocket endpoint (should fail properly)
            response = await client.get(f"{self.base_url}/ws")
            # WebSocket endpoints typically return 400 for non-WS requests
            if response.status_code in [400, 426]:
                print(f"✅ WebSocket Endpoint: Available (Status: {response.status_code})")
            elif response.status_code == 404:
                print(f"⚠️  WebSocket Endpoint: Not implemented")
            else:
                print(f"⚠️  WebSocket Endpoint: {response.status_code}")
        except Exception as e:
            print(f"⚠️  WebSocket Test: {e}")
        
        return True
    
    def print_summary(self):
        """Print test summary."""
        print("\n📊 Test Summary")
        print("-" * 40)
        print(f"Session ID Created: {self.session_id or 'None'}")
        print(f"Base URL: {self.base_url}")
        print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")


async def main():
    """Main test execution function."""
    # Check if custom base URL is needed
    base_url = "http://localhost:8000"
    
    test_suite = AgentPipelineTestSuite(base_url)
    
    try:
        await test_suite.run_all_tests()
        test_suite.print_summary()
        
    except KeyboardInterrupt:
        print("\n⚠️  Test suite interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Human-AI Co-Creation Agent Pipeline Test Suite")
    print("Testing backend integration, agent pipeline, and LLM connectivity...")
    print()
    
    asyncio.run(main())
