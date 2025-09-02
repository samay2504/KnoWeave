#!/usr/bin/env python3
"""
Frontend Integration Test Suite
Tests frontend-backend communication, OAuth flow, and API endpoints
Part of BTP Human-AI Co-Creation integration checks.
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, List
from pathlib import Path
import sys

# Add server to path
sys.path.append(str(Path(__file__).parent.parent))


class FrontendIntegrationTester:
    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url
        self.backend_url = "http://localhost:8000"
        self.results = {
            "test_summary": {},
            "api_tests": {},
            "oauth_tests": {},
            "websocket_tests": {},
            "errors": [],
            "warnings": [],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive frontend integration tests"""
        print("🌐 Starting frontend integration tests...")

        # Test API endpoints
        await self._test_api_endpoints()

        # Test health endpoints
        await self._test_health_endpoints()

        # Test OAuth flow (mock)
        await self._test_oauth_integration()

        # Test WebSocket connections
        await self._test_websocket_connection()

        # Test static file serving
        await self._test_static_files()

        # Generate summary
        self._generate_test_summary()

        return self.results

    async def _test_api_endpoints(self):
        """Test backend API endpoints"""
        print("🔌 Testing API endpoints...")

        api_tests = {}

        async with aiohttp.ClientSession() as session:
            # Test core endpoints
            endpoints = [
                ("/api/health", "GET", None),
                ("/api/health/detailed", "GET", None),
                ("/api/auth/status", "GET", None),
                # ("/api/sessions", "POST", {"user_id": "test_user", "topic": "story"}),
                # ("/api/agents/perception", "POST", {"content": "Test content"}),
            ]

            for endpoint, method, payload in endpoints:
                try:
                    url = f"{self.backend_url}{endpoint}"
                    start_time = time.time()

                    if method == "GET":
                        async with session.get(url) as response:
                            status = response.status
                            data = await response.text()
                            response_time = (time.time() - start_time) * 1000

                    elif method == "POST":
                        async with session.post(url, json=payload) as response:
                            status = response.status
                            data = await response.text()
                            response_time = (time.time() - start_time) * 1000

                    api_tests[endpoint] = {
                        "status": "✅ PASSED" if status < 500 else "❌ FAILED",
                        "http_status": status,
                        "response_time_ms": response_time,
                        "has_response": len(data) > 0,
                    }

                    if status >= 500:
                        self.results["errors"].append(
                            f"❌ API endpoint {endpoint} returned {status}"
                        )

                except Exception as e:
                    api_tests[endpoint] = {"status": "❌ FAILED", "error": str(e)}
                    self.results["errors"].append(
                        f"❌ API test failed for {endpoint}: {str(e)}"
                    )

        self.results["api_tests"] = api_tests

    async def _test_health_endpoints(self):
        """Test health monitoring endpoints"""
        print("🏥 Testing health endpoints...")

        health_tests = {}

        async with aiohttp.ClientSession() as session:
            health_endpoints = [
                "/api/health",
                "/api/health/detailed",
                "/api/health/readiness",
                "/api/health/liveness",
            ]

            for endpoint in health_endpoints:
                try:
                    url = f"{self.backend_url}{endpoint}"
                    start_time = time.time()

                    async with session.get(url) as response:
                        status = response.status
                        data = (
                            await response.json()
                            if response.content_type == "application/json"
                            else await response.text()
                        )
                        response_time = (time.time() - start_time) * 1000

                    health_tests[endpoint] = {
                        "status": (
                            "✅ PASSED"
                            if status == 200
                            else "⚠️  DEGRADED" if status == 503 else "❌ FAILED"
                        ),
                        "http_status": status,
                        "response_time_ms": response_time,
                        "has_json": isinstance(data, dict),
                    }

                except Exception as e:
                    health_tests[endpoint] = {"status": "❌ FAILED", "error": str(e)}
                    self.results["errors"].append(
                        f"❌ Health endpoint test failed for {endpoint}: {str(e)}"
                    )

        self.results["api_tests"]["health"] = health_tests

    async def _test_oauth_integration(self):
        """Test OAuth integration (mock flow)"""
        print("🔐 Testing OAuth integration...")

        oauth_tests = {}

        # Test OAuth configuration availability
        try:
            from server.server_config import ServerConfig

            config = ServerConfig()
            oauth_config = config.get_google_oauth_config()

            oauth_tests["config_loading"] = {
                "status": "✅ PASSED" if oauth_config else "❌ FAILED",
                "has_client_id": bool(oauth_config.get("client_id")),
                "has_client_secret": bool(oauth_config.get("client_secret")),
                "has_redirect_uri": bool(oauth_config.get("redirect_uris")),
            }

        except Exception as e:
            oauth_tests["config_loading"] = {"status": "❌ FAILED", "error": str(e)}
            self.results["errors"].append(f"❌ OAuth config test failed: {str(e)}")

        # Test OAuth endpoints (if available)
        async with aiohttp.ClientSession() as session:
            oauth_endpoints = ["/auth/google", "/auth/callback", "/auth/logout"]

            for endpoint in oauth_endpoints:
                try:
                    url = f"{self.backend_url}{endpoint}"

                    async with session.get(url) as response:
                        status = response.status

                        oauth_tests[endpoint] = {
                            "status": (
                                "✅ AVAILABLE"
                                if status != 404
                                else "⚠️  NOT_IMPLEMENTED"
                            ),
                            "http_status": status,
                        }

                except Exception as e:
                    oauth_tests[endpoint] = {"status": "❌ FAILED", "error": str(e)}

        self.results["oauth_tests"] = oauth_tests

    async def _test_websocket_connection(self):
        """Test WebSocket connections"""
        print("🔌 Testing WebSocket connections...")

        websocket_tests = {}

        try:
            import websockets

            # Test WebSocket endpoint
            ws_url = "ws://localhost:8000/ws"

            try:
                async with websockets.connect(ws_url, timeout=5) as websocket:
                    # Send test message
                    test_message = {"type": "ping", "data": "test"}
                    await websocket.send(json.dumps(test_message))

                    # Wait for response
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)

                    websocket_tests["connection"] = {
                        "status": "✅ PASSED",
                        "response_received": bool(response),
                    }

            except asyncio.TimeoutError:
                websocket_tests["connection"] = {
                    "status": "⚠️  TIMEOUT",
                    "error": "WebSocket connection timeout",
                }
                self.results["warnings"].append("⚠️  WebSocket connection timeout")

            except Exception as e:
                websocket_tests["connection"] = {"status": "❌ FAILED", "error": str(e)}
                self.results["warnings"].append(f"⚠️  WebSocket not available: {str(e)}")

        except ImportError:
            websocket_tests["connection"] = {
                "status": "⚠️  SKIPPED",
                "error": "websockets package not installed",
            }
            self.results["warnings"].append(
                "⚠️  WebSocket tests skipped - websockets package not installed"
            )

        self.results["websocket_tests"] = websocket_tests

    async def _test_static_files(self):
        """Test static file serving"""
        print("📁 Testing static file serving...")

        static_tests = {}

        async with aiohttp.ClientSession() as session:
            # Test common static files
            static_files = [
                "/favicon.ico",
                "/static/css/main.css",
                "/static/js/main.js",
                "/",  # Root HTML
            ]

            for file_path in static_files:
                try:
                    url = f"{self.base_url}{file_path}"

                    async with session.get(url) as response:
                        status = response.status
                        content_type = response.headers.get("content-type", "")

                        static_tests[file_path] = {
                            "status": (
                                "✅ AVAILABLE"
                                if status == 200
                                else "⚠️  NOT_FOUND" if status == 404 else "❌ ERROR"
                            ),
                            "http_status": status,
                            "content_type": content_type,
                        }

                except Exception as e:
                    static_tests[file_path] = {"status": "❌ FAILED", "error": str(e)}
                    self.results["warnings"].append(
                        f"⚠️  Static file test failed for {file_path}: {str(e)}"
                    )

        self.results["api_tests"]["static_files"] = static_tests

    def _generate_test_summary(self):
        """Generate test summary"""
        total_errors = len(self.results["errors"])
        total_warnings = len(self.results["warnings"])

        # Count passed/failed tests
        all_tests = []
        for test_category in [
            self.results["api_tests"],
            self.results["oauth_tests"],
            self.results["websocket_tests"],
        ]:
            if isinstance(test_category, dict):
                for test_name, test_result in test_category.items():
                    if isinstance(test_result, dict):
                        if test_result.get("status", "").startswith("✅"):
                            all_tests.append("passed")
                        elif test_result.get("status", "").startswith("⚠️"):
                            all_tests.append("warning")
                        else:
                            all_tests.append("failed")

        passed_tests = all_tests.count("passed")
        failed_tests = all_tests.count("failed")
        warning_tests = all_tests.count("warning")
        total_tests = len(all_tests)

        if failed_tests == 0 and total_errors == 0:
            if warning_tests > 0 or total_warnings > 0:
                status = f"⚠️  PASSED WITH WARNINGS ({warning_tests + total_warnings} warnings)"
            else:
                status = "🎉 ALL TESTS PASSED"
        else:
            status = f"❌ SOME TESTS FAILED ({failed_tests} failed, {warning_tests} warnings)"

        self.results["test_summary"] = {
            "final_status": status,
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "warnings": warning_tests,
            "errors": total_errors,
            "test_coverage": f"{passed_tests}/{total_tests} tests passed",
        }

        print(f"\n{'='*60}")
        print(f"🌐 FRONTEND INTEGRATION TESTS COMPLETE")
        print(f"{'='*60}")
        print(f"Status: {status}")
        print(f"Tests: {passed_tests}/{total_tests} passed")
        print(f"Errors: {total_errors}")
        print(f"Warnings: {total_warnings + warning_tests}")
        print(f"Timestamp: {self.results['timestamp']}")
        print(f"{'='*60}")


async def main():
    """Main execution function"""
    tester = FrontendIntegrationTester()
    results = await tester.run_all_tests()

    # Save results
    results_file = Path("data/frontend_integration_results.json")
    results_file.parent.mkdir(exist_ok=True)

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n📄 Results saved to: {results_file}")

    # Exit with error code if tests failed
    if results["errors"] or any(
        "❌" in str(test)
        for test in [
            results["api_tests"],
            results["oauth_tests"],
            results["websocket_tests"],
        ]
    ):
        print("\n❌ Some integration tests failed - check results above")
        return 1
    else:
        print("\n✅ Integration tests completed successfully")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
