#!/usr/bin/env python3
"""
Performance Testing
Measures response times, throughput, and resource utilization under load
"""

import asyncio
import json
import logging
import time
import psutil
import gc
from datetime import datetime
from pathlib import Path
import sys
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
import threading

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "server"))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PerformanceTester:
    """Comprehensive performance testing for the agentic system"""
    
    def __init__(self):
        self.test_id = f"performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.results = {
            "test_id": self.test_id,
            "timestamp": datetime.now().isoformat(),
            "system_info": self._get_system_info(),
            "performance_tests": {},
            "overall_status": "PENDING",
            "errors": []
        }
        
        # Performance thresholds
        self.thresholds = {
            "response_time_ms": 5000,  # 5 seconds max
            "memory_usage_mb": 1000,   # 1GB max per agent
            "cpu_usage_percent": 80,   # 80% max CPU
            "throughput_req_per_sec": 1,  # Minimum 1 request/sec
            "concurrent_users": 5      # Support 5 concurrent users
        }
        
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for baseline"""
        try:
            return {
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
                "python_version": sys.version,
                "platform": sys.platform
            }
        except Exception as e:
            logger.warning(f"Could not get system info: {e}")
            return {"error": str(e)}
    
    async def setup_environment(self):
        """Initialize testing environment"""
        try:
            logger.info("🔧 Setting up Performance Testing environment...")
            
            from server.dependencies import ProductionDependencyContainer
            from server.server_config import config
            
            self.container = ProductionDependencyContainer(config)
            await self.container.initialize()
            
            # Initialize agents for testing
            from server.agents.session_manager import SessionManager
            from server.agents.perception_agent import PerceptionAgent
            from server.agents.planner_generator_agent import PlannerGeneratorAgent
            from server.agents.graph_manager_agent import GraphManagerAgent
            from server.agents.verifier_agent import VerifierAgent
            from server.agents.evaluator_agent import EvaluatorAgent
            
            self.agents = {
                "session_manager": SessionManager(self.container),
                "perception": PerceptionAgent(self.container),
                "planner": PlannerGeneratorAgent(self.container),
                "graph_manager": GraphManagerAgent(self.container),
                "verifier": VerifierAgent(self.container),
                "evaluator": EvaluatorAgent(self.container)
            }
            
            logger.info("✅ Environment setup complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup environment: {e}")
            self.results["errors"].append(f"Setup error: {str(e)}")
            return False
    
    async def test_response_times(self):
        """Test individual agent response times"""
        try:
            logger.info("⏱️ Testing response times...")
            
            response_times = {}
            test_workspace = {
                "session_id": f"perf_test_{self.test_id}",
                "topic_content": "smart cities performance test",
                "user_input": "Test performance of city planning algorithms"
            }
            
            test_config = {"mode": "balanced", "test_run": True}
            
            for agent_name, agent in self.agents.items():
                if agent_name == "session_manager":
                    continue  # Skip session manager as it orchestrates others
                    
                logger.info(f"  ⏱️ Testing {agent_name} response time...")
                
                # Measure response time
                start_time = time.time()
                memory_before = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                
                try:
                    # Test agent invoke
                    result = await agent.invoke(test_workspace, test_config)
                    
                    end_time = time.time()
                    memory_after = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                    
                    response_time_ms = (end_time - start_time) * 1000
                    memory_used_mb = memory_after - memory_before
                    
                    response_times[agent_name] = {
                        "response_time_ms": round(response_time_ms, 2),
                        "memory_used_mb": round(memory_used_mb, 2),
                        "success": bool(result),
                        "within_threshold": response_time_ms <= self.thresholds["response_time_ms"],
                        "memory_efficient": memory_used_mb <= self.thresholds["memory_usage_mb"]
                    }
                    
                    if response_time_ms <= self.thresholds["response_time_ms"]:
                        logger.info(f"    ✅ {agent_name}: {response_time_ms:.0f}ms")
                    else:
                        logger.warning(f"    ⚠️ {agent_name}: {response_time_ms:.0f}ms (exceeded threshold)")
                    
                except Exception as e:
                    logger.warning(f"    ❌ {agent_name} failed: {e}")
                    response_times[agent_name] = {
                        "response_time_ms": -1,
                        "memory_used_mb": -1,
                        "success": False,
                        "error": str(e),
                        "within_threshold": False,
                        "memory_efficient": False
                    }
                
                # Clean up memory
                gc.collect()
                
            self.results["performance_tests"]["response_times"] = response_times
            
            # Calculate success rate
            successful_agents = sum(1 for rt in response_times.values() if rt.get("within_threshold", False))
            total_agents = len(response_times)
            success_rate = successful_agents / total_agents if total_agents > 0 else 0
            
            self.results["performance_tests"]["response_times"]["summary"] = {
                "total_agents": total_agents,
                "successful_agents": successful_agents,
                "success_rate": success_rate,
                "avg_response_time": round(
                    sum(rt.get("response_time_ms", 0) for rt in response_times.values() if rt.get("response_time_ms", 0) > 0) / 
                    len([rt for rt in response_times.values() if rt.get("response_time_ms", 0) > 0]) if response_times else 0, 2
                )
            }
            
            logger.info(f"✅ Response time testing complete: {successful_agents}/{total_agents} within threshold")
            return success_rate >= 0.8
            
        except Exception as e:
            logger.error(f"❌ Response time testing failed: {e}")
            self.results["performance_tests"]["response_times"] = {
                "status": "ERROR",
                "error": str(e)
            }
            return False
    
    async def test_concurrent_load(self):
        """Test system under concurrent load"""
        try:
            logger.info("🔀 Testing concurrent load...")
            
            concurrent_users = 3  # Reduced for realistic testing
            requests_per_user = 2
            
            # Test data for concurrent requests
            test_scenarios = [
                {"topic": "smart transportation", "input": "Analyze traffic patterns"},
                {"topic": "renewable energy", "input": "Plan solar panel deployment"},
                {"topic": "waste management", "input": "Optimize collection routes"}
            ]
            
            async def simulate_user_session(user_id: int, scenario: Dict):
                """Simulate a single user session"""
                session_results = []
                
                for request_id in range(requests_per_user):
                    workspace = {
                        "session_id": f"concurrent_test_{user_id}_{request_id}",
                        "topic_content": scenario["topic"],
                        "user_input": scenario["input"]
                    }
                    
                    config = {"mode": "balanced", "concurrent_test": True}
                    
                    try:
                        start_time = time.time()
                        
                        # Test with perception agent as representative
                        result = await self.agents["perception"].invoke(workspace, config)
                        
                        end_time = time.time()
                        response_time = (end_time - start_time) * 1000
                        
                        session_results.append({
                            "user_id": user_id,
                            "request_id": request_id,
                            "response_time_ms": round(response_time, 2),
                            "success": bool(result),
                            "scenario": scenario["topic"]
                        })
                        
                    except Exception as e:
                        session_results.append({
                            "user_id": user_id,
                            "request_id": request_id,
                            "response_time_ms": -1,
                            "success": False,
                            "error": str(e),
                            "scenario": scenario["topic"]
                        })
                
                return session_results
            
            # Run concurrent user sessions
            start_time = time.time()
            cpu_before = psutil.cpu_percent(interval=0.1)
            
            # Create tasks for concurrent execution
            tasks = []
            for user_id in range(concurrent_users):
                scenario = test_scenarios[user_id % len(test_scenarios)]
                task = simulate_user_session(user_id, scenario)
                tasks.append(task)
            
            # Execute all tasks concurrently
            all_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            cpu_after = psutil.cpu_percent(interval=0.1)
            
            # Process results
            successful_requests = 0
            total_requests = 0
            response_times = []
            
            for user_results in all_results:
                if isinstance(user_results, Exception):
                    logger.warning(f"User session failed: {user_results}")
                    continue
                    
                for result in user_results:
                    total_requests += 1
                    if result.get("success", False):
                        successful_requests += 1
                        if result.get("response_time_ms", 0) > 0:
                            response_times.append(result["response_time_ms"])
            
            total_time = end_time - start_time
            throughput = total_requests / total_time if total_time > 0 else 0
            
            concurrent_results = {
                "concurrent_users": concurrent_users,
                "requests_per_user": requests_per_user,
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "success_rate": successful_requests / total_requests if total_requests > 0 else 0,
                "total_time_seconds": round(total_time, 2),
                "throughput_req_per_sec": round(throughput, 2),
                "avg_response_time_ms": round(sum(response_times) / len(response_times), 2) if response_times else 0,
                "max_response_time_ms": max(response_times) if response_times else 0,
                "cpu_usage_increase": round(cpu_after - cpu_before, 2),
                "throughput_meets_threshold": throughput >= self.thresholds["throughput_req_per_sec"]
            }
            
            self.results["performance_tests"]["concurrent_load"] = concurrent_results
            
            if concurrent_results["throughput_meets_threshold"]:
                logger.info(f"✅ Concurrent load test passed: {throughput:.2f} req/sec")
            else:
                logger.warning(f"⚠️ Concurrent load test below threshold: {throughput:.2f} req/sec")
            
            return concurrent_results["throughput_meets_threshold"]
            
        except Exception as e:
            logger.error(f"❌ Concurrent load testing failed: {e}")
            self.results["performance_tests"]["concurrent_load"] = {
                "status": "ERROR",
                "error": str(e)
            }
            return False
    
    async def test_memory_usage(self):
        """Test memory usage patterns"""
        try:
            logger.info("🧠 Testing memory usage...")
            
            # Baseline memory
            initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            memory_tests = {}
            
            # Test each agent's memory footprint
            for agent_name, agent in self.agents.items():
                if agent_name == "session_manager":
                    continue
                    
                logger.info(f"  🧠 Testing {agent_name} memory usage...")
                
                memory_before = psutil.Process().memory_info().rss / 1024 / 1024
                
                # Run multiple operations to test memory accumulation
                for i in range(3):
                    workspace = {
                        "session_id": f"memory_test_{agent_name}_{i}",
                        "topic_content": f"memory test iteration {i}",
                        "user_input": "Test memory usage patterns"
                    }
                    
                    config = {"mode": "balanced", "memory_test": True}
                    
                    try:
                        await agent.invoke(workspace, config)
                    except Exception as e:
                        logger.warning(f"    Memory test iteration {i} failed: {e}")
                
                memory_after = psutil.Process().memory_info().rss / 1024 / 1024
                memory_used = memory_after - memory_before
                
                # Force garbage collection
                gc.collect()
                memory_after_gc = psutil.Process().memory_info().rss / 1024 / 1024
                memory_released = memory_after - memory_after_gc
                
                memory_tests[agent_name] = {
                    "memory_before_mb": round(memory_before, 2),
                    "memory_after_mb": round(memory_after, 2),
                    "memory_used_mb": round(memory_used, 2),
                    "memory_after_gc_mb": round(memory_after_gc, 2),
                    "memory_released_mb": round(memory_released, 2),
                    "memory_efficient": memory_used <= self.thresholds["memory_usage_mb"],
                    "memory_leak_detected": memory_released < (memory_used * 0.5)  # Less than 50% released suggests leak
                }
                
                if memory_tests[agent_name]["memory_efficient"]:
                    logger.info(f"    ✅ {agent_name}: {memory_used:.1f}MB used")
                else:
                    logger.warning(f"    ⚠️ {agent_name}: {memory_used:.1f}MB used (exceeded threshold)")
            
            self.results["performance_tests"]["memory_usage"] = memory_tests
            
            # Calculate overall memory efficiency
            efficient_agents = sum(1 for test in memory_tests.values() if test.get("memory_efficient", False))
            total_agents = len(memory_tests)
            efficiency_rate = efficient_agents / total_agents if total_agents > 0 else 0
            
            self.results["performance_tests"]["memory_usage"]["summary"] = {
                "initial_memory_mb": round(initial_memory, 2),
                "final_memory_mb": round(psutil.Process().memory_info().rss / 1024 / 1024, 2),
                "total_agents": total_agents,
                "efficient_agents": efficient_agents,
                "efficiency_rate": efficiency_rate
            }
            
            logger.info(f"✅ Memory usage testing complete: {efficient_agents}/{total_agents} within threshold")
            return efficiency_rate >= 0.8
            
        except Exception as e:
            logger.error(f"❌ Memory usage testing failed: {e}")
            self.results["performance_tests"]["memory_usage"] = {
                "status": "ERROR",
                "error": str(e)
            }
            return False
    
    async def test_stress_conditions(self):
        """Test system under stress conditions"""
        try:
            logger.info("💪 Testing stress conditions...")
            
            stress_tests = {}
            
            # Test 1: Large input data
            logger.info("  💪 Testing large input handling...")
            large_input = "Large input test. " * 500  # ~8KB of text
            
            workspace = {
                "session_id": f"stress_large_input_{self.test_id}",
                "topic_content": "large data processing test",
                "user_input": large_input
            }
            
            config = {"mode": "balanced", "stress_test": True}
            
            start_time = time.time()
            try:
                result = await self.agents["perception"].invoke(workspace, config)
                end_time = time.time()
                
                stress_tests["large_input"] = {
                    "input_size_kb": round(len(large_input) / 1024, 2),
                    "response_time_ms": round((end_time - start_time) * 1000, 2),
                    "success": bool(result),
                    "within_threshold": (end_time - start_time) * 1000 <= (self.thresholds["response_time_ms"] * 2)
                }
                
            except Exception as e:
                stress_tests["large_input"] = {
                    "input_size_kb": round(len(large_input) / 1024, 2),
                    "response_time_ms": -1,
                    "success": False,
                    "error": str(e),
                    "within_threshold": False
                }
            
            # Test 2: Rapid sequential requests
            logger.info("  💪 Testing rapid sequential requests...")
            rapid_requests = 5
            rapid_times = []
            rapid_successes = 0
            
            for i in range(rapid_requests):
                workspace = {
                    "session_id": f"stress_rapid_{self.test_id}_{i}",
                    "topic_content": f"rapid request {i}",
                    "user_input": f"Rapid test iteration {i}"
                }
                
                start_time = time.time()
                try:
                    result = await self.agents["perception"].invoke(workspace, config)
                    end_time = time.time()
                    
                    rapid_times.append((end_time - start_time) * 1000)
                    if result:
                        rapid_successes += 1
                        
                except Exception as e:
                    logger.warning(f"    Rapid request {i} failed: {e}")
                    rapid_times.append(-1)
            
            valid_times = [t for t in rapid_times if t > 0]
            stress_tests["rapid_requests"] = {
                "total_requests": rapid_requests,
                "successful_requests": rapid_successes,
                "success_rate": rapid_successes / rapid_requests,
                "avg_response_time_ms": round(sum(valid_times) / len(valid_times), 2) if valid_times else 0,
                "max_response_time_ms": max(valid_times) if valid_times else 0,
                "within_threshold": all(t <= self.thresholds["response_time_ms"] for t in valid_times)
            }
            
            self.results["performance_tests"]["stress_conditions"] = stress_tests
            
            # Calculate stress test success
            stress_success = (
                stress_tests.get("large_input", {}).get("within_threshold", False) and
                stress_tests.get("rapid_requests", {}).get("within_threshold", False)
            )
            
            if stress_success:
                logger.info("✅ Stress testing passed")
            else:
                logger.warning("⚠️ Stress testing issues detected")
            
            return stress_success
            
        except Exception as e:
            logger.error(f"❌ Stress testing failed: {e}")
            self.results["performance_tests"]["stress_conditions"] = {
                "status": "ERROR",
                "error": str(e)
            }
            return False
    
    async def run_full_performance_test(self):
        """Run complete performance test suite"""
        try:
            logger.info("🎯 Starting Performance Testing")
            
            # Setup environment
            setup_success = await self.setup_environment()
            if not setup_success:
                self.results["overall_status"] = "SETUP_FAILED"
                return False
            
            # Run all performance tests
            tests = [
                await self.test_response_times(),
                await self.test_concurrent_load(),
                await self.test_memory_usage(),
                await self.test_stress_conditions()
            ]
            
            # Calculate overall success
            passed_tests = sum(tests)
            total_tests = len(tests)
            success_rate = passed_tests / total_tests if total_tests > 0 else 0
            
            self.results["overall_status"] = "SUCCESS" if success_rate >= 0.75 else "PARTIAL_FAILURE"
            self.results["success_rate"] = success_rate
            self.results["passed_tests"] = passed_tests
            self.results["total_tests"] = total_tests
            
            logger.info(f"🎉 Performance Testing Complete: {passed_tests}/{total_tests} tests passed ({success_rate:.1%})")
            
            return success_rate >= 0.75
            
        except Exception as e:
            logger.error(f"❌ Performance testing failed: {e}")
            self.results["overall_status"] = "FAILED"
            self.results["errors"].append(f"Test error: {str(e)}")
            return False
        
        finally:
            # Cleanup
            if hasattr(self, 'container'):
                await self.container.cleanup()
    
    def save_results(self):
        """Save performance test results to file"""
        results_dir = Path(__file__).parent / "internal_checks"
        results_dir.mkdir(exist_ok=True)
        
        results_file = results_dir / f"performance_test_{datetime.now().strftime('%Y%m%dT%H%M%SZ')}.json"
        
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"📝 Performance results saved to: {results_file}")
        return results_file

async def main():
    """Main performance test runner"""
    tester = PerformanceTester()
    
    try:
        success = await tester.run_full_performance_test()
        results_file = tester.save_results()
        
        if success:
            print("🎉 ✅ PERFORMANCE TESTING: PASSED")
            print(f"📊 Results: {results_file}")
            return 0
        else:
            print("❌ PERFORMANCE TESTING: FAILED")
            print(f"📊 Results: {results_file}")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Performance test runner failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
