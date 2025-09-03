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
        if not prompt_payload or not self.llm_provider:
            logger.error("Planner agent requires a prompt payload and LLM provider.")
            return self._empty_response(workspace.get("session_id"))

        try:
            logger.info("Invoking Planner/Generator Agent with LLM-based generation.")
            
            llm_response = await self.llm_provider.generate(
                prompt=prompt_payload["prompt"],
                temperature=prompt_payload["temperature"],
                max_tokens=prompt_payload["max_tokens"],
                schema=prompt_payload["schema"]
            )

            # Add call metadata
            llm_response["call_metadata"] = {
                "provider": self.llm_provider.provider_name,
                "model": self.llm_provider.model_name,
                "prompt_hash": hash(prompt_payload["prompt"]),
                "timestamp": datetime.utcnow().isoformat()
            }

            # Add domain metadata to each branch
            topic_family = agent_config.get("topic_family", "unknown")
            for branch in llm_response.get("branches", []):
                if "meta" not in branch:
                    branch["meta"] = {}
                branch["meta"]["domain"] = topic_family
                branch["meta"]["topic_family"] = topic_family

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
