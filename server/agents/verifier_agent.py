"""
Verifier Agent - Consistency checking and fact verification
Checks for consistency violations and marks unverified facts
"""

import re
import logging
import asyncio
from typing import Dict, Any, List, Optional, Set, Tuple

from utils.schemas import (
    WorkspaceSchema,
    ProjectionSchema,
    VerificationOutput,
    CharacterSchema,
    EventSchema,
)
from utils.logging_cfg import get_agent_logger

logger = get_agent_logger("verifier")


class VerifierAgent:
    """Agent for consistency checking and fact verification"""

    def __init__(self, config: Dict[str, Any], llm_provider=None):
        self.config = config
        self.llm_provider = llm_provider

        # Grammar and style patterns
        self.grammar_patterns = {
            "incomplete_sentence": re.compile(r"\b[A-Z][^.!?]*$"),
            "run_on_sentence": re.compile(r"[^.!?]{200,}[.!?]"),
            "comma_splice": re.compile(r"\w+,\s*[A-Z]"),
            "subject_verb_disagreement": re.compile(
                r"\b(is|was)\s+\w*(?:s|es)\b|\b(are|were)\s+\w*(?:[^s]|[^e]s)\b"
            ),
        }

        # Consistency patterns
        self.pronoun_patterns = {
            "first_person": re.compile(
                r"\b(I|me|my|mine|myself|we|us|our|ours|ourselves)\b", re.IGNORECASE
            ),
            "second_person": re.compile(
                r"\b(you|your|yours|yourself|yourselves)\b", re.IGNORECASE
            ),
            "third_person": re.compile(
                r"\b(he|him|his|himself|she|her|hers|herself|it|its|itself|they|them|their|theirs|themselves)\b",
                re.IGNORECASE,
            ),
        }

        # Fact checking patterns
        self.uncertain_phrases = [
            "might",
            "could",
            "perhaps",
            "maybe",
            "possibly",
            "probably",
            "seems",
            "appears",
            "allegedly",
            "supposedly",
            "reportedly",
        ]

        self.definitive_phrases = [
            "definitely",
            "certainly",
            "absolutely",
            "undoubtedly",
            "clearly",
            "obviously",
            "factually",
            "proven",
        ]

    async def initialize(self):
        """Initialize the verifier agent"""
        logger.info("Initializing Verifier Agent")
        # Initialize verification resources
        logger.info("Verifier Agent initialized successfully")

    async def cleanup(self):
        """Cleanup verifier agent resources"""
        logger.info("Cleaning up Verifier Agent")
        # Clear any cached data
        logger.info("Verifier Agent cleanup completed")

    async def invoke(
        self, workspace: Dict[str, Any], agent_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Blueprint-compliant invoke method for Verifier Agent
        Validates content quality, consistency, and constraints
        """
        logger.info(
            f"Verifying content for session {workspace.get('session_id', 'unknown')}"
        )

        # Get workspace data
        topic_content = workspace.get("topic_content", "")
        perception_data = workspace.get("perception_analysis", {})
        planning_data = workspace.get("planner_analysis", {})
        graph_data = workspace.get("graph_analysis", {})

        # Configure validation based on agent config
        self._configure_validation_blueprint(agent_config, workspace)

        # Run comprehensive validation
        validation_results = await self._run_blueprint_validation_suite(
            topic_content, perception_data, planning_data, graph_data
        )

        # Calculate overall quality score
        quality_assessment = await self._assess_blueprint_quality(validation_results)

        # Generate improvement suggestions
        improvement_suggestions = await self._generate_blueprint_suggestions(
            validation_results, workspace
        )

        # Create validation report
        validation_report = await self._create_blueprint_report(
            validation_results, quality_assessment, improvement_suggestions
        )

        result = {
            "validation_results": validation_results,
            "quality_assessment": quality_assessment,
            "improvement_suggestions": improvement_suggestions,
            "validation_report": validation_report,
            "metadata": {
                "checks_performed": len(validation_results),
                "passed_checks": len(
                    [r for r in validation_results if r.get("passed", False)]
                ),
                "failed_checks": len(
                    [r for r in validation_results if not r.get("passed", True)]
                ),
                "timestamp": "2024-01-01T00:00:00Z",  # Would use datetime.now().isoformat()
            },
        }

        logger.debug(
            f"Blueprint verification complete - {len(validation_results)} checks, "
            f"{quality_assessment.get('overall_score', 0.0):.2f} quality score"
        )
        return result

    def _configure_validation_blueprint(
        self, agent_config: Dict[str, Any], workspace: Dict[str, Any]
    ) -> None:
        """Configure validation for blueprint compliance"""
        # Get content parameters
        content_plan = workspace.get("planner_analysis", {}).get("content_plan", {})
        content_type = content_plan.get("content_type", "story")
        topic_mode = workspace.get("topic_mode", "balanced")
        target_length = agent_config.get("target_length", "medium")
        audience = agent_config.get("audience", "general")

        # Store configuration for use in validation
        self.validation_config = {
            "content_type": content_type,
            "topic_mode": topic_mode,
            "target_length": target_length,
            "audience": audience,
        }

    async def _run_blueprint_validation_suite(
        self,
        topic_content: str,
        perception_data: Dict[str, Any],
        planning_data: Dict[str, Any],
        graph_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Run blueprint-compliant validation suite"""
        results = []

        # Grammar and readability
        grammar_result = await self._validate_blueprint_grammar(topic_content)
        results.append(grammar_result)

        # Content consistency
        consistency_result = await self._validate_blueprint_consistency(
            topic_content, perception_data
        )
        results.append(consistency_result)

        # Structural completeness
        completeness_result = await self._validate_blueprint_completeness(
            topic_content, planning_data
        )
        results.append(completeness_result)

        # Length requirements
        length_result = await self._validate_blueprint_length(topic_content)
        results.append(length_result)

        # Audience appropriateness
        audience_result = await self._validate_blueprint_audience(topic_content)
        results.append(audience_result)

        return results

    async def _validate_blueprint_grammar(self, topic_content: str) -> Dict[str, Any]:
        """Validate grammar using blueprint format"""
        if not topic_content.strip():
            return {
                "rule_id": "grammar",
                "rule_name": "Grammar Check",
                "passed": False,
                "score": 0.0,
                "message": "No content to check",
                "suggestions": ["Add content to validate"],
            }

        # Use existing grammar check
        grammar_score = self._check_grammar(topic_content)
        passed = grammar_score >= 0.8

        suggestions = []
        if not passed:
            suggestions.extend(
                [
                    "Review text for grammar errors",
                    "Check sentence structure and punctuation",
                    "Consider using grammar checking tools",
                ]
            )

        return {
            "rule_id": "grammar",
            "rule_name": "Grammar Check",
            "passed": passed,
            "score": grammar_score,
            "message": f"Grammar score: {grammar_score:.2f}",
            "suggestions": suggestions,
        }

    async def _validate_blueprint_consistency(
        self, topic_content: str, perception_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate consistency using blueprint format"""
        consistency_score = 1.0
        issues = []

        # POV consistency
        pov = perception_data.get("pov", "unknown")
        if pov == "mixed":
            consistency_score *= 0.7
            issues.append("Mixed point of view detected")
        elif pov == "unknown":
            consistency_score *= 0.8
            issues.append("Point of view unclear")

        # Character consistency (simplified)
        characters = perception_data.get("characters", [])
        for character in characters:
            name = character.get("name", "")
            if name:
                mentions = topic_content.lower().count(name.lower())
                if mentions > 0 and mentions != character.get("mentions", 0):
                    consistency_score *= 0.9
                    issues.append(f"Character mention count mismatch for {name}")

        passed = consistency_score >= 0.8 and len(issues) <= 1

        suggestions = []
        if not passed:
            suggestions.extend(
                [
                    "Maintain consistent point of view",
                    "Check character name consistency",
                    "Review content for logical consistency",
                ]
            )

        return {
            "rule_id": "consistency",
            "rule_name": "Content Consistency",
            "passed": passed,
            "score": consistency_score,
            "message": f"Consistency score: {consistency_score:.2f}",
            "details": {"issues": issues},
            "suggestions": suggestions,
        }

    async def _validate_blueprint_completeness(
        self, topic_content: str, planning_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate completeness using blueprint format"""
        outline = planning_data.get("outline", [])

        if not outline:
            return {
                "rule_id": "completeness",
                "rule_name": "Content Completeness",
                "passed": True,
                "score": 1.0,
                "message": "No outline to validate against",
                "suggestions": [],
            }

        # Check if outlined sections appear in content
        addressed_sections = 0
        missing_sections = []

        for item in outline:
            section = item.get("section", "")
            if section:
                if section.lower() in topic_content.lower():
                    addressed_sections += 1
                else:
                    missing_sections.append(section)

        completeness_score = addressed_sections / len(outline) if outline else 1.0
        passed = completeness_score >= 0.8

        suggestions = []
        if not passed:
            for section in missing_sections:
                suggestions.append(f"Add content for {section} section")

        return {
            "rule_id": "completeness",
            "rule_name": "Content Completeness",
            "passed": passed,
            "score": completeness_score,
            "message": f"Addressed {addressed_sections}/{len(outline)} planned sections",
            "details": {"missing_sections": missing_sections},
            "suggestions": suggestions,
        }

    async def _validate_blueprint_length(self, topic_content: str) -> Dict[str, Any]:
        """Validate length requirements using blueprint format"""
        word_count = len(topic_content.split())

        # Get length requirements from config
        target_length = self.validation_config.get("target_length", "medium")
        length_requirements = {
            "short": {"min": 50, "max": 300},
            "medium": {"min": 200, "max": 800},
            "long": {"min": 500, "max": 2000},
        }

        requirements = length_requirements.get(
            target_length, length_requirements["medium"]
        )
        min_words = requirements["min"]
        max_words = requirements["max"]

        if word_count < min_words:
            passed = False
            length_score = word_count / min_words
            message = f"Content too short: {word_count} words (min: {min_words})"
            suggestions = [f"Add approximately {min_words - word_count} more words"]
        elif word_count > max_words:
            passed = False
            length_score = max_words / word_count
            message = f"Content too long: {word_count} words (max: {max_words})"
            suggestions = [f"Remove approximately {word_count - max_words} words"]
        else:
            passed = True
            length_score = 1.0
            message = f"Appropriate length: {word_count} words"
            suggestions = []

        return {
            "rule_id": "length",
            "rule_name": "Length Requirements",
            "passed": passed,
            "score": length_score,
            "message": message,
            "details": {
                "word_count": word_count,
                "min_words": min_words,
                "max_words": max_words,
            },
            "suggestions": suggestions,
        }

    async def _validate_blueprint_audience(self, topic_content: str) -> Dict[str, Any]:
        """Validate audience appropriateness using blueprint format"""
        target_audience = self.validation_config.get("audience", "general")

        # Simple vocabulary complexity check
        words = topic_content.lower().split()
        complex_words = len([w for w in words if len(w) > 12])
        complexity_ratio = complex_words / len(words) if words else 0

        # Audience-specific thresholds
        complexity_thresholds = {
            "children": 0.05,
            "students": 0.15,
            "general": 0.25,
            "experts": 0.40,
        }

        threshold = complexity_thresholds.get(target_audience, 0.25)
        passed = complexity_ratio <= threshold
        audience_score = (
            min(1.0, threshold / complexity_ratio) if complexity_ratio > 0 else 1.0
        )

        suggestions = []
        if not passed:
            suggestions.append(f"Simplify vocabulary for {target_audience} audience")
            suggestions.append("Use shorter, more common words")

        return {
            "rule_id": "audience",
            "rule_name": "Audience Appropriateness",
            "passed": passed,
            "score": audience_score,
            "message": f"Complexity ratio: {complexity_ratio:.2f} (threshold: {threshold})",
            "details": {
                "complexity_ratio": complexity_ratio,
                "target_audience": target_audience,
            },
            "suggestions": suggestions,
        }

    async def _assess_blueprint_quality(
        self, validation_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Assess overall quality for blueprint compliance"""
        if not validation_results:
            return {
                "overall_score": 0.0,
                "grade": "unknown",
                "summary": "No validation performed",
            }

        # Calculate weighted average
        total_score = sum(result.get("score", 0.0) for result in validation_results)
        overall_score = total_score / len(validation_results)

        # Determine grade
        if overall_score >= 0.9:
            grade = "excellent"
        elif overall_score >= 0.8:
            grade = "good"
        elif overall_score >= 0.7:
            grade = "acceptable"
        elif overall_score >= 0.6:
            grade = "needs_improvement"
        else:
            grade = "poor"

        # Count passes/fails
        passed_count = len([r for r in validation_results if r.get("passed", False)])
        failed_count = len(validation_results) - passed_count

        return {
            "overall_score": overall_score,
            "grade": grade,
            "passed_checks": passed_count,
            "failed_checks": failed_count,
            "total_checks": len(validation_results),
            "summary": f"Overall quality: {grade} ({overall_score:.2f})",
        }

    async def _generate_blueprint_suggestions(
        self, validation_results: List[Dict[str, Any]], workspace: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate improvement suggestions for blueprint compliance"""
        suggestions = []

        # Priority mapping
        priority_map = {
            "grammar": "high",
            "consistency": "high",
            "completeness": "medium",
            "length": "medium",
            "audience": "low",
        }

        for result in validation_results:
            if not result.get("passed", True):
                rule_id = result.get("rule_id", "unknown")
                rule_suggestions = result.get("suggestions", [])

                for suggestion in rule_suggestions:
                    suggestions.append(
                        {
                            "category": rule_id,
                            "priority": priority_map.get(rule_id, "medium"),
                            "suggestion": suggestion,
                            "rule": result.get("rule_name", rule_id),
                            "score_impact": 1.0 - result.get("score", 0.0),
                        }
                    )

        # Sort by priority and impact
        priority_order = {"high": 3, "medium": 2, "low": 1}
        suggestions.sort(
            key=lambda x: (priority_order.get(x["priority"], 0), x["score_impact"]),
            reverse=True,
        )

        return suggestions[:10]  # Return top 10 suggestions

    async def _create_blueprint_report(
        self,
        validation_results: List[Dict[str, Any]],
        quality_assessment: Dict[str, Any],
        improvement_suggestions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Create blueprint-compliant validation report"""

        # Group results by rule
        rule_summaries = {}
        for result in validation_results:
            rule_id = result.get("rule_id", "unknown")
            rule_summaries[rule_id] = {
                "rule_name": result.get("rule_name", rule_id),
                "passed": result.get("passed", False),
                "score": result.get("score", 0.0),
                "message": result.get("message", ""),
                "suggestions": result.get("suggestions", []),
            }

        # Priority actions
        priority_actions = [
            s for s in improvement_suggestions if s["priority"] == "high"
        ][:3]

        return {
            "summary": quality_assessment["summary"],
            "overall_score": quality_assessment["overall_score"],
            "grade": quality_assessment["grade"],
            "rule_summaries": rule_summaries,
            "priority_actions": priority_actions,
            "improvement_suggestions": improvement_suggestions,
            "validation_timestamp": "2024-01-01T00:00:00Z",  # Would use datetime.now().isoformat()
            "recommendations": self._generate_blueprint_recommendations(
                quality_assessment
            ),
        }

    def _generate_blueprint_recommendations(
        self, quality_assessment: Dict[str, Any]
    ) -> List[str]:
        """Generate high-level recommendations for blueprint compliance"""
        recommendations = []
        overall_score = quality_assessment["overall_score"]

        if overall_score < 0.6:
            recommendations.append(
                "Content requires significant revision before completion"
            )
        elif overall_score < 0.8:
            recommendations.append(
                "Content is good but could benefit from focused improvements"
            )
        else:
            recommendations.append(
                "Content quality is high, minor refinements may be beneficial"
            )

        return recommendations

    async def _verify_single_projection(
        self, workspace: WorkspaceSchema, projection: ProjectionSchema
    ) -> VerificationOutput:
        """Verify a single projection for consistency and accuracy"""

        # Initialize verification result
        result = VerificationOutput()

        # 1. Grammar and style checking
        result.grammar_score = self._check_grammar(projection.paragraph)

        # 2. POV consistency checking
        result.pov_consistent = self._check_pov_consistency(
            workspace, projection.paragraph
        )
        if not result.pov_consistent:
            result.violations.append("Point of view inconsistency detected")

        # 3. Character consistency checking
        char_consistency, char_violations = self._check_character_consistency(
            workspace, projection
        )
        result.character_consistent = char_consistency
        result.violations.extend(char_violations)

        # 4. Fact verification
        verified_facts, unverified_facts = await self._verify_facts(
            workspace, projection
        )
        result.verified_facts = verified_facts
        result.unverified_facts = unverified_facts

        # 5. Generate improvement suggestions
        result.suggestions = self._generate_suggestions(workspace, projection, result)

        logger.debug(
            f"Verification complete - Grammar: {result.grammar_score:.2f}, "
            f"POV: {result.pov_consistent}, Character: {result.character_consistent}"
        )

        return result

    def _check_grammar(self, text: str) -> float:
        """Check grammar and return a score between 0 and 1"""
        if not text.strip():
            return 0.0

        total_checks = 0
        issues_found = 0

        # Check for various grammar issues
        for pattern_name, pattern in self.grammar_patterns.items():
            matches = pattern.findall(text)
            total_checks += 1

            if pattern_name == "incomplete_sentence" and matches:
                issues_found += 1
            elif pattern_name == "run_on_sentence" and matches:
                issues_found += 1
            elif pattern_name == "comma_splice" and matches:
                issues_found += 1
            elif pattern_name == "subject_verb_disagreement" and matches:
                issues_found += 1

        # Check sentence structure
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if sentences:
            total_checks += 2

            # Check for very short sentences (< 3 words)
            short_sentences = sum(1 for s in sentences if len(s.split()) < 3)
            if short_sentences / len(sentences) > 0.3:  # More than 30% are too short
                issues_found += 1

            # Check for very long sentences (> 40 words)
            long_sentences = sum(1 for s in sentences if len(s.split()) > 40)
            if long_sentences / len(sentences) > 0.2:  # More than 20% are too long
                issues_found += 1

        # Calculate score
        if total_checks == 0:
            return 1.0

        score = 1.0 - (issues_found / total_checks)
        return max(0.0, score)

    def _check_pov_consistency(self, workspace: WorkspaceSchema, text: str) -> bool:
        """Check if point of view is consistent with the workspace"""
        if not workspace.policy.preserve_pov:
            return True  # POV preservation not required

        # Detect POV in existing content
        existing_pov = self._detect_pov(workspace.topic_content)

        # Detect POV in new text
        new_pov = self._detect_pov(text)

        # If we can't detect either POV, assume consistency
        if not existing_pov or not new_pov:
            return True

        # Check for consistency
        return existing_pov == new_pov or new_pov == "mixed"

    def _detect_pov(self, text: str) -> Optional[str]:
        """Detect the dominant point of view in text"""
        if not text.strip():
            return None

        # Count pronouns for each POV
        pov_counts = {}
        for pov_type, pattern in self.pronoun_patterns.items():
            matches = pattern.findall(text)
            pov_counts[pov_type] = len(matches)

        total_pronouns = sum(pov_counts.values())

        if total_pronouns == 0:
            return None

        # Find dominant POV
        dominant_pov = max(pov_counts, key=pov_counts.get)
        dominant_count = pov_counts[dominant_pov]

        # Check if it's clearly dominant (>50%) or mixed
        if dominant_count / total_pronouns > 0.5:
            return dominant_pov
        else:
            return "mixed"

    def _check_character_consistency(
        self, workspace: WorkspaceSchema, projection: ProjectionSchema
    ) -> Tuple[bool, List[str]]:
        """Check character consistency"""
        if not workspace.policy.preserve_characters:
            return True, []

        violations = []

        # Extract character names mentioned in the projection
        mentioned_chars = self._extract_character_names(projection.paragraph)

        # Check each mentioned character
        for char_name in mentioned_chars:
            if char_name in workspace.characters:
                character = workspace.characters[char_name]
                violations.extend(
                    self._check_character_traits(
                        char_name, character, projection.paragraph
                    )
                )
            else:
                # New character introduced - check if this violates policy
                if workspace.policy.strict_mode:
                    violations.append(
                        f"New character '{char_name}' introduced without prior definition"
                    )

        # Check for trait consistency in events
        for event in projection.events:
            if event.actor and event.actor in workspace.characters:
                character = workspace.characters[event.actor]
                trait_violations = self._check_event_character_consistency(
                    event, character
                )
                violations.extend(trait_violations)

        return len(violations) == 0, violations

    def _extract_character_names(self, text: str) -> Set[str]:
        """Extract character names from text"""
        # Simple approach: look for capitalized words that might be names
        # This could be enhanced with NER
        words = re.findall(r"\b[A-Z][a-z]+\b", text)

        # Filter out common non-name words
        common_words = {
            "The",
            "This",
            "That",
            "These",
            "Those",
            "When",
            "Where",
            "What",
            "Who",
            "Why",
            "How",
            "But",
            "And",
            "Or",
            "So",
            "Yet",
            "For",
            "Nor",
            "Because",
            "Since",
            "Although",
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        }

        potential_names = set(
            word for word in words if word not in common_words and len(word) > 2
        )
        return potential_names

    def _check_character_traits(
        self, char_name: str, character: CharacterSchema, text: str
    ) -> List[str]:
        """Check if character behavior matches defined traits"""
        violations = []
        text_lower = text.lower()
        char_name_lower = char_name.lower()

        # Look for contradictory traits
        for trait in character.traits:
            trait_lower = trait.lower()

            # Define opposing traits
            trait_opposites = {
                "brave": ["cowardly", "fearful", "scared", "timid"],
                "kind": ["cruel", "mean", "harsh", "unkind"],
                "smart": ["stupid", "dumb", "foolish", "ignorant"],
                "funny": ["serious", "humorless", "grim"],
                "calm": ["angry", "agitated", "frantic", "excited"],
                "honest": ["dishonest", "lying", "deceptive"],
                "shy": ["bold", "outgoing", "confident", "assertive"],
            }

            # Check for contradictions
            if trait_lower in trait_opposites:
                for opposite in trait_opposites[trait_lower]:
                    if opposite in text_lower and char_name_lower in text_lower:
                        violations.append(
                            f"Character {char_name} described as '{opposite}' "
                            f"contradicts established trait '{trait}'"
                        )

        return violations

    def _check_event_character_consistency(
        self, event: EventSchema, character: CharacterSchema
    ) -> List[str]:
        """Check if event actions are consistent with character traits"""
        violations = []
        event_lower = event.summary.lower()

        # Check for trait-inconsistent actions
        inconsistent_patterns = {
            "brave": ["ran away", "hid", "cowered", "fled"],
            "kind": ["attacked", "hurt", "insulted", "mocked"],
            "calm": ["screamed", "yelled", "raged", "exploded"],
            "honest": ["lied", "deceived", "tricked", "misled"],
            "shy": ["boldly spoke", "confidently stated", "loudly proclaimed"],
        }

        for trait in character.traits:
            trait_lower = trait.lower()
            if trait_lower in inconsistent_patterns:
                for pattern in inconsistent_patterns[trait_lower]:
                    if pattern in event_lower:
                        violations.append(
                            f"Event '{event.summary}' for {event.actor} "
                            f"inconsistent with trait '{trait}'"
                        )

        return violations

    async def _verify_facts(
        self, workspace: WorkspaceSchema, projection: ProjectionSchema
    ) -> Tuple[List[str], List[str]]:
        """Verify facts in the projection"""
        verified_facts = []
        unverified_facts = []

        text = projection.paragraph

        # Check for uncertain language
        for phrase in self.uncertain_phrases:
            if phrase in text.lower():
                # Extract sentence containing uncertain phrase
                sentences = re.split(r"[.!?]+", text)
                for sentence in sentences:
                    if phrase in sentence.lower():
                        unverified_facts.append(f"Uncertain: {sentence.strip()}")

        # Check for definitive statements
        for phrase in self.definitive_phrases:
            if phrase in text.lower():
                sentences = re.split(r"[.!?]+", text)
                for sentence in sentences:
                    if phrase in sentence.lower():
                        verified_facts.append(
                            f"Stated definitively: {sentence.strip()}"
                        )

        # Check against existing knowledge base
        existing_facts = set()
        for triple in workspace.kb_triples:
            if len(triple) >= 3:
                fact = f"{triple[0]} {triple[1]} {triple[2]}"
                existing_facts.add(fact.lower())

        # Look for new factual claims
        sentences = re.split(r"[.!?]+", text)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:  # Ignore very short sentences
                # Check if this introduces new factual information
                if (
                    self._appears_factual(sentence)
                    and sentence.lower() not in existing_facts
                ):
                    unverified_facts.append(f"New fact: {sentence}")

        # Use LLM for advanced fact checking if available
        if self.llm_provider and workspace.policy.strict_mode:
            try:
                llm_verified = await self._llm_fact_check(workspace, text)
                unverified_facts.extend(llm_verified)
            except Exception as e:
                logger.warning(f"LLM fact checking failed: {e}")

        return verified_facts, unverified_facts

    def _appears_factual(self, sentence: str) -> bool:
        """Determine if a sentence appears to state facts"""
        # Heuristics for factual statements
        factual_verbs = [
            "is",
            "was",
            "are",
            "were",
            "has",
            "have",
            "had",
            "contains",
            "includes",
        ]
        sentence_lower = sentence.lower()

        # Check for factual verbs
        for verb in factual_verbs:
            if f" {verb} " in sentence_lower:
                return True

        # Check for specific patterns that suggest facts
        factual_patterns = [
            r"\b\d+\s+(years?|months?|days?|hours?)\b",  # Time periods
            r"\b(located|situated|born|died|founded|established)\b",  # Factual verbs
            r"\b(capital|population|area|height|weight|length)\b",  # Measurable properties
        ]

        for pattern in factual_patterns:
            if re.search(pattern, sentence_lower):
                return True

        return False

    async def _llm_fact_check(self, workspace: WorkspaceSchema, text: str) -> List[str]:
        """Use LLM to check facts"""
        if not self.llm_provider:
            return []

        prompt = f"""
        Check the following text for factual claims that may need verification:
        
        Context from existing content:
        {workspace.topic_content[-500:]}
        
        New text to check:
        {text}
        
        Identify any factual claims in the new text that:
        1. Cannot be verified from the existing context
        2. Seem questionable or potentially inaccurate
        3. Contradict information in the existing context
        
        Return a list of questionable facts, or "NONE" if all facts seem verifiable.
        """

        try:
            response = await self.llm_provider.invoke(prompt)

            if isinstance(response, str) and "NONE" not in response.upper():
                # Parse the response for fact issues
                lines = response.split("\n")
                return [
                    line.strip()
                    for line in lines
                    if line.strip() and not line.startswith("-")
                ]

        except Exception as e:
            logger.error(f"LLM fact checking failed: {e}")

        return []

    def _generate_suggestions(
        self,
        workspace: WorkspaceSchema,
        projection: ProjectionSchema,
        verification_result: VerificationOutput,
    ) -> List[str]:
        """Generate improvement suggestions based on verification results"""
        suggestions = []

        # Grammar suggestions
        if verification_result.grammar_score < 0.7:
            suggestions.append(
                "Consider revising for better grammar and sentence structure"
            )

        # POV suggestions
        if not verification_result.pov_consistent:
            existing_pov = self._detect_pov(workspace.topic_content)
            suggestions.append(
                f"Maintain consistent point of view (detected: {existing_pov})"
            )

        # Character consistency suggestions
        if not verification_result.character_consistent:
            suggestions.append("Ensure character actions align with established traits")

        # Fact verification suggestions
        if verification_result.unverified_facts:
            suggestions.append("Verify or clearly mark uncertain factual claims")

        # Style suggestions based on topic
        if workspace.topic == "lesson_plan":
            suggestions.append("Ensure activities are age-appropriate and time-bounded")
        elif workspace.topic == "story":
            suggestions.append("Consider pacing and narrative flow")

        return suggestions


async def create_verifier_agent(
    config: Dict[str, Any], llm_provider=None
) -> VerifierAgent:
    """Factory function to create verifier agent"""
    return VerifierAgent(config, llm_provider)
