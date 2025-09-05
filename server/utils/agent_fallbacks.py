#!/usr/bin/env python3
"""
Production-grade agent fallback mechanisms for handling missing configurations.
Ensures agents gracefully degrade instead of failing with errors.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AgentFallbackHandler:
    """Handles graceful degradation for agent failures and missing configurations."""
    
    @staticmethod
    def get_default_prompt_payload(agent_name: str, session_id: str, content: str = "") -> Dict[str, Any]:
        """Generate a default prompt payload when none is provided."""
        default_prompts = {
            "planner": {
                "prompt": f"Generate creative content suggestions for the following context: {content[:500]}",
                "temperature": 0.7,
                "max_tokens": 150,
                "schema": {
                    "type": "object",
                    "properties": {
                        "suggestions": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                }
            },
            "verifier": {
                "prompt": f"Verify the quality and consistency of this content: {content[:500]}",
                "temperature": 0.3,
                "max_tokens": 100,
                "schema": {
                    "type": "object",
                    "properties": {
                        "score": {"type": "number"},
                        "issues": {
                            "type": "array", 
                            "items": {"type": "string"}
                        }
                    }
                }
            }
        }
        
        payload = default_prompts.get(agent_name, {
            "prompt": f"Process this content for {agent_name}: {content[:500]}",
            "temperature": 0.5,
            "max_tokens": 100,
            "schema": {"type": "object", "properties": {}}
        })
        
        logger.info(f"Generated fallback prompt payload for {agent_name} agent")
        return payload
    
    @staticmethod
    def create_fallback_response(agent_name: str, session_id: str, reason: str = "Configuration missing") -> Dict[str, Any]:
        """Create a fallback response when an agent cannot process normally."""
        fallback_responses = {
            "planner": {
                "branches": [],
                "metadata": {
                    "generated_count": 0,
                    "fallback_reason": reason,
                    "agent": "planner",
                    "timestamp": datetime.now().isoformat()
                },
                "execution_time": 0.0,
                "success": False
            },
            "verifier": {
                "verification_result": {
                    "overall_score": 0.5,
                    "passed": True,
                    "issues": [],
                    "suggestions": [],
                    "fallback_reason": reason
                },
                "metadata": {
                    "agent": "verifier",
                    "timestamp": datetime.now().isoformat(),
                    "fallback_used": True
                },
                "execution_time": 0.0,
                "success": False
            }
        }
        
        response = fallback_responses.get(agent_name, {
            "result": "fallback",
            "reason": reason,
            "agent": agent_name,
            "timestamp": datetime.now().isoformat(),
            "success": False
        })
        
        logger.warning(f"Using fallback response for {agent_name} agent: {reason}")
        return response
    
    @staticmethod
    def is_valid_agent_config(agent_config: Dict[str, Any]) -> bool:
        """Check if agent configuration is valid for production use."""
        required_fields = ["session_id"]
        optional_fields = ["prompt_payload", "mode", "constraints"]
        
        # Check required fields
        for field in required_fields:
            if field not in agent_config or not agent_config[field]:
                logger.warning(f"Missing required agent config field: {field}")
                return False
        
        # Check if prompt_payload is properly structured when present
        if "prompt_payload" in agent_config and agent_config["prompt_payload"]:
            payload = agent_config["prompt_payload"]
            if not isinstance(payload, dict):
                logger.warning("prompt_payload must be a dictionary")
                return False
            
            required_payload_fields = ["prompt", "temperature", "max_tokens"]
            for field in required_payload_fields:
                if field not in payload:
                    logger.warning(f"Missing prompt_payload field: {field}")
                    return False
        
        return True
    
    @staticmethod
    def enhance_agent_config(agent_config: Dict[str, Any], agent_name: str, content: str = "") -> Dict[str, Any]:
        """Enhance agent configuration with fallback values."""
        enhanced_config = agent_config.copy()
        
        # Add default prompt_payload if missing
        if not enhanced_config.get("prompt_payload"):
            session_id = enhanced_config.get("session_id", "unknown")
            enhanced_config["prompt_payload"] = AgentFallbackHandler.get_default_prompt_payload(
                agent_name, session_id, content
            )
        
        # Add default values for optional fields
        if "mode" not in enhanced_config:
            enhanced_config["mode"] = "balanced"
        
        if "constraints" not in enhanced_config:
            enhanced_config["constraints"] = {}
        
        # Add metadata
        enhanced_config["_enhanced"] = True
        enhanced_config["_enhanced_timestamp"] = datetime.now().isoformat()
        
        return enhanced_config


class ProductionAgentValidator:
    """Validates agent inputs and outputs for production environments."""
    
    @staticmethod
    def validate_workspace_data(workspace_data: Any) -> Dict[str, Any]:
        """Validate and normalize workspace data."""
        if workspace_data is None:
            logger.warning("Workspace data is None, using empty dict")
            return {}
        
        if isinstance(workspace_data, dict):
            return workspace_data
        
        # Try to convert to dict if it has methods
        if hasattr(workspace_data, 'to_dict'):
            try:
                return workspace_data.to_dict()
            except Exception as e:
                logger.warning(f"Failed to convert workspace to dict via to_dict(): {e}")
        
        if hasattr(workspace_data, 'model_dump'):
            try:
                return workspace_data.model_dump()
            except Exception as e:
                logger.warning(f"Failed to convert workspace to dict via model_dump(): {e}")
        
        if hasattr(workspace_data, '__dict__'):
            try:
                return workspace_data.__dict__
            except Exception as e:
                logger.warning(f"Failed to convert workspace to dict via __dict__: {e}")
        
        logger.warning(f"Could not convert workspace data of type {type(workspace_data)}, using empty dict")
        return {}
    
    @staticmethod
    def sanitize_agent_response(response: Any, agent_name: str) -> Dict[str, Any]:
        """Sanitize and validate agent responses for production."""
        if response is None:
            logger.warning(f"Agent {agent_name} returned None response")
            return AgentFallbackHandler.create_fallback_response(agent_name, "unknown", "Null response")
        
        if isinstance(response, dict):
            # Ensure required fields exist
            sanitized = response.copy()
            if "success" not in sanitized:
                sanitized["success"] = True
            if "timestamp" not in sanitized:
                sanitized["timestamp"] = datetime.now().isoformat()
            if "agent" not in sanitized:
                sanitized["agent"] = agent_name
            return sanitized
        
        # Convert non-dict responses
        logger.warning(f"Agent {agent_name} returned non-dict response: {type(response)}")
        return {
            "result": str(response) if response is not None else "None",
            "agent": agent_name,
            "timestamp": datetime.now().isoformat(),
            "success": True,
            "raw_response": True
        }


# Export main classes
__all__ = ["AgentFallbackHandler", "ProductionAgentValidator"]
