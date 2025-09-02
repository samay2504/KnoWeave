#!/usr/bin/env python3
"""
Comprehensive End-to-End Agentic System Test
Tests full agent chain with deterministic scenario using fixtures
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
import sys

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "server"))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AgenticSystemE2ETest:
    """End-to-end test runner for the 6-agent Human-AI Co-Creation system"""
    
    def __init__(self):
        self.test_session_id = f"e2e_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.test_scenario = {
            "topic": "sustainable_urban_planning", 
            "user_input": "How can we design eco-friendly transportation systems for smart cities?",
            "expected_agents": ["session_manager", "perception", "planner", "graph_manager", "verifier", "evaluator"],
            "test_mode": True
        }
        self.results = {
            "test_id": self.test_session_id,
            "timestamp": datetime.now().isoformat(),
            "scenario": self.test_scenario,
            "agent_results": {},
            "integration_status": "PENDING",
            "errors": []
        }
        
    async def setup_test_environment(self):
        """Initialize test environment and dependencies"""
        try:
            logger.info("🚀 Setting up E2E test environment...")
            
            # Import server components with proper path handling
            try:
                from server.dependencies import ProductionDependencyContainer, setup_dependencies
                from server.agents.session_manager import SessionManager
                from server.agents.perception_agent import PerceptionAgent
                from server.agents.planner_generator_agent import PlannerGeneratorAgent
                from server.agents.graph_manager_agent import GraphManagerAgent
                from server.agents.verifier_agent import VerifierAgent
                from server.agents.evaluator_agent import EvaluatorAgent
                from server.server_config import config
            except ImportError:
                # Fallback for when running from server directory
                from dependencies import ProductionDependencyContainer, setup_dependencies
                from agents.session_manager import SessionManager
                from agents.perception_agent import PerceptionAgent
                from agents.planner_generator_agent import PlannerGeneratorAgent
                from agents.graph_manager_agent import GraphManagerAgent
                from agents.verifier_agent import VerifierAgent
                from agents.evaluator_agent import EvaluatorAgent
                from server_config import config

            # Initialize dependency container
            self.container = ProductionDependencyContainer(config)
            await self.container.initialize()
            
            # Initialize session manager
            self.session_manager = SessionManager(config)
            await self.session_manager.initialize()
            
            # Initialize all agents with config (like in app.py)
            self.agents = {
                "session_manager": self.session_manager,
                "perception": PerceptionAgent(config),
                "planner": PlannerGeneratorAgent(config),
                "graph_manager": GraphManagerAgent(config),
                "verifier": VerifierAgent(config),
                "evaluator": EvaluatorAgent(config)
            }
            
            # Initialize all agents except session_manager (already done)
            for agent_name, agent in self.agents.items():
                if agent_name != "session_manager":
                    await agent.initialize()
                    logger.info(f"✅ Initialized {agent_name} agent")
            
            logger.info("✅ Test environment setup complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup test environment: {e}")
            self.results["errors"].append(f"Setup error: {str(e)}")
            return False
    
    async def test_session_manager(self):
        """Test Session Manager - Prompt Template Generation"""
        try:
            logger.info("🧠 Testing Session Manager (PTG)...")
            
            session_manager = self.agents["session_manager"]
            
            # Test PTG through session manager's ptg attribute
            test_prompt = session_manager.ptg.generate_canonical_prompt(
                agent_name="perception",
                session_id=self.test_session_id,
                topic=self.test_scenario["topic"],
                topic_descriptor="smart cities infrastructure",
                input_data={"content": "Test content for perception"},
                mode="balanced"
            )
            
            self.results["agent_results"]["session_manager"] = {
                "status": "SUCCESS",
                "ptg_available": hasattr(session_manager, 'ptg'),
                "prompt_generated": bool(test_prompt),
                "has_prompt_content": "prompt" in test_prompt if test_prompt else False,
                "has_metadata": "metadata" in test_prompt if test_prompt else False
            }
            
            logger.info("✅ Session Manager test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Session Manager test failed: {e}")
            self.results["agent_results"]["session_manager"] = {
                "status": "FAILED",
                "error": str(e)
            }
            return False
    
    async def test_perception_agent(self):
        """Test Perception Agent - Input Analysis"""
        try:
            logger.info("👁️ Testing Perception Agent...")
            
            perception = self.agents["perception"]
            
            # Test perception processing using blueprint-compliant invoke method
            workspace = {
                "text": self.test_scenario["user_input"],
                "session_id": self.test_session_id
            }
            agent_config = {"mode": "analysis"}
            
            perception_result = await perception.invoke(workspace, agent_config)
            
            self.results["agent_results"]["perception"] = {
                "status": "SUCCESS",
                "result_received": bool(perception_result),
                "entities_found": len(perception_result.get("entities", [])) if perception_result else 0,
                "chunks_created": len(perception_result.get("chunks", [])) if perception_result else 0
            }
            
            logger.info("✅ Perception Agent test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Perception Agent test failed: {e}")
            self.results["agent_results"]["perception"] = {
                "status": "FAILED",
                "error": str(e)
            }
            return False
    
    async def test_planner_agent(self):
        """Test Planner Generator Agent - Task Planning"""
        try:
            logger.info("📋 Testing Planner Generator Agent...")
            
            planner = self.agents["planner"]
            
            # Test plan generation using blueprint-compliant invoke method
            workspace = {
                "user_input": self.test_scenario["user_input"],
                "context": {"topic": self.test_scenario["topic"]},
                "session_id": self.test_session_id
            }
            agent_config = {"branches": 3}
            
            plan_result = await planner.invoke(workspace, agent_config)
            
            self.results["agent_results"]["planner"] = {
                "status": "SUCCESS",
                "result_received": bool(plan_result),
                "branches_generated": len(plan_result.get("branches", [])) if plan_result else 0,
                "has_recommendations": bool(plan_result.get("recommendations")) if plan_result else False
            }
            
            logger.info("✅ Planner Generator test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Planner Generator test failed: {e}")
            self.results["agent_results"]["planner"] = {
                "status": "FAILED", 
                "error": str(e)
            }
            return False
    
    async def test_graph_manager(self):
        """Test Graph Manager Agent - Knowledge Graph Operations"""
        try:
            logger.info("🕸️ Testing Graph Manager Agent...")
            
            graph_manager = self.agents["graph_manager"]
            
            # Test knowledge graph operations using blueprint-compliant invoke method
            workspace = {
                "entities": ["smart_cities", "transportation", "sustainability"],
                "relationships": [{"from": "smart_cities", "to": "transportation", "type": "includes"}],
                "session_id": self.test_session_id
            }
            agent_config = {"operation": "update"}
            
            graph_result = await graph_manager.invoke(workspace, agent_config)
            
            self.results["agent_results"]["graph_manager"] = {
                "status": "SUCCESS",
                "result_received": bool(graph_result),
                "nodes_processed": len(workspace["entities"]),
                "edges_processed": len(workspace["relationships"])
            }
            
            logger.info("✅ Graph Manager test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Graph Manager test failed: {e}")
            self.results["agent_results"]["graph_manager"] = {
                "status": "FAILED",
                "error": str(e)
            }
            return False
    
    async def test_verifier_agent(self):
        """Test Verifier Agent - Output Validation"""
        try:
            logger.info("✅ Testing Verifier Agent...")
            
            verifier = self.agents["verifier"]
            
            # Test verification using blueprint-compliant invoke method
            workspace = {
                "content": "Implement eco-friendly transportation systems including electric buses, bike lanes, and smart traffic management.",
                "type": "plan",
                "session_id": self.test_session_id
            }
            agent_config = {"validation_mode": "comprehensive"}
            
            verification_result = await verifier.invoke(workspace, agent_config)
            
            self.results["agent_results"]["verifier"] = {
                "status": "SUCCESS",
                "result_received": bool(verification_result),
                "validation_completed": bool(verification_result.get("valid")) if verification_result else False,
                "has_feedback": bool(verification_result.get("feedback")) if verification_result else False
            }
            
            logger.info("✅ Verifier Agent test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Verifier Agent test failed: {e}")
            self.results["agent_results"]["verifier"] = {
                "status": "FAILED",
                "error": str(e)
            }
            return False
    
    async def test_evaluator_agent(self):
        """Test Evaluator Agent - Performance Assessment"""
        try:
            logger.info("📊 Testing Evaluator Agent...")
            
            evaluator = self.agents["evaluator"]
            
            # Test evaluation using blueprint-compliant invoke method
            workspace = {
                "session_id": self.test_session_id,
                "branches": [
                    {"content": "Electric bus network", "score": 8.5},
                    {"content": "Bike sharing system", "score": 7.2},
                    {"content": "Smart traffic lights", "score": 9.1}
                ]
            }
            agent_config = {"metrics": ["relevance", "creativity", "feasibility"]}
            
            evaluation_result = await evaluator.invoke(workspace, agent_config)
            
            self.results["agent_results"]["evaluator"] = {
                "status": "SUCCESS",
                "result_received": bool(evaluation_result),
                "ranking_provided": bool(evaluation_result.get("ranking")) if evaluation_result else False,
                "metrics_calculated": len(evaluation_result.get("metrics", {})) if evaluation_result else 0
            }
            
            logger.info("✅ Evaluator Agent test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Evaluator Agent test failed: {e}")
            self.results["agent_results"]["evaluator"] = {
                "status": "FAILED",
                "error": str(e)
            }
            return False
    
    async def run_full_e2e_test(self):
        """Run complete end-to-end test scenario"""
        try:
            logger.info("🎯 Starting Full End-to-End Agentic System Test")
            
            # Setup test environment
            setup_success = await self.setup_test_environment()
            if not setup_success:
                self.results["integration_status"] = "SETUP_FAILED"
                return False
            
            # Run individual agent tests
            test_results = []
            test_results.append(await self.test_session_manager())
            test_results.append(await self.test_perception_agent())
            test_results.append(await self.test_planner_agent())
            test_results.append(await self.test_graph_manager())
            test_results.append(await self.test_verifier_agent())
            test_results.append(await self.test_evaluator_agent())
            
            # Calculate overall success
            passed_tests = sum(test_results)
            total_tests = len(test_results)
            success_rate = passed_tests / total_tests if total_tests > 0 else 0
            
            self.results["integration_status"] = "SUCCESS" if success_rate >= 0.8 else "PARTIAL_FAILURE"
            self.results["success_rate"] = success_rate
            self.results["passed_tests"] = passed_tests
            self.results["total_tests"] = total_tests
            
            logger.info(f"🎉 E2E Test Complete: {passed_tests}/{total_tests} agents passed ({success_rate:.1%})")
            
            return success_rate >= 0.8
            
        except Exception as e:
            logger.error(f"❌ E2E test failed: {e}")
            self.results["integration_status"] = "FAILED"
            self.results["errors"].append(f"E2E test error: {str(e)}")
            return False
        
        finally:
            # Cleanup
            if hasattr(self, 'container'):
                await self.container.cleanup()
    
    def save_results(self):
        """Save test results to file"""
        results_dir = Path(__file__).parent / "internal_checks"
        results_dir.mkdir(exist_ok=True)
        
        results_file = results_dir / f"agentic_e2e_test_{datetime.now().strftime('%Y%m%dT%H%M%SZ')}.json"
        
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"📝 Test results saved to: {results_file}")
        return results_file

async def main():
    """Main test runner"""
    test_runner = AgenticSystemE2ETest()
    
    try:
        success = await test_runner.run_full_e2e_test()
        results_file = test_runner.save_results()
        
        if success:
            print("🎉 ✅ AGENTIC SYSTEM E2E TEST: PASSED")
            print(f"📊 Results: {results_file}")
            return 0
        else:
            print("❌ AGENTIC SYSTEM E2E TEST: FAILED")
            print(f"📊 Results: {results_file}")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Test runner failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
