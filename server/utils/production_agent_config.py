#!/usr/bin/env python3
"""
Production Agent Configuration System
Ensures all agents have proper configuration and LLM providers in production environments.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ProductionAgentConfigurator:
    """Configures agents with production-grade settings and validates configurations."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm_provider: Optional[Any] = None
        self._default_configurations = self._setup_default_configurations()
    
    def _setup_default_configurations(self) -> Dict[str, Dict[str, Any]]:
        """Setup default configurations for all agents."""
        return {
            "planner": {
                "default_prompt": "Generate creative content suggestions based on the following context",
                "default_temperature": 0.7,
                "default_max_tokens": 150,
                "fallback_enabled": True,
                "timeout_seconds": 30
            },
            "verifier": {
                "default_prompt": "Verify the quality and consistency of the following content",
                "default_temperature": 0.3,
                "default_max_tokens": 100,
                "fallback_enabled": True,
                "timeout_seconds": 20
            },
            "perception": {
                "default_prompt": "Analyze the context and extract relevant information",
                "default_temperature": 0.5,
                "default_max_tokens": 200,
                "fallback_enabled": True,
                "timeout_seconds": 25
            },
            "graph_manager": {
                "fallback_enabled": True,
                "timeout_seconds": 15
            },
            "evaluator": {
                "default_prompt": "Evaluate and rank the provided content options",
                "default_temperature": 0.4,
                "default_max_tokens": 100,
                "fallback_enabled": True,
                "timeout_seconds": 20
            }
        }
    
    def set_llm_provider(self, llm_provider: Any) -> None:
        """Set the LLM provider for agent configuration."""
        self.llm_provider = llm_provider
        logger.info(f"LLM provider configured: {type(llm_provider).__name__}")
    
    def configure_agent_with_defaults(self, agent_name: str, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """Configure an agent with production defaults and validation."""
        default_config = self._default_configurations.get(agent_name, {})
        enhanced_config = agent_config.copy()
        
        # Ensure session_id is present
        if "session_id" not in enhanced_config:
            enhanced_config["session_id"] = "default_session"
            logger.warning(f"No session_id provided for {agent_name}, using default")
        
        # Add LLM provider if not present
        if "llm_provider" not in enhanced_config and self.llm_provider:
            enhanced_config["llm_provider"] = self.llm_provider
        
        # Add prompt payload if not present and agent requires it
        if agent_name in ["planner", "verifier", "perception", "evaluator"]:
            if "prompt_payload" not in enhanced_config or not enhanced_config["prompt_payload"]:
                enhanced_config["prompt_payload"] = self._create_default_prompt_payload(
                    agent_name, 
                    enhanced_config.get("content", ""),
                    enhanced_config.get("session_id", "unknown")
                )
                logger.info(f"Added default prompt payload for {agent_name}")
        
        # Add fallback configuration
        enhanced_config["fallback_enabled"] = default_config.get("fallback_enabled", True)
        enhanced_config["timeout_seconds"] = default_config.get("timeout_seconds", 30)
        
        # Add metadata
        enhanced_config["_configured_at"] = datetime.now().isoformat()
        enhanced_config["_agent_name"] = agent_name
        enhanced_config["_production_configured"] = True
        
        return enhanced_config
    
    def _create_default_prompt_payload(self, agent_name: str, content: str, session_id: str) -> Dict[str, Any]:
        """Create a default prompt payload for an agent."""
        defaults = self._default_configurations.get(agent_name, {})
        
        # Truncate content for prompt to avoid token limits
        truncated_content = content[:500] if content else "No content provided"
        
        prompt_template = defaults.get("default_prompt", f"Process content for {agent_name}")
        
        return {
            "prompt": f"{prompt_template}: {truncated_content}",
            "temperature": defaults.get("default_temperature", 0.5),
            "max_tokens": defaults.get("default_max_tokens", 100),
            "schema": {
                "type": "object",
                "properties": {
                    "result": {"type": "string"},
                    "success": {"type": "boolean"},
                    "metadata": {"type": "object"}
                }
            },
            "session_id": session_id,
            "_generated_default": True
        }
    
    def validate_agent_configuration(self, agent_name: str, agent_config: Dict[str, Any]) -> bool:
        """Validate that an agent configuration is production-ready."""
        validation_errors = []
        
        # Check required fields
        if "session_id" not in agent_config:
            validation_errors.append("Missing session_id")
        
        # Check LLM-dependent agents
        if agent_name in ["planner", "verifier", "perception", "evaluator"]:
            if "prompt_payload" not in agent_config:
                validation_errors.append("Missing prompt_payload for LLM-dependent agent")
            elif not isinstance(agent_config["prompt_payload"], dict):
                validation_errors.append("prompt_payload must be a dictionary")
            else:
                payload = agent_config["prompt_payload"]
                required_payload_fields = ["prompt", "temperature", "max_tokens"]
                for field in required_payload_fields:
                    if field not in payload:
                        validation_errors.append(f"Missing {field} in prompt_payload")
        
        # Log validation results
        if validation_errors:
            logger.warning(f"Agent {agent_name} configuration validation failed: {validation_errors}")
            return False
        else:
            logger.debug(f"Agent {agent_name} configuration validated successfully")
            return True
    
    def get_production_agent_config(self, agent_name: str, base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Get a production-ready agent configuration."""
        # First, configure with defaults
        enhanced_config = self.configure_agent_with_defaults(agent_name, base_config)
        
        # Validate the configuration
        if not self.validate_agent_configuration(agent_name, enhanced_config):
            logger.error(f"Failed to create valid configuration for {agent_name}")
            # Return a minimal working configuration
            return self._create_minimal_config(agent_name, base_config.get("session_id", "fallback"))
        
        return enhanced_config
    
    def _create_minimal_config(self, agent_name: str, session_id: str) -> Dict[str, Any]:
        """Create a minimal working configuration for an agent."""
        minimal_config = {
            "session_id": session_id,
            "fallback_enabled": True,
            "timeout_seconds": 30,
            "_minimal_config": True,
            "_created_at": datetime.now().isoformat()
        }
        
        # Add prompt payload for LLM-dependent agents
        if agent_name in ["planner", "verifier", "perception", "evaluator"]:
            minimal_config["prompt_payload"] = self._create_default_prompt_payload(
                agent_name, "", session_id
            )
        
        if self.llm_provider:
            minimal_config["llm_provider"] = self.llm_provider
        
        logger.info(f"Created minimal configuration for {agent_name}")
        return minimal_config


class AgentInitializationManager:
    """Manages agent initialization in production environments."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.configurator = ProductionAgentConfigurator(config)
        self.initialized_agents: Dict[str, Any] = {}
    
    async def initialize_agents(self, agents: Dict[str, Any], llm_provider: Optional[Any] = None) -> Dict[str, Any]:
        """Initialize all agents with production configurations."""
        if llm_provider:
            self.configurator.set_llm_provider(llm_provider)
        
        initialized_agents = {}
        
        for agent_name, agent_instance in agents.items():
            try:
                # Configure agent with production settings
                if hasattr(agent_instance, 'llm_provider') and llm_provider:
                    agent_instance.llm_provider = llm_provider
                    logger.info(f"Assigned LLM provider to {agent_name}")
                
                # Initialize agent if it has an initialize method
                if hasattr(agent_instance, 'initialize') and callable(getattr(agent_instance, 'initialize')):
                    await agent_instance.initialize()
                    logger.info(f"Initialized {agent_name} agent")
                
                # Store initialized agent
                initialized_agents[agent_name] = agent_instance
                
            except Exception as e:
                logger.error(f"Failed to initialize {agent_name} agent: {e}")
                # Continue with other agents rather than failing completely
                continue
        
        self.initialized_agents = initialized_agents
        logger.info(f"Successfully initialized {len(initialized_agents)} agents")
        
        return initialized_agents
    
    def get_agent_status(self) -> Dict[str, str]:
        """Get the initialization status of all agents."""
        return {
            agent_name: "initialized" 
            for agent_name in self.initialized_agents.keys()
        }


# Export main classes
__all__ = ["ProductionAgentConfigurator", "AgentInitializationManager"]
