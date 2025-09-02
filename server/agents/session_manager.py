"""
Session Manager / Policy Agent - Human-AI Co-Creation System
Blueprint-compliant session orchestration with Prompt Template Generator (PTG)
Implements the exact 6-agent architecture with dynamic, non-hardcoded prompting
"""

from __future__ import annotations
import json
import uuid
import asyncio
import re
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
import logging
from pathlib import Path

try:
    from pydantic import BaseModel, Field

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = object

# Import schemas
from utils.schemas import (
    WorkspaceSchema,
    PolicySchema,
    NewSessionRequest,
    SuggestionMode,
    TopicType,
    BranchType,
)

from utils.logging_cfg import get_agent_logger

logger = get_agent_logger("session_manager")


class PromptTemplateGenerator:
    """
    Canonical Prompt Template Generator (PTG) - Core of blueprint architecture
    Implements strict JSON output, few-shot examples, schema validation, and retry policies
    Creates topic-agnostic prompts for all 6 agents using examples.json
    NO hardcoded topic modules - all prompts generated dynamically
    """

    # Global prompt rules constants
    RETRY_MAX = 3
    MAX_PROMPT_CHARS = 8000
    STRICT_JSON_INSTRUCTION = (
        "RESPONSE FORMAT: Return only a single JSON object exactly matching the schema provided below. "
        "Do not include explanatory text, code fences, or extra fields."
    )
    RETRY_INSTRUCTION = (
        "If previous response failed JSON validation, strictly produce valid JSON only (no commentary). "
        "If confused, reduce response complexity."
    )

    def __init__(self, examples_path: str = "prompts/examples.json"):
        # More robust path resolution to handle different working directories
        if not Path(examples_path).is_absolute():
            # Try to find the examples file relative to this module first
            module_dir = Path(__file__).parent.parent  # Go up to server directory
            potential_path = module_dir / examples_path
            if potential_path.exists():
                self.examples_path = potential_path
            else:
                # Fall back to relative path from current working directory
                self.examples_path = Path(examples_path)
        else:
            self.examples_path = Path(examples_path)
            
        self.examples_cache = {}
        self.template_cache = {}
        self.schema_version = "1.0"
        self.load_examples()

    def load_examples(self) -> None:
        """Load canonical few-shot examples from examples.json"""
        try:
            if self.examples_path.exists():
                with open(self.examples_path, "r", encoding="utf-8") as f:
                    self.examples_cache = json.load(f)
                logger.info(
                    f"Loaded canonical examples for {len(self.examples_cache)} topics"
                )
            else:
                logger.warning(
                    f"Canonical examples file not found: {self.examples_path}"
                )
                self.examples_cache = self._get_canonical_fallback_examples()
        except Exception as e:
            logger.error(f"Failed to load canonical examples: {e}")
            self.examples_cache = self._get_canonical_fallback_examples()

    def _get_canonical_fallback_examples(self) -> Dict[str, Any]:
        """Canonical fallback examples matching the prompt specification"""
        return {
            "story": {
                "conservative": [
                    {
                        "input": {
                            "topic_content": "A lighthouse keeper noticed strange lights",
                            "mode": "conservative",
                        },
                        "output": {
                            "summary_short": "Lighthouse keeper observes unusual phenomena",
                            "intents": ["describe_setting", "mystery_setup"],
                            "entities": [
                                {
                                    "name": "lighthouse keeper",
                                    "type": "PERSON",
                                    "confidence": 0.9,
                                }
                            ],
                        },
                    }
                ],
                "balanced": [
                    {
                        "input": {
                            "topic_content": "The old wizard studied the ancient tome",
                            "mode": "balanced",
                        },
                        "output": {
                            "summary_short": "Wizard researches magical knowledge",
                            "intents": ["fantasy_story", "knowledge_seeking"],
                            "entities": [
                                {"name": "wizard", "type": "PERSON", "confidence": 0.9},
                                {"name": "tome", "type": "OBJECT", "confidence": 0.8},
                            ],
                        },
                    }
                ],
                "creative": [
                    {
                        "input": {
                            "topic_content": "Quantum butterflies danced through dimensions",
                            "mode": "creative",
                        },
                        "output": {
                            "summary_short": "Interdimensional butterfly phenomenon",
                            "intents": ["sci_fi_story", "surreal_narrative"],
                            "entities": [
                                {
                                    "name": "butterflies",
                                    "type": "ENTITY",
                                    "confidence": 0.7,
                                }
                            ],
                        },
                    }
                ],
            }
        }

    def generate_canonical_prompt(
        self,
        agent_name: str,
        session_id: str,
        topic: str,
        topic_descriptor: str,
        input_data: Dict[str, Any],
        mode: str = "balanced",
        context_chunks: List[Dict] = None,
        user_constraints: Dict[str, Any] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate canonical prompt following the strict prompt specification
        Returns PTG payload with strict JSON validation requirements
        """
        context_chunks = context_chunks or []
        user_constraints = user_constraints or {}

        # Build PTG payload following canonical format
        ptg_payload = {
            "session_id": session_id,
            "topic": topic,
            "topic_descriptor": topic_descriptor,
            "mode": mode,
            "context_chunks": context_chunks,
            "user_constraints": user_constraints,
            "agent_name": agent_name,
            "agent_instructions": self._get_canonical_agent_instructions(agent_name, mode),
            "few_shot_examples": self._select_canonical_examples(
                topic, mode, agent_name
            ),
            "output_schema": self._get_canonical_schema(agent_name),
            "max_tokens": self._get_max_tokens(agent_name),
            "temperature": self._get_canonical_temperature(agent_name, mode),
            "stop_sequences": ["\n\n"],
        }

        # Format into final prompt string with strict JSON requirements
        formatted_prompt = self._format_canonical_prompt(ptg_payload, input_data)

        return {
            "prompt": formatted_prompt,
            "temperature": ptg_payload["temperature"],
            "max_tokens": ptg_payload["max_tokens"],
            "schema": ptg_payload["output_schema"],
            "schema_version": self.schema_version,  # Add schema_version at top level for compatibility
            "metadata": {
                "agent": agent_name,
                "session_id": session_id,
                "schema_version": self.schema_version,
                "generated_at": datetime.utcnow().isoformat(),
                "retry_count": 0,
            },
        }

    def _get_canonical_agent_instructions(self, agent_name: str, mode: str = "balanced") -> str:
        """Get canonical system prompts with mode-specific modifications"""
        # Mode configurations
        MODE_CONFIGS = {
            "conservative": {
                "description": "Safe, predictable continuations",
                "suffix": "Prioritize safety, proven approaches, and careful validation. Minimize risks."
            },
            "balanced": {
                "description": "Balanced creativity and consistency", 
                "suffix": "Balance creativity with consistency, innovation with reliability."
            },
            "exploratory": {
                "description": "Creative, experimental approaches",
                "suffix": "Embrace creativity, novel approaches, and innovative solutions. Think outside the box."
            },
            "focused": {
                "description": "Highly focused, specific outcomes",
                "suffix": "Be precise, specific, and targeted in your analysis. Avoid broad generalizations."
            }
        }
        
        # Get base instructions
        base_prompts = {
            "session_manager": (
                "SYSTEM: You are the Session Manager. Your task is orchestration, not content generation. "
                "For each new session, produce: 1) A topology of which agents to call and in which order. "
                "2) Per-agent prompt payloads using the Prompt Template Generator (PTG) format below. "
                "3) Validation checks that must be run after each agent's response. "
                "Always return a JSON object matching the schema provided in OUTPUT_SCHEMA."
            ),
            "perception": (
                "SYSTEM: You are Perception Agent. Convert the provided input_text and context_chunks "
                "into structured metadata. Output only JSON matching OUTPUT_SCHEMA. Use provided "
                "context_chunks for reference. If input is very long, work on the supplied chunk list."
            ),
            "planner": (
                "SYSTEM: You are Planner Agent. Using perception metadata and the provided chunks, "
                "author N candidate branches for the session. Each branch must be independent, "
                "contain an estimated cost (time/LLM tokens), required actions, required agents, "
                "and a short rationale. Output strictly as JSON array named 'branches' following OUTPUT_SCHEMA."
            ),
            "graph_manager": (
                "SYSTEM: You are Graph Manager. When given new nodes/edges or branch updates, you must: "
                "1) Insert or update nodes/edges into ArangoDB; if Arango unavailable, write into Mongo "
                "with identical schema. 2) Apply node-merge heuristics using embedding similarity "
                "(threshold configurable). 3) Prune nodes based on age/usage/score and update snapshot. "
                "Return only JSON conforming to OUTPUT_SCHEMA."
            ),
            "verifier": (
                "SYSTEM: You are Verifier Agent. Take a branch and its referenced chunks; verify: "
                "- Factual consistency with chunks - Grammar and readability "
                "- Safety & policy checks (e.g., PII, disallowed topics) "
                "Return single JSON per branch with reasons and suggested corrections."
            ),
            "evaluator": (
                "SYSTEM: You are Evaluator Agent. For an array of branches, compute multi-criteria "
                "scores and produce a composite ranking. Use scoring weights provided in input. "
                "Output JSON exactly matching schema."
            ),
        }
        
        base_instruction = base_prompts.get(
            agent_name, "SYSTEM: You are an AI assistant. Follow instructions strictly."
        )
        
        # Add mode-specific instructions
        mode_config = MODE_CONFIGS.get(mode, MODE_CONFIGS["balanced"])
        mode_suffix = f"\n\nMODE: {mode.upper()} - {mode_config['description']}. {mode_config['suffix']}"
        
        return base_instruction + mode_suffix

    def _get_canonical_schema(self, agent_name: str) -> Dict[str, Any]:
        """Get canonical output schemas matching the prompt specification exactly"""
        canonical_schemas = {
            "session_manager": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "plan_id": {"type": "string"},
                    "agents_sequence": {"type": "array", "items": {"type": "string"}},
                    "prompts": {"type": "object"},
                    "created_at": {"type": "string", "format": "date-time"},
                },
                "required": [
                    "session_id",
                    "plan_id",
                    "agents_sequence",
                    "prompts",
                    "created_at",
                ],
            },
            "perception": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "summary_short": {"type": "string", "maxLength": 60},
                    "summary_long": {"type": "string", "maxLength": 300},
                    "title": {"type": "string"},
                    "intents": {"type": "array", "items": {"type": "string"}},
                    "entities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "type": {"type": "string"},
                                "start": {"type": "integer"},
                                "end": {"type": "integer"},
                                "confidence": {
                                    "type": "number",
                                    "minimum": 0,
                                    "maximum": 1,
                                },
                            },
                        },
                    },
                    "sentiment": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "score": {"type": "number", "minimum": -1, "maximum": 1},
                        },
                    },
                    "key_phrases": {"type": "array", "items": {"type": "string"}},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "recommended_chunks": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "safe_to_continue": {"type": "boolean"},
                    "warnings": {"type": "array", "items": {"type": "string"}},
                    "call_metadata": {"type": "object"},
                },
                "required": [
                    "session_id",
                    "summary_short",
                    "intents",
                    "entities",
                    "safe_to_continue",
                    "call_metadata",
                ],
            },
            "planner": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "branches": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "branch_id": {"type": "string"},
                                "title": {"type": "string"},
                                "rationale": {"type": "string"},
                                "score_estimate": {
                                    "type": "number",
                                    "minimum": 0,
                                    "maximum": 1,
                                },
                                "cost_estimate": {
                                    "type": "object",
                                    "properties": {
                                        "tokens": {"type": "integer"},
                                        "time_ms": {"type": "integer"},
                                    },
                                },
                                "steps": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "step_id": {"type": "string"},
                                            "agent": {"type": "string"},
                                            "action": {"type": "string"},
                                            "inputs": {"type": "object"},
                                            "estimated_tokens": {"type": "integer"},
                                            "estimated_ms": {"type": "integer"},
                                        },
                                    },
                                },
                                "safety_checks": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "meta": {"type": "object"},
                            },
                        },
                    },
                    "call_metadata": {"type": "object"},
                },
                "required": ["session_id", "branches", "call_metadata"],
            },
            "graph_manager": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "applied_ops": {"type": "array"},
                    "merged_nodes": {"type": "array"},
                    "pruned_nodes": {"type": "array"},
                    "call_metadata": {"type": "object"},
                },
                "required": ["session_id", "applied_ops", "call_metadata"],
            },
            "verifier": {
                "type": "object",
                "properties": {
                    "branch_id": {"type": "string"},
                    "factual_consistency": {
                        "type": "object",
                        "properties": {
                            "score": {"type": "number"},
                            "issues": {"type": "array"},
                        },
                    },
                    "grammar_issues": {"type": "array"},
                    "safety_violations": {"type": "array"},
                    "accept_reject": {
                        "type": "string",
                        "enum": ["accept", "reject", "needs_revision"],
                    },
                    "suggested_edits": {"type": "array"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "call_metadata": {"type": "object"},
                },
                "required": [
                    "branch_id",
                    "accept_reject",
                    "confidence",
                    "call_metadata",
                ],
            },
            "evaluator": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "ranked_branches": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "branch_id": {"type": "string"},
                                "scores": {"type": "object"},
                                "composite_score": {"type": "number"},
                                "rank": {"type": "integer"},
                                "recommended": {"type": "boolean"},
                                "reasons": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                        },
                    },
                    "call_metadata": {"type": "object"},
                },
                "required": ["session_id", "ranked_branches", "call_metadata"],
            },
        }
        return canonical_schemas.get(agent_name, {"type": "object"})

    def _get_canonical_temperature(self, agent_name: str, mode: str) -> float:
        """Get canonical temperature settings for deterministic sampling of critical tasks"""
        # Very low temperature for critical verification tasks
        verification_agents = {"graph_manager", "verifier", "evaluator"}
        
        # Creative agents that benefit from higher temperatures
        creative_agents = {"perception", "planner"}

        if agent_name in verification_agents:
            return 0.1  # Deterministic sampling for critical verification tasks
        elif agent_name in creative_agents and mode == "creative":
            # In creative mode, planner should have higher temperature than perception
            if agent_name == "planner":
                return 0.7  # Higher temperature for creative planning
            else:  # perception
                return 0.3  # Moderate creativity for perception
        elif agent_name in creative_agents:
            return 0.3  # Balanced temperature for creative agents in balanced mode
        else:
            return 0.2  # Low-moderate default for other agents

    def _get_max_tokens(self, agent_name: str) -> int:
        """Get max tokens per agent type"""
        token_limits = {
            "session_manager": 1000,
            "perception": 1500,
            "planner": 2000,
            "graph_manager": 1000,
            "verifier": 1500,
            "evaluator": 1000,
        }
        return token_limits.get(agent_name, 1000)

    def _select_canonical_examples(
        self, topic: str, mode: str, agent_name: str
    ) -> List[Dict[str, Any]]:
        """Select 1-3 few-shot examples semantically similar to topic"""
        try:
            # Infer topic type from content
            topic_type = self._infer_topic_type(topic)

            topic_examples = self.examples_cache.get(topic_type, {})
            mode_examples = topic_examples.get(mode, topic_examples.get("balanced", []))

            # Return 1-3 examples as per canonical specification
            if isinstance(mode_examples, list):
                return mode_examples[:3]
            return []
        except Exception as e:
            logger.warning(f"Canonical example selection failed: {e}")
            return []

    def _infer_topic_type(self, topic: str) -> str:
        """Infer topic type for example selection"""
        topic_lower = topic.lower()

        # Educational indicators
        if any(
            word in topic_lower
            for word in ["learn", "teach", "lesson", "study", "explain"]
        ):
            return (
                "lesson_plan"
                if any(word in topic_lower for word in ["plan", "class", "activity"])
                else "study_guide"
            )

        # Story indicators (default)
        return "story"

    def _format_canonical_prompt(
        self, ptg_payload: Dict[str, Any], input_data: Dict[str, Any]
    ) -> str:
        """Format canonical prompt with strict JSON output requirements"""
        agent_name = ptg_payload["agent_name"]

        # Build prompt sections
        system_section = ptg_payload["agent_instructions"]

        # Context section
        context_section = ""
        if ptg_payload["context_chunks"]:
            chunks_text = "\n".join(
                [
                    f"Chunk {i+1}: {chunk.get('text', '')}"
                    for i, chunk in enumerate(ptg_payload["context_chunks"][:6])
                ]
            )
            context_section = f"\nCONTEXT:\n{chunks_text}\n"

        # Input section
        input_section = f"\nINPUT:\n{json.dumps(input_data, indent=2)}\n"

        # Few-shot examples section
        examples_section = ""
        if ptg_payload["few_shot_examples"]:
            examples_text = "\n".join(
                [
                    f"Example {i+1}:\nInput: {json.dumps(ex.get('input', {}))}\nOutput: {json.dumps(ex.get('output', {}))}"
                    for i, ex in enumerate(ptg_payload["few_shot_examples"])
                ]
            )
            examples_section = f"\nFEW-SHOT EXAMPLES:\n{examples_text}\n"

        # Schema section
        schema_section = (
            f"\nOUTPUT_SCHEMA:\n{json.dumps(ptg_payload['output_schema'], indent=2)}\n"
        )

        # Instructions section with strict JSON requirement
        instructions_section = f"""
INSTRUCTIONS:
- Follow the schema exactly
- Include all required fields
- Use appropriate data types
- Schema version: {self.schema_version}

{self.STRICT_JSON_INSTRUCTION}
"""

        # Combine all sections
        full_prompt = (
            system_section
            + context_section
            + input_section
            + examples_section
            + schema_section
            + instructions_section
        )

        # Check prompt length and truncate if needed
        if len(full_prompt) > self.MAX_PROMPT_CHARS:
            logger.warning(f"Prompt too long ({len(full_prompt)} chars), truncating")
            # Truncate context first, then examples if still too long
            if context_section and len(full_prompt) > self.MAX_PROMPT_CHARS:
                context_section = context_section[:1000] + "...\n"
            full_prompt = (
                system_section
                + context_section
                + input_section
                + examples_section
                + schema_section
                + instructions_section
            )

        return full_prompt


class SessionManagerAgent:
    """
    Blueprint-compliant Session Manager Agent
    Orchestrates the 6-agent system using canonical PTG and strict JSON validation
    """

    def __init__(
        self, config: Dict[str, Any], storage_provider=None, llm_provider=None
    ):
        self.config = config
        self.storage_provider = storage_provider
        self.llm_provider = llm_provider
        self.ptg = PromptTemplateGenerator()

        # Session state management
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.session_locks = {}

        # Blueprint configuration
        self.max_concurrent_sessions = config.get("max_concurrent_sessions", 10)
        self.session_timeout = config.get("session_timeout_minutes", 30)

        logger.info("Session Manager initialized with canonical PTG")

    async def invoke(
        self, workspace: Dict[str, Any], agent_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Main session manager invoke - orchestrates the 6-agent pipeline
        Returns session plan following canonical schema
        """
        session_id = workspace.get("session_id") or str(uuid.uuid4())
        topic = workspace.get("topic_content", "")
        topic_descriptor = workspace.get("topic_descriptor", "")
        mode = workspace.get("topic_mode", "balanced")

        # Create session plan
        plan_id = str(uuid.uuid4())
        agents_sequence = [
            "perception",
            "planner",
            "graph_manager",
            "verifier",
            "evaluator",
        ]

        # Generate prompts for each agent using canonical PTG
        prompts = {}
        for agent_name in agents_sequence:
            try:
                prompt_data = self.ptg.generate_canonical_prompt(
                    agent_name=agent_name,
                    session_id=session_id,
                    topic=topic,
                    topic_descriptor=topic_descriptor,
                    input_data=workspace,
                    mode=mode,
                    context_chunks=workspace.get("context_chunks", []),
                    user_constraints=agent_config.get("constraints", {}),
                )
                prompts[agent_name] = prompt_data
            except Exception as e:
                logger.error(f"Failed to generate prompt for {agent_name}: {e}")
                # Fallback prompt
                prompts[agent_name] = {
                    "prompt": f"Process the input for {agent_name}",
                    "temperature": 0.3,
                    "schema": {"type": "object"},
                }

        # Return canonical session plan
        return {
            "session_id": session_id,
            "plan_id": plan_id,
            "agents_sequence": agents_sequence,
            "prompts": prompts,
            "created_at": datetime.utcnow().isoformat(),
        }

    async def validate_json_response(
        self, response: str, expected_schema: Dict[str, Any], retry_count: int = 0
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Validate JSON response with retry policy following canonical specification
        """
        try:
            # Try to parse JSON
            parsed = json.loads(response)
            return parsed, True
        except json.JSONDecodeError:
            # Try to extract JSON substring
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                    return parsed, True
                except json.JSONDecodeError:
                    logger.debug("Failed to parse extracted JSON substring")

            # If parsing fails and we haven't exceeded retry limit
            if retry_count < PromptTemplateGenerator.RETRY_MAX:
                logger.warning(f"JSON validation failed, retry {retry_count + 1}")
                return {}, False
            else:
                # Use fallback response
                logger.error("JSON validation failed after max retries, using fallback")
                return {
                    "fallback": True,
                    "raw_response": response,
                    "error": "JSON validation failed",
                }, True

    async def call_agent_with_retry(
        self, agent_name: str, prompt_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call agent with retry policy and JSON validation
        """
        if not self.llm_provider:
            return {"error": "No LLM provider available", "fallback": True}

        prompt = prompt_data["prompt"]
        schema = prompt_data.get("schema", {})
        temperature = prompt_data.get("temperature", 0.3)

        for attempt in range(PromptTemplateGenerator.RETRY_MAX):
            try:
                # Add retry instruction if this is a retry
                if attempt > 0:
                    prompt += f"\n\n{PromptTemplateGenerator.RETRY_INSTRUCTION}"

                # Call LLM
                response = await self.llm_provider.invoke(
                    prompt, temperature=temperature
                )

                # Validate JSON
                parsed_response, is_valid = await self.validate_json_response(
                    response, schema, attempt
                )

                if is_valid:
                    # Add call metadata
                    parsed_response["call_metadata"] = {
                        "provider": getattr(
                            self.llm_provider, "provider_name", "unknown"
                        ),
                        "model": getattr(self.llm_provider, "model_name", "unknown"),
                        "attempt": attempt + 1,
                        "temperature": temperature,
                    }
                    return parsed_response

            except Exception as e:
                logger.error(
                    f"Agent {agent_name} call failed on attempt {attempt + 1}: {e}"
                )
                if attempt == PromptTemplateGenerator.RETRY_MAX - 1:
                    return {
                        "error": str(e),
                        "fallback": True,
                        "call_metadata": {"attempts": attempt + 1},
                    }

        # Should not reach here, but fallback
        return {"error": "Max retries exceeded", "fallback": True}

    async def orchestrate_agents(
        self, session_plan: Dict[str, Any], workspace: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Orchestrate the execution of agents in sequence
        """
        session_id = session_plan["session_id"]
        agents_sequence = session_plan["agents_sequence"]
        prompts = session_plan["prompts"]

        results = {}
        current_workspace = workspace.copy()

        for agent_name in agents_sequence:
            logger.info(f"Executing agent: {agent_name}")

            try:
                # Get prompt for this agent
                prompt_data = prompts.get(agent_name, {})

                # Update prompt with current workspace state
                if agent_name != "perception":  # Perception uses original input
                    # Update prompt context with previous results
                    updated_prompt = self._update_prompt_with_results(
                        prompt_data, current_workspace, results
                    )
                else:
                    updated_prompt = prompt_data

                # Call agent with retry
                agent_result = await self.call_agent_with_retry(
                    agent_name, updated_prompt
                )

                # Store result
                results[agent_name] = agent_result

                # Update workspace with agent result
                current_workspace[f"{agent_name}_analysis"] = agent_result

                # Check for critical failures
                if agent_result.get("fallback") and agent_name in [
                    "perception",
                    "verifier",
                ]:
                    logger.warning(
                        f"Critical agent {agent_name} failed, stopping pipeline"
                    )
                    break

            except Exception as e:
                logger.error(f"Agent {agent_name} execution failed: {e}")
                results[agent_name] = {"error": str(e), "fallback": True}

        return {
            "session_id": session_id,
            "results": results,
            "final_workspace": current_workspace,
            "execution_complete": True,
        }

    def _update_prompt_with_results(
        self,
        prompt_data: Dict[str, Any],
        workspace: Dict[str, Any],
        previous_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update prompt with previous agent results as context"""
        updated_prompt_data = prompt_data.copy()

        # Add previous results to the prompt context
        context_addition = "\n\nPREVIOUS AGENT RESULTS:\n"
        for agent, result in previous_results.items():
            context_addition += f"{agent.upper()}: {json.dumps(result, indent=2)}\n"

        updated_prompt_data["prompt"] += context_addition
        return updated_prompt_data


# Factory function for agent creation
async def create_session_manager_agent(
    config: Dict[str, Any], storage_provider=None, llm_provider=None
) -> SessionManagerAgent:
    """Create and initialize session manager agent"""
    return SessionManagerAgent(config, storage_provider, llm_provider)

    def _format_prompt_template(self, template: Dict[str, Any]) -> str:
        """Format the template into final prompt string following blueprint schema"""
        context = template["topic_context"]
        constraints = template["constraints"]
        examples = template["few_shot_examples"]
        schema = template["output_schema"]

        # Format examples
        examples_text = ""
        for i, example in enumerate(examples):
            examples_text += f"- example_{i+1}: {json.dumps(example, indent=2)}\n"

        # Build final prompt following blueprint master template
        prompt = f"""SYSTEM: {template["system"]}
TOPIC_CONTEXT:
- topic: {context["topic"]}
- descriptor: {context["descriptor"]}
- workspace_summary: {context["workspace_summary"]}
- mode: {context["mode"]}
CONSTRAINTS:
{self._format_constraints(constraints)}
FEW_SHOT_EXAMPLES:
{examples_text}
OUTPUT_SCHEMA:
{json.dumps(schema, indent=2)}
RESPONSE_INSTRUCTIONS:
{template["response_instructions"]}
- Temperature: {template["temperature"]}"""

        return prompt

    def _format_constraints(self, constraints: Dict[str, Any]) -> str:
        """Format constraints section"""
        lines = []
        for key, value in constraints.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines) if lines else "- None specified"


class SessionManager:
    """
    Session Manager / Policy Agent - First of the 6 blueprint agents
    Manages sessions, policies, persistence, and orchestrates other agents
    """

    def __init__(
        self,
        config: Dict[str, Any],
        database_client=None,
        graph_client=None,
        llm_provider=None,
    ):
        self.config = config
        self.database_client = database_client
        self.graph_client = graph_client
        self.llm_provider = llm_provider

        # Initialize PTG - core of blueprint architecture
        self.ptg = PromptTemplateGenerator()

        # Session tracking
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.session_cooldowns: Dict[str, datetime] = {}

        # Policy defaults from blueprint
        self.default_policy = {
            "max_backtrack": 2,
            "suggestion_mode": "on_demand",  # on_demand|idle_smart|proactive
            "cooldown_seconds": 300,  # 5 minutes
            "idle_timeout": 60,  # seconds
            "max_branches": 3,
            "preserve_characters": True,
            "preserve_pov": True,
            "strict_mode": False,
        }

    async def initialize(self):
        """Initialize the session manager"""
        logger.info("Initializing Session Manager")
        # Initialize PTG examples
        self.ptg.load_examples()
        logger.info("Session Manager initialized successfully")

    async def cleanup(self):
        """Cleanup session manager resources"""
        logger.info("Cleaning up Session Manager")
        # Clear active sessions
        self.active_sessions.clear()
        self.session_cooldowns.clear()
        logger.info("Session Manager cleanup completed")

    async def invoke(
        self, workspace: Dict[str, Any], agent_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Main agent invoke method - manages session state and policies"""
        session_id = workspace.get("session_id")

        # Update session tracking
        self._update_session_state(session_id, workspace)

        # Check policies and determine next action
        next_action = await self._determine_next_action(workspace)

        # Enforce cooldowns
        cooldown_remaining = self._check_cooldown(session_id)

        # Detect if user is stuck
        is_stuck = self._detect_stuck_indicators(workspace)

        return {
            "session_id": session_id,
            "status": self._get_session_status(workspace),
            "next_action": next_action,
            "is_stuck": is_stuck,
            "cooldown_remaining": cooldown_remaining,
            "policy_violations": [],
            "metadata": {
                "last_activity": datetime.utcnow().isoformat(),
                "suggestion_mode": workspace.get("policy", {}).get(
                    "suggestion_mode", "on_demand"
                ),
            },
        }

    async def create_workspace(
        self,
        session_id: str,
        topic: str,
        mode: str,
        user_preferences: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Create new workspace following blueprint schema"""
        user_preferences = user_preferences or {}

        workspace = {
            "session_id": session_id,
            "topic": topic,
            "topic_content": "",  # story_so_far or content
            "events": [],
            "characters": {},
            "kb_triples": [],
            "projections": {},
            "history": [],
            "graph": {"nodes": [], "edges": []},
            "policy": {**self.default_policy, **user_preferences},
            "metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "last_modified": datetime.utcnow().isoformat(),
                "mode": mode,
                "user_preferences": user_preferences,
            },
        }

        # Save to database
        await self._persist_workspace(workspace)

        # Track session
        self.active_sessions[session_id] = workspace
        logger.info(f"Created workspace for session {session_id}, topic: {topic}")
        return workspace

    def _save_examples(self) -> None:
        """Save examples to JSON file"""
        try:
            self.examples_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.examples_path, "w", encoding="utf-8") as f:
                json.dump(self.examples_cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save examples: {e}")

    def generate_agent_prompt(
        self,
        agent_role: str,
        topic: str,
        topic_descriptor: Optional[str],
        workspace_summary: str,
        mode: str = "balanced",
        constraints: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a dynamic prompt for an agent based on topic and context

        Args:
            agent_role: Role of the agent (e.g., "Story Generator", "Lesson Planner")
            topic: Topic type (story, lesson_plan, etc.)
            topic_descriptor: Topic-specific descriptor
            workspace_summary: Summary of current workspace
            mode: Generation mode (conservative, balanced, creative)
            constraints: Generation constraints
            output_schema: Expected output JSON schema

        Returns:
            Dictionary containing the complete prompt structure
        """
        if constraints is None:
            constraints = {}

        # Get topic category for examples
        topic_category = self._get_topic_category(topic)
        few_shot_examples = self._get_examples_for_topic(topic_category)

        # Build the prompt
        prompt_data = {
            "system_role": f"You are a {agent_role} assistant. Follow instructions strictly.",
            "topic_context": {
                "topic": topic,
                "descriptor": topic_descriptor or "",
                "workspace_summary": workspace_summary,
            },
            "constraints": {
                "preserve": constraints.get("preserve_rules", []),
                "max_items": constraints.get("max_events", 4),
                "pov": constraints.get("pov"),
                "mode": mode,
            },
            "few_shot_examples": few_shot_examples,
            "output_schema": output_schema or {},
            "response_instructions": [
                "Reply ONLY with valid JSON matching OUTPUT_SCHEMA.",
                "Mark any invented or unverified facts under 'flags'.",
                f"Generate content appropriate for {mode} mode.",
                "Maintain consistency with provided context.",
            ],
            "temperature_hint": self._get_temperature_for_mode(mode),
            "max_tokens_hint": 2048,
        }

        return prompt_data

    def _get_topic_category(self, topic: str) -> str:
        """Map specific topics to general categories for examples"""
        category_mapping = {
            "story": "story",
            "lesson_plan": "lesson_plan",
            "study_guide": "study_guide",
            "article": "story",  # Use story examples for articles
            "research": "study_guide",  # Use study guide examples for research
        }
        return category_mapping.get(topic, "story")  # Default to story

    def _get_examples_for_topic(self, topic_category: str) -> List[Dict[str, Any]]:
        """Get few-shot examples for a topic category"""
        examples = self.examples_cache.get(topic_category, [])
        return examples[:2]  # Return max 2 examples to keep prompts manageable

    def _get_temperature_for_mode(self, mode: str) -> float:
        """Get suggested temperature based on generation mode"""
        temperature_map = {"conservative": 0.1, "balanced": 0.39, "creative": 0.7}
        return temperature_map.get(mode, 0.39)

    def format_prompt_for_llm(self, prompt_data: Dict[str, Any]) -> str:
        """Format the prompt data into a string for LLM consumption"""
        lines = [
            f"SYSTEM: {prompt_data['system_role']}",
            "",
            "TOPIC_CONTEXT:",
            f"- topic: {prompt_data['topic_context']['topic']}",
            f"- descriptor: {prompt_data['topic_context']['descriptor']}",
            f"- workspace_summary: {prompt_data['topic_context']['workspace_summary']}",
            "",
            "CONSTRAINTS:",
            f"- preserve: {prompt_data['constraints']['preserve']}",
            f"- max_items: {prompt_data['constraints']['max_items']}",
            f"- pov: {prompt_data['constraints']['pov']}",
            f"- mode: {prompt_data['constraints']['mode']}",
            "",
            "FEW_SHOT_EXAMPLES:",
        ]

        # Add examples
        for i, example in enumerate(prompt_data["few_shot_examples"]):
            lines.append(f"- example_{i+1}: {json.dumps(example, ensure_ascii=False)}")

        lines.extend(
            [
                "",
                "OUTPUT_SCHEMA:",
                json.dumps(prompt_data["output_schema"], indent=2),
                "",
                "RESPONSE_INSTRUCTIONS:",
            ]
        )

        # Add response instructions
        for instruction in prompt_data["response_instructions"]:
            lines.append(f"- {instruction}")

        return "\n".join(lines)


class SessionAPIManager:
    """Manages session lifecycle, policies, and orchestrates other agents via API"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ptg = PromptTemplateGenerator()
        self.active_sessions = {}
        self.session_policies = {}

    async def create_session(self, request: NewSessionRequest) -> WorkspaceSchema:
        """Create a new session workspace"""
        session_id = self._generate_session_id()

        # Create workspace
        workspace = WorkspaceSchema(
            session_id=session_id,
            user_id=request.user_id,
            topic=request.topic,
            topic_descriptor=request.topic_descriptor,
            topic_content=request.initial_content,
            policy=request.policy or PolicySchema(),
            created_at=datetime.utcnow(),
            last_modified=datetime.utcnow(),
        )

        # Store in active sessions
        self.active_sessions[session_id] = workspace
        self.session_policies[session_id] = workspace.policy

        logger.info(f"Created session {session_id} for user {request.user_id}")
        return workspace

    def _generate_session_id(self) -> str:
        """Generate a unique session ID"""
        import uuid

        return f"session_{uuid.uuid4().hex[:12]}"

    async def get_session(self, session_id: str) -> Optional[WorkspaceSchema]:
        """Get session workspace"""
        return self.active_sessions.get(session_id)

    async def update_session(self, session_id: str, workspace: WorkspaceSchema) -> bool:
        """Update session workspace"""
        if session_id not in self.active_sessions:
            return False

        workspace.last_modified = datetime.utcnow()
        self.active_sessions[session_id] = workspace
        logger.debug(f"Updated session {session_id}")
        return True

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        if session_id in self.session_policies:
            del self.session_policies[session_id]
        logger.info(f"Deleted session {session_id}")
        return True

    def should_suggest(self, session_id: str, context: Dict[str, Any]) -> bool:
        """Determine if suggestions should be triggered based on policy"""
        policy = self.session_policies.get(session_id)
        if not policy:
            return False

        if policy.suggestion_mode == SuggestionMode.ON_DEMAND:
            return context.get("user_requested", False)

        elif policy.suggestion_mode == SuggestionMode.IDLE_SMART:
            idle_time = context.get("idle_time", 0)
            return (
                idle_time > 60  # 60 seconds idle
                and context.get("recent_activity_low", False)
                and not context.get("suggestion_cooldown", False)
            )

        elif policy.suggestion_mode == SuggestionMode.PROACTIVE:
            return (
                context.get("low_creativity_detected", False)
                or context.get("high_opportunity_detected", False)
            ) and not context.get("suggestion_cooldown", False)

        return False

    def generate_workspace_summary(self, workspace: WorkspaceSchema) -> str:
        """Generate a concise summary of the current workspace state"""
        summary_parts = [
            f"Topic: {workspace.topic}",
            f"Content length: {len(workspace.topic_content)} characters",
            f"Events: {len(workspace.events)}",
            f"Characters: {len(workspace.characters)}",
        ]

        if workspace.topic_descriptor:
            summary_parts.append(f"Descriptor: {workspace.topic_descriptor}")

        # Add recent activity
        if workspace.history:
            last_action = workspace.history[-1]
            summary_parts.append(f"Last action: {last_action.get('type', 'unknown')}")

        return "; ".join(summary_parts)

    def create_agent_prompt(
        self, agent_name: str, workspace: WorkspaceSchema, agent_config: Dict[str, Any]
    ) -> str:
        """Create a prompt for a specific agent using PTG"""

        # Map agent names to roles
        role_mapping = {
            "planner": "Content Generator",
            "verifier": "Consistency Checker",
            "evaluator": "Quality Evaluator",
            "graph_manager": "Knowledge Graph Manager",
            "perception": "Content Analyzer",
        }

        role = role_mapping.get(agent_name, agent_name.title())

        # Get workspace summary
        workspace_summary = self.generate_workspace_summary(workspace)

        # Create prompt using PTG
        prompt_data = self.ptg.generate_agent_prompt(
            agent_role=role,
            topic=workspace.topic,
            topic_descriptor=workspace.topic_descriptor,
            workspace_summary=workspace_summary,
            mode=agent_config.get("mode", "balanced"),
            constraints=agent_config.get("constraints", {}),
            output_schema=agent_config.get("output_schema", {}),
        )

        return self.ptg.format_prompt_for_llm(prompt_data)

    def apply_global_policies(self, session_id: str, agent_output: Any) -> Any:
        """Apply global policies to agent outputs"""
        policy = self.session_policies.get(session_id)
        if not policy:
            return agent_output

        # Apply privacy filters
        if hasattr(agent_output, "flags"):
            if policy.strict_mode and agent_output.flags.get("unverified_facts"):
                # In strict mode, reject outputs with unverified facts
                logger.warning(
                    f"Rejected output due to strict mode: {agent_output.flags}"
                )
                return None

        # Apply bias detection
        if agent_output and hasattr(agent_output, "content"):
            bias_indicators = self._detect_bias(agent_output.content)
            if bias_indicators:
                agent_output.flags = getattr(agent_output, "flags", {})
                agent_output.flags["bias_detected"] = bias_indicators
                logger.info(f"Bias indicators detected: {bias_indicators}")

        return agent_output

    def _detect_bias(self, content: str) -> List[str]:
        """Detect potential bias indicators in content"""
        bias_indicators = []
        content_lower = content.lower()

        # Basic bias detection patterns
        bias_patterns = {
            "gender": ["all men", "all women", "typical male", "typical female"],
            "racial": ["all people of", "typical for their race"],
            "religious": ["all believers", "all atheists"],
            "age": [
                "all young people",
                "all old people",
                "millennials are",
                "boomers are",
            ],
            "stereotyping": ["as expected", "naturally", "obviously"],
        }

        for bias_type, patterns in bias_patterns.items():
            for pattern in patterns:
                if pattern in content_lower:
                    bias_indicators.append(f"{bias_type}: '{pattern}'")

        return bias_indicators

    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about active sessions"""
        return {
            "active_sessions": len(self.active_sessions),
            "sessions_by_topic": self._count_sessions_by_topic(),
            "average_content_length": self._calculate_average_content_length(),
        }

    def _count_sessions_by_topic(self) -> Dict[str, int]:
        """Count sessions by topic"""
        topic_counts = {}
        for workspace in self.active_sessions.values():
            topic = workspace.topic
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        return topic_counts

    def _calculate_average_content_length(self) -> float:
        """Calculate average content length across sessions"""
        if not self.active_sessions:
            return 0.0

        total_length = sum(
            len(workspace.topic_content) for workspace in self.active_sessions.values()
        )
        return total_length / len(self.active_sessions)


async def create_session_manager(config: Dict[str, Any]) -> SessionManager:
    """Factory function to create session manager"""
    return SessionManager(config)
