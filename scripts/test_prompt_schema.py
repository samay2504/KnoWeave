#!/usr/bin/env python3
"""
Prompt Schema Validation Check
Validates all prompts conform to canonical schema structure and content requirements
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
import sys
from typing import Dict, Any, List, Optional

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "server"))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PromptSchemaValidator:
    """Comprehensive prompt schema validation for canonical system"""
    
    def __init__(self):
        self.test_id = f"prompt_schema_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.results = {
            "test_id": self.test_id,
            "timestamp": datetime.now().isoformat(),
            "validations": {},
            "overall_status": "PENDING",
            "errors": []
        }
        
        # Required canonical schema structure - updated for actual PTG return format
        self.required_schema_keys = [
            "prompt",
            "temperature", 
            "max_tokens",
            "schema",
            "metadata"
        ]
        
        # Metadata required fields
        self.required_metadata_keys = [
            "agent",
            "session_id",
            "schema_version",
            "generated_at"
        ]
        
        # Agent-specific prompt requirements
        self.agent_requirements = {
            "perception": {
                "must_contain": ["entity extraction", "relationship identification", "semantic analysis"],
                "input_types": ["text", "content"],
                "output_format": "structured_entities"
            },
            "planner": {
                "must_contain": ["plan generation", "action sequencing", "objective alignment"],
                "input_types": ["entities", "relationships"],
                "output_format": "execution_plan"
            },
            "graph_manager": {
                "must_contain": ["node creation", "edge formation", "graph optimization"],
                "input_types": ["entities", "plan"],
                "output_format": "graph_updates"
            },
            "verifier": {
                "must_contain": ["consistency check", "validation rules", "quality assessment"],
                "input_types": ["graph_state", "content"],
                "output_format": "verification_report"
            },
            "evaluator": {
                "must_contain": ["ranking criteria", "scoring mechanism", "comparative analysis"],
                "input_types": ["branches", "alternatives"],
                "output_format": "ranked_results"
            }
        }
        
    async def setup_environment(self):
        """Initialize PTG system"""
        try:
            logger.info("🔧 Setting up Prompt Schema Validation environment...")
            
            # Import PTG directly
            from server.agents.session_manager import PromptTemplateGenerator
            
            # Create PTG instance
            self.ptg = PromptTemplateGenerator()
            
            logger.info("✅ Environment setup complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup environment: {e}")
            self.results["errors"].append(f"Setup error: {str(e)}")
            return False
    
    def validate_prompt_structure(self, prompt_data: Dict[str, Any], agent_name: str) -> Dict[str, Any]:
        """Validate prompt follows canonical schema structure"""
        validation_result = {
            "agent_name": agent_name,
            "structure_valid": True,
            "missing_keys": [],
            "content_checks": {},
            "errors": []
        }
        
        try:
            # Check required schema keys
            for key in self.required_schema_keys:
                if key not in prompt_data:
                    validation_result["missing_keys"].append(key)
                    validation_result["structure_valid"] = False
            
            # Check metadata structure
            metadata = prompt_data.get("metadata", {})
            missing_metadata = []
            for key in self.required_metadata_keys:
                if key not in metadata:
                    missing_metadata.append(key)
                    validation_result["structure_valid"] = False
            
            if missing_metadata:
                validation_result["missing_keys"].extend([f"metadata.{key}" for key in missing_metadata])
            
            # Validate agent-specific requirements
            if agent_name in self.agent_requirements:
                requirements = self.agent_requirements[agent_name]
                prompt_text = prompt_data.get("prompt", "").lower()
                
                # Check required content in prompt
                content_found = []
                for required_content in requirements["must_contain"]:
                    if required_content.lower() in prompt_text:
                        content_found.append(required_content)
                
                validation_result["content_checks"]["required_content"] = {
                    "expected": requirements["must_contain"],
                    "found": content_found,
                    "coverage": len(content_found) / len(requirements["must_contain"])
                }
                
                # Check schema exists and has structure
                schema = prompt_data.get("schema", {})
                validation_result["content_checks"]["output_schema"] = {
                    "schema_defined": bool(schema),
                    "has_properties": "properties" in schema if isinstance(schema, dict) else False,
                    "schema_type": type(schema).__name__
                }
                
                # Check prompt length and structure
                validation_result["content_checks"]["prompt_structure"] = {
                    "prompt_length": len(prompt_text),
                    "has_system_section": "system:" in prompt_text.lower(),
                    "has_instructions": len(prompt_text) > 100,  # Reasonable length check
                    "mentions_agent": agent_name.lower() in prompt_text.lower()
                }
            
            # Validate temperature and max_tokens are reasonable
            temperature = prompt_data.get("temperature", 0)
            max_tokens = prompt_data.get("max_tokens", 0)
            
            validation_result["content_checks"]["generation_params"] = {
                "temperature_valid": 0 <= temperature <= 2,
                "max_tokens_valid": max_tokens > 0,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
        except Exception as e:
            validation_result["errors"].append(f"Validation error: {str(e)}")
            validation_result["structure_valid"] = False
        
        return validation_result
    
    async def validate_all_agent_prompts(self):
        """Validate prompts for all agents"""
        try:
            logger.info("📋 Validating prompts for all agents...")
            
            validation_results = {}
            test_topic = "smart cities infrastructure"
            test_session_id = f"schema_test_{self.test_id}"
            
            for agent_name in self.agent_requirements.keys():
                try:
                    logger.info(f"  🔍 Validating {agent_name} prompt...")
                    
                    # Generate canonical prompt
                    prompt_data = self.ptg.generate_canonical_prompt(
                        agent_name=agent_name,
                        session_id=test_session_id,
                        topic=test_topic,
                        topic_descriptor="urban planning and technology integration",
                        input_data={"content": f"Test content for {agent_name}"},
                        mode="balanced"
                    )
                    
                    # Validate prompt structure
                    validation = self.validate_prompt_structure(prompt_data, agent_name)
                    validation_results[agent_name] = validation
                    
                    if validation["structure_valid"]:
                        logger.info(f"    ✅ {agent_name} prompt validation passed")
                    else:
                        logger.warning(f"    ⚠️ {agent_name} prompt validation issues detected")
                    
                except Exception as e:
                    logger.error(f"    ❌ {agent_name} prompt validation failed: {e}")
                    validation_results[agent_name] = {
                        "agent_name": agent_name,
                        "structure_valid": False,
                        "errors": [str(e)]
                    }
            
            self.results["validations"]["agent_prompts"] = validation_results
            
            # Calculate success rate
            valid_prompts = sum(1 for v in validation_results.values() if v.get("structure_valid", False))
            total_prompts = len(validation_results)
            success_rate = valid_prompts / total_prompts if total_prompts > 0 else 0
            
            self.results["validations"]["agent_prompts"]["summary"] = {
                "total_agents": total_prompts,
                "valid_prompts": valid_prompts,
                "success_rate": success_rate
            }
            
            logger.info(f"✅ Agent prompt validation complete: {valid_prompts}/{total_prompts} passed ({success_rate:.1%})")
            return success_rate >= 0.8
            
        except Exception as e:
            logger.error(f"❌ Agent prompt validation failed: {e}")
            self.results["validations"]["agent_prompts"] = {
                "status": "ERROR",
                "error": str(e)
            }
            return False
    
    async def validate_topic_coverage(self):
        """Validate prompts work across different topics"""
        try:
            logger.info("🌍 Validating topic coverage...")
            
            test_topics = [
                {"topic": "renewable energy", "descriptor": "sustainable power generation"},
                {"topic": "healthcare innovation", "descriptor": "medical technology advancement"},
                {"topic": "autonomous vehicles", "descriptor": "self-driving transportation systems"},
                {"topic": "artificial intelligence", "descriptor": "machine learning applications"}
            ]
            
            topic_results = {}
            
            for topic_data in test_topics:
                topic = topic_data["topic"]
                descriptor = topic_data["descriptor"]
                topic_key = topic.replace(" ", "_")
                
                logger.info(f"  🎯 Testing topic: {topic}")
                
                try:
                    # Test with perception agent as representative
                    prompt_data = self.ptg.generate_canonical_prompt(
                        agent_name="perception",
                        session_id=f"topic_test_{topic_key}",
                        topic=topic,
                        topic_descriptor=descriptor,
                        input_data={"content": f"Test content about {topic}"},
                        mode="balanced"
                    )
                    
                    # Check topic relevance
                    prompt_text = prompt_data.get("prompt", "").lower()
                    topic_mentioned = topic.lower() in prompt_text
                    descriptor_mentioned = any(word in prompt_text for word in descriptor.lower().split())
                    
                    topic_results[topic_key] = {
                        "topic": topic,
                        "prompt_generated": bool(prompt_data),
                        "topic_mentioned": topic_mentioned,
                        "descriptor_mentioned": descriptor_mentioned,
                        "relevant_content": topic_mentioned or descriptor_mentioned
                    }
                    
                    if topic_results[topic_key]["relevant_content"]:
                        logger.info(f"    ✅ {topic} coverage validated")
                    else:
                        logger.warning(f"    ⚠️ {topic} may not be properly covered")
                    
                except Exception as e:
                    logger.error(f"    ❌ {topic} validation failed: {e}")
                    topic_results[topic_key] = {
                        "topic": topic,
                        "prompt_generated": False,
                        "error": str(e)
                    }
            
            self.results["validations"]["topic_coverage"] = topic_results
            
            # Calculate coverage success
            successful_topics = sum(
                1 for result in topic_results.values() 
                if result.get("relevant_content", False)
            )
            total_topics = len(topic_results)
            coverage_rate = successful_topics / total_topics if total_topics > 0 else 0
            
            self.results["validations"]["topic_coverage"]["summary"] = {
                "total_topics": total_topics,
                "successful_topics": successful_topics,
                "coverage_rate": coverage_rate
            }
            
            logger.info(f"✅ Topic coverage validation complete: {successful_topics}/{total_topics} passed ({coverage_rate:.1%})")
            return coverage_rate >= 0.75
            
        except Exception as e:
            logger.error(f"❌ Topic coverage validation failed: {e}")
            self.results["validations"]["topic_coverage"] = {
                "status": "ERROR",
                "error": str(e)
            }
            return False
    
    async def validate_mode_variations(self):
        """Validate prompts adapt to different modes"""
        try:
            logger.info("⚙️ Validating mode variations...")
            
            test_modes = ["focused", "balanced", "exploratory", "conservative"]
            mode_results = {}
            test_topic = "climate change solutions"
            
            for mode in test_modes:
                logger.info(f"  🔧 Testing mode: {mode}")
                
                try:
                    # Generate prompt with specific mode
                    prompt_data = self.ptg.generate_canonical_prompt(
                        agent_name="planner",  # Use planner as representative
                        session_id=f"mode_test_{mode}",
                        topic=test_topic,
                        topic_descriptor="environmental sustainability initiatives",
                        input_data={"content": f"Mode test for {mode}"},
                        mode=mode
                    )
                    
                    # Check mode influence
                    prompt_text = prompt_data.get("prompt", "").lower()
                    mode_indicators = {
                        "focused": ["specific", "targeted", "precise", "narrow"],
                        "balanced": ["balanced", "comprehensive", "moderate", "measured"],
                        "exploratory": ["explore", "creative", "innovative", "broad"],
                        "conservative": ["conservative", "careful", "safe", "proven"]
                    }
                    
                    mode_words = mode_indicators.get(mode, [])
                    mode_influence = any(word in prompt_text for word in mode_words)
                    
                    mode_results[mode] = {
                        "mode": mode,
                        "prompt_generated": bool(prompt_data),
                        "mode_indicators": mode_words,
                        "mode_influence_detected": mode_influence,
                        "instruction_length": len(prompt_text.split())
                    }
                    
                    if mode_influence:
                        logger.info(f"    ✅ {mode} mode influence detected")
                    else:
                        logger.warning(f"    ⚠️ {mode} mode influence not clearly detected")
                    
                except Exception as e:
                    logger.error(f"    ❌ {mode} mode validation failed: {e}")
                    mode_results[mode] = {
                        "mode": mode,
                        "prompt_generated": False,
                        "error": str(e)
                    }
            
            self.results["validations"]["mode_variations"] = mode_results
            
            # Calculate mode adaptation success
            successful_modes = sum(
                1 for result in mode_results.values() 
                if result.get("mode_influence_detected", False)
            )
            total_modes = len(mode_results)
            adaptation_rate = successful_modes / total_modes if total_modes > 0 else 0
            
            self.results["validations"]["mode_variations"]["summary"] = {
                "total_modes": total_modes,
                "successful_modes": successful_modes,
                "adaptation_rate": adaptation_rate
            }
            
            logger.info(f"✅ Mode variation validation complete: {successful_modes}/{total_modes} passed ({adaptation_rate:.1%})")
            return adaptation_rate >= 0.5  # Lower threshold as mode influence can be subtle
            
        except Exception as e:
            logger.error(f"❌ Mode variation validation failed: {e}")
            self.results["validations"]["mode_variations"] = {
                "status": "ERROR",
                "error": str(e)
            }
            return False
    
    async def validate_consistency_across_sessions(self):
        """Validate prompts are consistent across different sessions"""
        try:
            logger.info("🔄 Validating consistency across sessions...")
            
            test_sessions = [f"consistency_test_{i}" for i in range(3)]
            consistency_results = {}
            
            # Generate same prompt across multiple sessions
            prompts_data = []
            for session_id in test_sessions:
                try:
                    prompt_data = self.ptg.generate_canonical_prompt(
                        agent_name="perception",
                        session_id=session_id,
                        topic="smart cities infrastructure",
                        topic_descriptor="urban planning and technology integration",
                        input_data={"content": "Consistency test content"},
                        mode="balanced"
                    )
                    prompts_data.append(prompt_data)
                    
                except Exception as e:
                    logger.warning(f"Failed to generate prompt for session {session_id}: {e}")
            
            if len(prompts_data) >= 2:
                # Compare structural consistency
                first_prompt = prompts_data[0]
                structural_consistency = True
                content_similarity = 0
                
                for prompt in prompts_data[1:]:
                    # Check same keys exist
                    if set(first_prompt.keys()) != set(prompt.keys()):
                        structural_consistency = False
                    
                    # Check instruction similarity (simple word overlap)
                    first_words = set(first_prompt.get("prompt", "").lower().split())
                    prompt_words = set(prompt.get("prompt", "").lower().split())
                    
                    if first_words and prompt_words:
                        overlap = len(first_words.intersection(prompt_words))
                        total_unique = len(first_words.union(prompt_words))
                        similarity = overlap / total_unique if total_unique > 0 else 0
                        content_similarity += similarity
                
                content_similarity /= (len(prompts_data) - 1)  # Average similarity
                
                consistency_results = {
                    "sessions_tested": len(prompts_data),
                    "structural_consistency": structural_consistency,
                    "content_similarity": content_similarity,
                    "consistency_threshold_met": content_similarity >= 0.8 and structural_consistency
                }
                
                self.results["validations"]["session_consistency"] = consistency_results
                
                if consistency_results["consistency_threshold_met"]:
                    logger.info(f"✅ Session consistency validated ({content_similarity:.1%} similarity)")
                else:
                    logger.warning(f"⚠️ Session consistency issues detected ({content_similarity:.1%} similarity)")
                
                return consistency_results["consistency_threshold_met"]
                
            else:
                logger.error("❌ Insufficient prompts generated for consistency check")
                self.results["validations"]["session_consistency"] = {
                    "status": "FAILED",
                    "error": "Insufficient prompts generated"
                }
                return False
            
        except Exception as e:
            logger.error(f"❌ Session consistency validation failed: {e}")
            self.results["validations"]["session_consistency"] = {
                "status": "ERROR",
                "error": str(e)
            }
            return False
    
    async def run_full_validation(self):
        """Run complete prompt schema validation"""
        try:
            logger.info("🎯 Starting Prompt Schema Validation")
            
            # Setup environment
            setup_success = await self.setup_environment()
            if not setup_success:
                self.results["overall_status"] = "SETUP_FAILED"
                return False
            
            # Run all validations
            validations = [
                await self.validate_all_agent_prompts(),
                await self.validate_topic_coverage(),
                await self.validate_mode_variations(),
                await self.validate_consistency_across_sessions()
            ]
            
            # Calculate overall success
            passed_validations = sum(validations)
            total_validations = len(validations)
            success_rate = passed_validations / total_validations if total_validations > 0 else 0
            
            self.results["overall_status"] = "SUCCESS" if success_rate >= 0.75 else "PARTIAL_FAILURE"
            self.results["success_rate"] = success_rate
            self.results["passed_validations"] = passed_validations
            self.results["total_validations"] = total_validations
            
            logger.info(f"🎉 Prompt Schema Validation Complete: {passed_validations}/{total_validations} validations passed ({success_rate:.1%})")
            
            return success_rate >= 0.75
            
        except Exception as e:
            logger.error(f"❌ Prompt schema validation failed: {e}")
            self.results["overall_status"] = "FAILED"
            self.results["errors"].append(f"Validation error: {str(e)}")
            return False
        
        finally:
            # No cleanup needed for direct PTG instance
            pass
    
    def save_results(self):
        """Save validation results to file"""
        results_dir = Path(__file__).parent / "internal_checks"
        results_dir.mkdir(exist_ok=True)
        
        results_file = results_dir / f"prompt_schema_validation_{datetime.now().strftime('%Y%m%dT%H%M%SZ')}.json"
        
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"📝 Validation results saved to: {results_file}")
        return results_file

async def main():
    """Main validation runner"""
    validator = PromptSchemaValidator()
    
    try:
        success = await validator.run_full_validation()
        results_file = validator.save_results()
        
        if success:
            print("🎉 ✅ PROMPT SCHEMA VALIDATION: PASSED")
            print(f"📊 Results: {results_file}")
            return 0
        else:
            print("❌ PROMPT SCHEMA VALIDATION: FAILED")
            print(f"📊 Results: {results_file}")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Validation runner failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
