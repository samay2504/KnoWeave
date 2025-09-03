"""
Evaluator Agent - Human-AI Co-Creation System
Blueprint-compliant branch scoring and ranking agent
Agent 6 of 6: Scores and ranks branches using multiple criteria, provides final ordering
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

from utils.logging_cfg import get_agent_logger

logger = get_agent_logger("evaluator")


@dataclass
class BranchScore:
    """Schema for individual branch scoring"""
    branch_id: str
    scores: Dict[str, float]  # {"relevance": 0.9, "creativity": 0.7, "safety": 0.95, "cost": 0.8}
    composite_score: float
    rank: int
    recommended: bool
    reasons: List[str]


@dataclass
class EvaluatorResult:
    """Output schema for Evaluator Agent following canonical specification"""
    session_id: str
    ranked_branches: List[BranchScore]
    call_metadata: Dict[str, Any]
    
    def dict(self):
        """Convert to dictionary for compatibility"""
        return {
            'session_id': self.session_id,
            'ranked_branches': [
                {
                    'branch_id': b.branch_id,
                    'scores': b.scores,
                    'composite_score': b.composite_score,
                    'rank': b.rank,
                    'recommended': b.recommended,
                    'reasons': b.reasons
                } for b in self.ranked_branches
            ],
            'call_metadata': self.call_metadata
        }


class EvaluatorAgent:
    """
    Evaluator Agent - Blueprint-compliant branch scoring and ranking
    Now prompt-driven and supports domain-specific weighting.
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
        Blueprint-compliant invoke method for Evaluator Agent.
        Scores and ranks branches using a prompt-driven approach.
        """
        prompt_payload = agent_config.get("prompt_payload")
        if not prompt_payload or not self.llm_provider:
            logger.error("Evaluator agent requires a prompt payload and LLM provider.")
            return self._empty_response(workspace.get("session_id"))

        try:
            logger.info("Invoking Evaluator Agent with LLM-based evaluation.")
            
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

            if self.prompt_audit_enabled:
                self._log_prompt_audit(prompt_payload, llm_response)

            return llm_response

        except Exception as e:
            logger.error(f"LLM-based evaluation failed: {e}")
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
                "agent": "evaluator",
                "prompt_hash": hash(prompt_payload.get("prompt", "")),
                "metadata": prompt_payload.get("metadata", {}),
                "response_summary": {
                    "ranked_branches_count": len(response.get("ranked_branches", [])),
                    "top_branch_score": response.get("ranked_branches", [{}])[0].get("composite_score", 0)
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
            "ranked_branches": [],
            "call_metadata": {
                "provider": "local",
                "model": "error_fallback",
                "timestamp": datetime.utcnow().isoformat(),
                "error": "Evaluator agent failed to produce a response."
            }
        }


    async def invoke(
        self, workspace: Dict[str, Any], agent_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Main evaluator invoke - scores and ranks branches using multiple criteria

        Args:
            workspace: Contains branches to evaluate, criteria weights, user preferences
            agent_config: Agent-specific configuration

        Returns:
            EvaluatorResult with ranked branches and composite scores
        """
        logger.debug(f"Evaluator invoke called with workspace type: {type(workspace)}")
        
        session_id = workspace.get("session_id", "unknown")
        branches = workspace.get("branches", [])
        criteria_weights = workspace.get(
            "criteria_weights", self._get_default_weights()
        )
        user_preferences = workspace.get("user_preferences", {})

        logger.info(f"Evaluating {len(branches)} branches for session {session_id}")

        try:
            # Score each branch
            scored_branches = []
            logger.debug(f"Processing {len(branches)} branches")
            
            for i, branch in enumerate(branches):
                logger.debug(f"Processing branch {i}: type={type(branch)}")
                
                # Ensure branch is a dictionary
                if not isinstance(branch, dict):
                    logger.error(f"Branch {i} is not a dict: {type(branch)} - {branch}")
                    continue
                    
                logger.debug(f"About to score branch {i}")
                branch_score = await self._score_branch(
                    branch, criteria_weights, user_preferences, session_id
                )
                scored_branches.append(branch_score)

            # Sort by composite score (descending)
            scored_branches.sort(key=lambda x: x.composite_score, reverse=True)

            # Apply ranking and recommendations
            ranked_branches = self._apply_ranking_and_recommendations(scored_branches)

            # Create result
            result = EvaluatorResult(
                session_id=session_id,
                ranked_branches=ranked_branches,
                call_metadata={
                    "provider": "evaluator_agent",
                    "model": "internal_scoring",
                    "latency_ms": 0,  # Internal processing
                    "branches_evaluated": len(branches),
                    "criteria_used": list(criteria_weights.keys()),
                    "evaluation_timestamp": datetime.now().isoformat(),
                },
            )

            logger.info(f"Evaluation complete: {len(ranked_branches)} branches ranked")
            return result.dict()

        except Exception as e:
            logger.error(f"Evaluator invoke failed: {e}")
            return {
                "session_id": session_id,
                "ranked_branches": [],
                "error": str(e),
                "fallback": True,
                "call_metadata": {
                    "provider": "evaluator_agent",
                    "model": "fallback",
                    "latency_ms": 0,
                    "error": str(e),
                },
            }

    async def _score_branch(
        self,
        branch: Dict[str, Any],
        criteria_weights: Dict[str, float],
        user_preferences: Dict[str, Any],
        session_id: str,
    ) -> BranchScore:
        """
        Score an individual branch across all criteria

        Args:
            branch: Branch to score
            criteria_weights: Scoring weights {"relevance": 0.4, "creativity": 0.2, "safety": 0.3, "cost": -0.1}
            user_preferences: User preferences for scoring
            session_id: Session identifier

        Returns:
            BranchScore with individual and composite scores
        """
        branch_id = branch.get("branch_id", f"unknown_{hash(str(branch))}")
        
        logger.debug(f"Scoring branch: {branch_id}, type: {type(branch)}")

        # Calculate individual criterion scores
        scores = {}
        reasons = []

        # Relevance scoring (0-1)
        try:
            logger.debug(f"About to score relevance - branch type: {type(branch)}, prefs type: {type(user_preferences)}")
            relevance_score = self._score_relevance(branch, user_preferences)
            scores["relevance"] = relevance_score
        except Exception as e:
            logger.error(f"Relevance scoring failed: {e}, branch type: {type(branch)}, prefs type: {type(user_preferences)}")
            scores["relevance"] = 0.5
        if relevance_score > 0.8:
            reasons.append("High relevance to user intent")
        elif relevance_score < 0.4:
            reasons.append("Low relevance to requirements")

        # Creativity scoring (0-1)
        try:
            creativity_score = self._score_creativity(branch)
            scores["creativity"] = creativity_score
        except Exception as e:
            logger.error(f"Creativity scoring failed: {e}, branch type: {type(branch)}")
            scores["creativity"] = 0.5
        if scores["creativity"] > 0.7:
            reasons.append("Strong creative elements")
        elif scores["creativity"] < 0.3:
            reasons.append("Conservative approach")

        # Safety scoring (0-1)
        try:
            safety_score = self._score_safety(branch)
            scores["safety"] = safety_score
        except Exception as e:
            logger.error(f"Safety scoring failed: {e}, branch type: {type(branch)}")
            scores["safety"] = 0.5
        if scores["safety"] < 0.2:
            reasons.append("Safety concerns identified")
        elif scores["safety"] > 0.9:
            reasons.append("Safe content")

        # Cost scoring (0-1, higher is better efficiency)
        try:
            cost_score = self._score_cost_efficiency(branch)
            scores["cost"] = cost_score
        except Exception as e:
            logger.error(f"Cost scoring failed: {e}, branch type: {type(branch)}")
            scores["cost"] = 0.5
        if scores["cost"] > 0.8:
            reasons.append("Good cost efficiency")
        elif scores["cost"] < 0.4:
            reasons.append("Higher resource requirements")

        # Calculate composite score using weights
        composite_score = 0.0
        for criterion, weight in criteria_weights.items():
            if criterion in scores:
                composite_score += scores[criterion] * weight

        # Clamp composite score to [0, 1]
        composite_score = max(0.0, min(1.0, composite_score))

        # Determine recommendation based on safety override and composite score
        recommended = self._determine_recommendation(scores, composite_score)
        if not recommended and scores.get("safety", 1.0) < 0.2:
            reasons.append("Not recommended due to safety concerns")

        return BranchScore(
            branch_id=branch_id,
            scores=scores,
            composite_score=composite_score,
            rank=0,  # Will be set during ranking
            recommended=recommended,
            reasons=reasons,
        )

    def _score_relevance(
        self, branch: Dict[str, Any], user_preferences: Dict[str, Any]
    ) -> float:
        """Score branch relevance to user intent and requirements"""
        base_score = 0.7  # Default baseline

        # Check if branch title matches user preferences
        title = branch.get("title", "").lower()
        preferred_style = user_preferences.get("style", "").lower()

        if preferred_style in title:
            base_score += 0.2

        # Check step count vs preferences
        steps = branch.get("steps", [])
        preferred_complexity = user_preferences.get("complexity", "medium")

        if preferred_complexity == "simple" and len(steps) <= 4:
            base_score += 0.1
        elif preferred_complexity == "complex" and len(steps) > 6:
            base_score += 0.1
        elif preferred_complexity == "medium" and 4 < len(steps) <= 6:
            base_score += 0.1

        return min(1.0, base_score)

    def _score_creativity(self, branch: Dict[str, Any]) -> float:
        """Score branch creativity and originality"""
        base_score = 0.5  # Default baseline

        title = branch.get("title", "").lower()
        rationale = branch.get("rationale", "").lower()

        # Look for creative indicators
        creative_words = [
            "unique",
            "innovative",
            "creative",
            "original",
            "imaginative",
            "unexpected",
            "surprising",
            "novel",
            "artistic",
            "experimental",
        ]

        text_to_check = f"{title} {rationale}"
        creative_matches = sum(1 for word in creative_words if word in text_to_check)

        # Boost score based on creative language
        base_score += min(0.4, creative_matches * 0.1)

        # Check for creative step types
        steps = branch.get("steps", [])
        for step in steps:
            # Handle both string steps and dict steps
            if isinstance(step, dict):
                action = step.get("action", "").lower()
            elif isinstance(step, str):
                action = step.lower()
            else:
                action = str(step).lower()
                
            if any(creative_word in action for creative_word in creative_words):
                base_score += 0.1
                break

        return min(1.0, base_score)

    def _score_safety(self, branch: Dict[str, Any]) -> float:
        """Score branch safety and policy compliance"""
        base_score = 0.9  # Default safe baseline

        # Check safety_checks field
        safety_checks = branch.get("safety_checks", [])
        if not safety_checks:
            base_score -= 0.1

        # Look for safety violations in rationale or steps
        rationale = branch.get("rationale", "").lower()

        unsafe_indicators = [
            "violent",
            "harmful",
            "dangerous",
            "inappropriate",
            "offensive",
            "illegal",
            "explicit",
            "nsfw",
            "adult",
            "violence",
        ]

        for indicator in unsafe_indicators:
            if indicator in rationale:
                base_score -= 0.3
                break

        # Check steps for safety issues
        steps = branch.get("steps", [])
        for step in steps:
            # Handle both string steps and dict steps
            if isinstance(step, dict):
                action = step.get("action", "").lower()
            elif isinstance(step, str):
                action = step.lower()
            else:
                action = str(step).lower()
                
            if any(unsafe in action for unsafe in unsafe_indicators):
                base_score -= 0.2
                break

        return max(0.0, base_score)

    def _score_cost_efficiency(self, branch: Dict[str, Any]) -> float:
        """Score branch cost efficiency (lower cost = higher score)"""
        cost_estimate = branch.get("cost_estimate", {})

        # Get token and time estimates
        estimated_tokens = cost_estimate.get("tokens", 1000)  # Default assumption
        estimated_time_ms = cost_estimate.get("time_ms", 5000)  # Default assumption

        # Normalize scores (lower cost = higher score)
        # Token efficiency (assume 500-3000 token range)
        token_efficiency = max(0.0, min(1.0, (3000 - estimated_tokens) / 2500))

        # Time efficiency (assume 1000-10000 ms range)
        time_efficiency = max(0.0, min(1.0, (10000 - estimated_time_ms) / 9000))

        # Combined efficiency score
        efficiency_score = (token_efficiency + time_efficiency) / 2

        return efficiency_score

    def _determine_recommendation(
        self, scores: Dict[str, float], composite_score: float
    ) -> bool:
        """
        Determine if branch should be recommended

        Safety override: If safety < 0.2, set recommended=false regardless of composite score
        """
        safety_score = scores.get("safety", 1.0)

        # Safety override
        if safety_score < 0.2:
            return False

        # Recommend if composite score is above threshold
        return composite_score >= 0.6

    def _apply_ranking_and_recommendations(
        self, scored_branches: List[BranchScore]
    ) -> List[BranchScore]:
        """
        Apply final ranking with tie-breaking rules

        Tie breaking: use safety then relevance as specified
        """
        # Sort with tie-breaking: composite_score DESC, safety DESC, relevance DESC
        scored_branches.sort(
            key=lambda x: (
                x.composite_score,
                x.scores.get("safety", 0),
                x.scores.get("relevance", 0),
            ),
            reverse=True,
        )

        # Apply ranking
        for i, branch in enumerate(scored_branches):
            branch.rank = i + 1

        return scored_branches

    def _get_default_weights(self) -> Dict[str, float]:
        """Get default criteria weights following canonical specification"""
        return {
            "relevance": 0.4,
            "creativity": 0.2,
            "safety": 0.3,
            "cost": -0.1,  # Negative weight: higher cost reduces composite score
        }

    async def call_agent_with_retry(
        self, agent_name: str, prompt_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call agent with retry logic and JSON validation
        Note: Evaluator primarily uses internal scoring, but this method supports LLM fallback
        """
        if not self.llm_provider:
            logger.warning(
                "No LLM provider available for evaluator, using internal scoring only"
            )
            return {"fallback": True, "reason": "no_llm_provider"}

        for attempt in range(self.RETRY_MAX):
            try:
                # Call LLM provider
                response = await self.llm_provider.invoke(prompt_data["prompt"])

                # Validate JSON response
                result = self.validate_json_response(response.get("content", ""))
                if result.get("valid"):
                    return result["data"]

                # Add retry instruction for next attempt
                if attempt < self.RETRY_MAX - 1:
                    prompt_data["prompt"] += f"\n\n{self.RETRY_INSTRUCTION}"

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt == self.RETRY_MAX - 1:
                    return {"fallback": True, "error": str(e)}

        return {"fallback": True, "reason": "max_retries_exceeded"}

    def validate_json_response(self, response: str) -> Dict[str, Any]:
        """Validate JSON response with regex fallback"""
        try:
            # Try direct parsing
            data = json.loads(response)
            return {"valid": True, "data": data}
        except json.JSONDecodeError:
            # Try regex extraction
            import re

            json_patterns = [r"\{[^{}]*\}", r"\{.*?\}", r"```json\s*(\{.*?\})\s*```"]

            for pattern in json_patterns:
                matches = re.findall(pattern, response, re.DOTALL)
                for match in matches:
                    try:
                        data = json.loads(match)
                        return {"valid": True, "data": data}
                    except json.JSONDecodeError:
                        continue

            return {"valid": False, "error": "No valid JSON found"}


# Factory function for agent creation
async def create_evaluator_agent(
    config: Dict[str, Any], llm_provider=None
) -> EvaluatorAgent:
    """Create and initialize evaluator agent"""
    return EvaluatorAgent(config, llm_provider)
