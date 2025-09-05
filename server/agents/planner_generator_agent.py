"""
Planner/Generator Agent - Human-AI Co-Creation System
Blueprint-compliant content planning and generation agent
Agent 3 of 6: Plans content structure and generates suggestions
"""

import asyncio
import logging
import json
import re
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
from pathlib import Path

from utils.logging_cfg import get_agent_logger

logger = get_agent_logger("planner_generator")


class PlannerGeneratorAgent:
    """
    Planner/Generator Agent - Third of the 6 blueprint agents
    Plans content structure and generates creative suggestions
    Uses dynamic prompts from PTG, no hardcoded topic logic
    """

    def __init__(self, config: Dict[str, Any], llm_provider=None):
        self.config = config
        self.llm_provider = llm_provider
        self.prompt_audit_enabled = config.get("PROMPT_AUDIT", False)
        self.audit_log_dir = config.get("audit_log_dir", "internal_checks")

    async def invoke(
        self, workspace: Dict[str, Any], agent_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Blueprint-compliant invoke method for Planner/Generator Agent
        Generates candidate branches using a prompt-driven approach.
        """
        prompt_payload = agent_config.get("prompt_payload")
        session_id = workspace.get("session_id", "unknown")
        
        # Debug logging to check LLM provider status
        logger.debug(f"Planner agent invoke - LLM provider: {self.llm_provider is not None}, Prompt payload: {prompt_payload is not None}")
        
        # Production-grade fallback handling with reduced logging
        if not prompt_payload or not self.llm_provider:
            # Only log warning once per session to reduce noise
            if not hasattr(self, '_fallback_sessions'):
                self._fallback_sessions = set()
            
            if session_id not in self._fallback_sessions:
                logger.warning(f"Planner agent using fallback mode (session: {session_id})")
                self._fallback_sessions.add(session_id)
            else:
                logger.debug(f"Planner agent continuing in fallback mode (session: {session_id})")
            
            # Generate fallback response instead of empty response
            return self._generate_fallback_response(session_id, agent_config.get("max_branches", 3))

        try:
            logger.info("Invoking Planner/Generator Agent with LLM-based generation.")
            
            # Debug: Log the prompt payload to see what PTG generated
            logger.warning(f"🔍 PTG Prompt payload keys: {list(prompt_payload.keys())}")
            if "schema" in prompt_payload:
                logger.warning(f"🔍 PTG Schema type: {type(prompt_payload['schema'])}")
                logger.warning(f"🔍 PTG Schema preview: {str(prompt_payload['schema'])[:200]}...")
            
            llm_response = await self.llm_provider.generate(
                prompt=prompt_payload["prompt"],
                temperature=prompt_payload.get("temperature", 0.7),
                max_tokens=prompt_payload.get("max_tokens", 1000),
                schema=prompt_payload.get("schema"),
                session_id=session_id,
                agent="planner"
            )

            # Debug: Log the LLM response structure
            logger.warning(f"🔍 LLM response keys: {list(llm_response.keys())}")
            logger.warning(f"🔍 LLM response preview: {str(llm_response)[:500]}...")
            
            # Check if response has expected structure
            if "branches" not in llm_response:
                logger.warning(f"❌ LLM response missing 'branches' field. Available keys: {list(llm_response.keys())}")
                if "error" in llm_response:
                    logger.error(f"❌ LLM generation error: {llm_response['error']}")
                    return self._empty_response(session_id)
                # Try to extract content and format as a single branch
                content = llm_response.get("content", llm_response.get("raw_response", ""))
                if content:
                    logger.warning("🔧 Converting non-structured response to branch format")
                    llm_response = {
                        "branches": [{
                            "branch_id": "branch-001",
                            "title": "Generated Content",
                            "content": {"title": "Generated Content", "paragraph": content},
                            "score_estimate": 0.7,
                            "meta": {"source": "llm_fallback"}
                        }]
                    }
                else:
                    logger.error("❌ No usable content in LLM response")
                    return self._empty_response(session_id)
            else:
                logger.warning(f"✅ Found {len(llm_response['branches'])} branches in LLM response")

            # Add call metadata
            llm_response["call_metadata"] = {
                "provider": getattr(self.llm_provider, 'current_provider', 'unknown'),
                "model": getattr(self.llm_provider, 'name', 'unknown'),
                "prompt_hash": hash(prompt_payload["prompt"]),
                "timestamp": datetime.utcnow().isoformat()
            }

            # Add domain metadata and normalize each branch to ProjectionSchema fields
            topic_family = agent_config.get("topic_family", "unknown")
            normalized_branches = []
            for branch in llm_response.get("branches", []):
                # Flatten content if present
                content = branch.get("content", {})
                # Map required fields
                title = content.get("title") or branch.get("title") or "Untitled"
                paragraph = content.get("paragraph") or branch.get("paragraph") or ""
                events = content.get("events") or branch.get("events") or []
                flags = content.get("flags") or branch.get("flags") or {}
                branch_type = content.get("branch_type") or branch.get("branch_type") or "balanced"
                score = content.get("score") or branch.get("score")
                # Add domain metadata
                meta = branch.get("meta", {})
                meta["domain"] = topic_family
                meta["topic_family"] = topic_family
                # Build normalized branch
                normalized = {
                    "title": title,
                    "paragraph": paragraph,
                    "events": events,
                    "flags": flags,
                    "branch_type": branch_type,
                    "score": score,
                    "meta": meta
                }
                normalized_branches.append(normalized)

            llm_response["branches"] = normalized_branches

            if self.prompt_audit_enabled:
                self._log_prompt_audit(prompt_payload, llm_response)

            return llm_response

        except Exception as e:
            logger.error(f"LLM-based planning/generation failed: {e}")
            return self._empty_response(workspace.get("session_id"))

    def _log_prompt_audit(self, prompt_payload: Dict[str, Any], response: Dict[str, Any]):
        """Logs outgoing prompts and metadata for auditing."""
        try:
            ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            log_path = Path(self.audit_log_dir)
            log_path.mkdir(exist_ok=True)
            log_file = log_path / f"llm_prompts_{ts}.ndjson"
            
            audit_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "agent": "planner_generator",
                "prompt_hash": hash(prompt_payload.get("prompt", "")),
                "metadata": prompt_payload.get("metadata", {}),
                "response_summary": {
                    "branch_count": len(response.get("branches", [])),
                    "first_branch_title": response.get("branches", [{}])[0].get("title", "N/A")
                }
            }
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(audit_record) + "\n")
        except Exception as e:
            logger.error(f"Failed to write to prompt audit log: {e}")

    def _empty_response(self, session_id: Optional[str]) -> Dict[str, Any]:
        """Returns a default empty response for error cases."""
        return {
            "session_id": session_id,
            "branches": [],
            "call_metadata": {
                "provider": "local",
                "model": "error_fallback",
                "timestamp": datetime.utcnow().isoformat(),
                "error": "Planner/Generator agent failed to produce a response."
            }
        }

    def _generate_fallback_response(self, session_id: str, max_branches: int = 3) -> Dict[str, Any]:
        """Generate a fallback response when LLM provider is unavailable."""
        from datetime import datetime
        
        # Create basic fallback branches with correct schema
        fallback_branches = []
        for i in range(min(max_branches, 2)):  # Limit to 2 fallback branches
            branch = {
                "title": f"Continue Writing (Suggestion {i+1})",
                "paragraph": f"Continue writing from here... This is a fallback suggestion {i+1} that provides a basic continuation point for your story.",
                "events": [],
                "flags": {},
                "branch_type": "balanced",
                "score": 5.0
            }
            fallback_branches.append(branch)
        
        # Format as expected by SuggestionsResponse schema
        projections = {}
        for i, branch in enumerate(fallback_branches):
            projections[f"branch_{i}"] = branch
        
        return {
            "branches": fallback_branches,  # Keep for backwards compatibility
            "projections": projections,     # New schema format
            "metadata": {
                "agent": "planner",
                "session_id": session_id,
                "generated_count": len(fallback_branches),
                "fallback_mode": True,
                "timestamp": datetime.now().isoformat(),
                "execution_time": 0.001
            },
            "success": True,
            "fallback_used": True
        }

    def _parse_llm_response(self, llm_response_text: str, session_id: str) -> Dict[str, Any]:
        """Parse LLM response text and structure it into the expected format"""
        try:
            # Try to parse as JSON first
            if llm_response_text.strip().startswith('{'):
                parsed = json.loads(llm_response_text)
                if "branches" in parsed:
                    return parsed
            
            # If not JSON, create structured response from text
            # Split by paragraphs or sentences to create multiple branches
            lines = [line.strip() for line in llm_response_text.split('\n') if line.strip()]
            
            # Create branches from content
            branches = []
            if len(lines) >= 3:
                # Create 3 branches from different parts of the response
                branch_1 = {
                    "title": "Comprehensive Article",
                    "content": llm_response_text,
                    "meta": {"confidence": 0.9, "approach": "detailed"}
                }
                branch_2 = {
                    "title": "Focused Overview", 
                    "content": " ".join(lines[:len(lines)//2]),
                    "meta": {"confidence": 0.8, "approach": "concise"}
                }
                branch_3 = {
                    "title": "Extended Analysis",
                    "content": " ".join(lines[len(lines)//2:]),
                    "meta": {"confidence": 0.75, "approach": "analytical"}
                }
                branches = [branch_1, branch_2, branch_3]
            else:
                # Single branch if content is short
                branches = [{
                    "title": "Generated Content",
                    "content": llm_response_text,
                    "meta": {"confidence": 0.85, "approach": "direct"}
                }]
            
            # Format as expected by SuggestionsResponse schema
            projections = {}
            for i, branch in enumerate(branches):
                projections[f"branch_{i}"] = branch
            
            return {
                "branches": branches,
                "projections": projections,
                "metadata": {
                    "agent": "planner",
                    "session_id": session_id,
                    "generated_count": len(branches),
                    "fallback_mode": False,
                    "timestamp": datetime.now().isoformat(),
                    "execution_time": 0.1
                },
                "success": True,
                "fallback_used": False
            }
            
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            # Return single branch with the raw response
            return {
                "branches": [{
                    "title": "LLM Generated Content",
                    "content": llm_response_text,
                    "meta": {"confidence": 0.7, "parsing_error": str(e)}
                }],
                "metadata": {
                    "agent": "planner",
                    "session_id": session_id,
                    "generated_count": 1,
                    "fallback_mode": False,
                    "timestamp": datetime.now().isoformat(),
                    "execution_time": 0.05
                },
                "success": True,
                "fallback_used": False
            }



    async def initialize(self):
        """Initialize the planner generator agent"""
        logger.info("Initializing Planner Generator Agent")
        # Initialize any required resources
        logger.info("Planner Generator Agent initialized successfully")

    async def cleanup(self):
        """Cleanup planner generator agent resources"""
        logger.info("Cleaning up Planner Generator Agent")
        # Clear any cached data
        logger.info("Planner Generator Agent cleanup completed")


# Factory function for agent creation
async def create_planner_generator_agent(
    config: Dict[str, Any], llm_provider=None
) -> PlannerGeneratorAgent:
    """Create and initialize planner generator agent"""
    agent = PlannerGeneratorAgent(config, llm_provider)
    await agent.initialize()
    return agent
