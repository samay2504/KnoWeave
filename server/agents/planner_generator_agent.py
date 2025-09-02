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

        # Content structure templates (dynamic via PTG in real implementation)
        self.structure_templates = {
            "story": {
                "elements": ["setting", "characters", "conflict", "plot", "resolution"],
                "flow": [
                    "exposition",
                    "rising_action",
                    "climax",
                    "falling_action",
                    "resolution",
                ],
                "patterns": ["hero_journey", "three_act", "freytag_pyramid"],
            },
            "lesson_plan": {
                "elements": [
                    "objectives",
                    "materials",
                    "activities",
                    "assessment",
                    "extension",
                ],
                "flow": ["hook", "instruction", "practice", "assessment", "closure"],
                "patterns": ["gradual_release", "inquiry_based", "direct_instruction"],
            },
            "study_guide": {
                "elements": [
                    "key_concepts",
                    "examples",
                    "practice",
                    "summary",
                    "resources",
                ],
                "flow": [
                    "overview",
                    "detailed_content",
                    "examples",
                    "exercises",
                    "review",
                ],
                "patterns": [
                    "concept_mapping",
                    "question_framework",
                    "spaced_repetition",
                ],
            },
        }

        # Creative prompts for different styles
        self.style_prompts = {
            "conservative": {
                "tone": "formal and traditional",
                "structure": "well-organized and conventional",
                "approach": "proven methods and established patterns",
            },
            "balanced": {
                "tone": "engaging yet professional",
                "structure": "clear with creative elements",
                "approach": "blend of traditional and innovative methods",
            },
            "creative": {
                "tone": "imaginative and expressive",
                "structure": "flexible and innovative",
                "approach": "experimental and artistic methods",
            },
        }

        # Planning heuristics
        self.planning_strategies = {
            "length_based": self._plan_by_length,
            "complexity_based": self._plan_by_complexity,
            "audience_based": self._plan_by_audience,
            "goal_based": self._plan_by_goals,
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

    async def invoke(
        self, workspace: Dict[str, Any], agent_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Main agent invoke method - plans content structure and generates suggestions
        Uses dynamic prompts from Session Manager's PTG
        """
        topic_content = workspace.get("topic_content", "")
        perception_data = workspace.get("perception_analysis", {})

        # Get planning parameters
        topic_mode = workspace.get("topic_mode", "balanced")
        target_length = agent_config.get("target_length", "medium")
        audience = agent_config.get("audience", "general")

        # Generate content plan
        content_plan = await self._create_content_plan(
            topic_content, perception_data, topic_mode, target_length, audience
        )

        # Generate creative suggestions
        suggestions = await self._generate_suggestions(
            topic_content, content_plan, perception_data, topic_mode
        )

        # Create outline
        outline = await self._create_outline(content_plan, suggestions)

        # Generate next steps
        next_steps = await self._generate_next_steps(content_plan, workspace)

        result = {
            "content_plan": content_plan,
            "suggestions": suggestions,
            "outline": outline,
            "next_steps": next_steps,
            "metadata": {
                "planning_strategy": content_plan.get("strategy", "goal_based"),
                "confidence": content_plan.get("confidence", 0.8),
                "timestamp": datetime.now().isoformat(),
            },
        }

        logger.debug(
            f"Planner analysis complete - {len(suggestions)} suggestions, {len(outline)} outline items"
        )
        return result

    async def _create_content_plan(
        self,
        topic_content: str,
        perception_data: Dict[str, Any],
        topic_mode: str,
        target_length: str,
        audience: str,
    ) -> Dict[str, Any]:
        """Create structured content plan based on analysis"""

        # Infer content type from perception data
        content_type = self._infer_content_type(topic_content, perception_data)

        # Select planning strategy
        strategy = self._select_planning_strategy(
            perception_data, target_length, audience
        )

        # Get base structure for content type
        base_structure = self.structure_templates.get(
            content_type, self.structure_templates["story"]
        )

        # Apply planning strategy
        plan = await self.planning_strategies[strategy](
            topic_content,
            perception_data,
            base_structure,
            topic_mode,
            target_length,
            audience,
        )

        plan.update(
            {
                "content_type": content_type,
                "strategy": strategy,
                "mode": topic_mode,
                "target_length": target_length,
                "audience": audience,
                "confidence": 0.8,
            }
        )

        return plan

    def _infer_content_type(
        self, topic_content: str, perception_data: Dict[str, Any]
    ) -> str:
        """Infer content type from text analysis"""
        text_lower = topic_content.lower()

        # Check for educational indicators
        educational_terms = {
            "learn",
            "teach",
            "lesson",
            "study",
            "understand",
            "explain",
            "concept",
        }
        if any(term in text_lower for term in educational_terms):
            # Distinguish between lesson plan and study guide
            if any(
                term in text_lower
                for term in {"plan", "activity", "classroom", "students"}
            ):
                return "lesson_plan"
            else:
                return "study_guide"

        # Check for narrative indicators
        narrative_terms = {
            "story",
            "character",
            "plot",
            "once",
            "happened",
            "adventure",
        }
        pov = perception_data.get("pov", "")
        if any(term in text_lower for term in narrative_terms) or pov in [
            "first",
            "third",
        ]:
            return "story"

        # Default to story if unclear
        return "story"

    def _select_planning_strategy(
        self, perception_data: Dict[str, Any], target_length: str, audience: str
    ) -> str:
        """Select appropriate planning strategy"""

        # Consider text complexity
        token_count = len(perception_data.get("tokens", []))
        entity_count = len(perception_data.get("entities", []))

        if token_count < 50:
            return "length_based"
        elif entity_count > 5:
            return "complexity_based"
        elif audience in ["children", "students", "beginners"]:
            return "audience_based"
        else:
            return "goal_based"

    async def _plan_by_length(
        self,
        topic_content: str,
        perception_data: Dict[str, Any],
        base_structure: Dict[str, Any],
        topic_mode: str,
        target_length: str,
        audience: str,
    ) -> Dict[str, Any]:
        """Plan content based on target length"""

        length_specs = {
            "short": {"sections": 3, "words_per_section": 100, "detail_level": "basic"},
            "medium": {
                "sections": 5,
                "words_per_section": 200,
                "detail_level": "moderate",
            },
            "long": {
                "sections": 7,
                "words_per_section": 300,
                "detail_level": "detailed",
            },
        }

        spec = length_specs.get(target_length, length_specs["medium"])
        elements = base_structure["elements"][: spec["sections"]]

        return {
            "structure": {
                "elements": elements,
                "sections": spec["sections"],
                "target_words": spec["sections"] * spec["words_per_section"],
                "detail_level": spec["detail_level"],
            },
            "flow": base_structure["flow"][: spec["sections"]],
            "patterns": [base_structure["patterns"][0]],  # Use primary pattern
        }

    async def _plan_by_complexity(
        self,
        topic_content: str,
        perception_data: Dict[str, Any],
        base_structure: Dict[str, Any],
        topic_mode: str,
        target_length: str,
        audience: str,
    ) -> Dict[str, Any]:
        """Plan content based on complexity level"""

        entity_count = len(perception_data.get("entities", []))
        character_count = len(perception_data.get("characters", []))

        # High complexity - many entities/characters
        if entity_count > 8 or character_count > 3:
            complexity = "high"
            sections = 6
            detail_level = "comprehensive"
        # Medium complexity
        elif entity_count > 4 or character_count > 1:
            complexity = "medium"
            sections = 4
            detail_level = "moderate"
        # Low complexity
        else:
            complexity = "low"
            sections = 3
            detail_level = "simple"

        return {
            "structure": {
                "elements": base_structure["elements"][:sections],
                "sections": sections,
                "complexity": complexity,
                "detail_level": detail_level,
            },
            "flow": base_structure["flow"][:sections],
            "patterns": base_structure["patterns"][
                :2
            ],  # Use multiple patterns for complexity
        }

    async def _plan_by_audience(
        self,
        topic_content: str,
        perception_data: Dict[str, Any],
        base_structure: Dict[str, Any],
        topic_mode: str,
        target_length: str,
        audience: str,
    ) -> Dict[str, Any]:
        """Plan content based on target audience"""

        audience_specs = {
            "children": {
                "vocabulary": "simple",
                "concepts": "concrete",
                "examples": "familiar",
            },
            "students": {
                "vocabulary": "academic",
                "concepts": "progressive",
                "examples": "educational",
            },
            "adults": {
                "vocabulary": "standard",
                "concepts": "abstract",
                "examples": "practical",
            },
            "experts": {
                "vocabulary": "technical",
                "concepts": "advanced",
                "examples": "specialized",
            },
        }

        spec = audience_specs.get(audience, audience_specs["adults"])

        # Adjust structure based on audience
        if audience in ["children", "students"]:
            sections = 4
            patterns = [base_structure["patterns"][0]]  # Simple pattern
        else:
            sections = 5
            patterns = base_structure["patterns"][:2]  # More sophisticated patterns

        return {
            "structure": {
                "elements": base_structure["elements"][:sections],
                "sections": sections,
                "audience_specs": spec,
            },
            "flow": base_structure["flow"][:sections],
            "patterns": patterns,
        }

    async def _plan_by_goals(
        self,
        topic_content: str,
        perception_data: Dict[str, Any],
        base_structure: Dict[str, Any],
        topic_mode: str,
        target_length: str,
        audience: str,
    ) -> Dict[str, Any]:
        """Plan content based on inferred goals"""

        # Infer goals from content and perception data
        tone = perception_data.get("tone", "neutral")
        pov = perception_data.get("pov", "unknown")

        # Default goal-based structure
        if tone == "questioning":
            goal = "exploration"
            focus = "discovery"
        elif tone in ["positive", "negative"]:
            goal = "persuasion"
            focus = "emotional_impact"
        elif pov in ["first", "second"]:
            goal = "engagement"
            focus = "personal_connection"
        else:
            goal = "information"
            focus = "clarity"

        return {
            "structure": {
                "elements": base_structure["elements"],
                "goal": goal,
                "focus": focus,
                "sections": len(base_structure["elements"]),
            },
            "flow": base_structure["flow"],
            "patterns": base_structure["patterns"],
        }

    async def _generate_suggestions(
        self,
        topic_content: str,
        content_plan: Dict[str, Any],
        perception_data: Dict[str, Any],
        topic_mode: str,
    ) -> List[Dict[str, Any]]:
        """Generate creative suggestions for content development"""

        suggestions = []
        content_type = content_plan.get("content_type", "story")
        style = self.style_prompts.get(topic_mode, self.style_prompts["balanced"])

        # Character suggestions (if applicable)
        if content_type == "story":
            suggestions.extend(
                await self._generate_character_suggestions(perception_data, style)
            )

        # Structure suggestions
        suggestions.extend(
            await self._generate_structure_suggestions(content_plan, style)
        )

        # Style suggestions
        suggestions.extend(
            await self._generate_style_suggestions(perception_data, style)
        )

        # Enhancement suggestions
        suggestions.extend(
            await self._generate_enhancement_suggestions(topic_content, content_plan)
        )

        # Use LLM for additional suggestions if available
        if self.llm_provider:
            try:
                llm_suggestions = await self._generate_llm_suggestions(
                    topic_content, content_plan, perception_data, topic_mode
                )
                suggestions.extend(llm_suggestions)
            except Exception as e:
                logger.warning(f"LLM suggestion generation failed: {e}")

        return suggestions[:20]  # Limit to top 20 suggestions

    async def _generate_character_suggestions(
        self, perception_data: Dict[str, Any], style: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate character development suggestions"""
        suggestions = []
        characters = perception_data.get("characters", [])

        for character in characters:
            name = character["name"]
            traits = character.get("traits", [])

            if not traits:
                suggestions.append(
                    {
                        "type": "character_development",
                        "priority": "high",
                        "suggestion": f"Develop personality traits for {name}",
                        "details": f"Consider adding distinctive characteristics that align with {style['tone']} tone",
                        "implementation": f"Add descriptive details about {name}'s appearance, mannerisms, or background",
                    }
                )

            suggestions.append(
                {
                    "type": "character_arc",
                    "priority": "medium",
                    "suggestion": f"Create character arc for {name}",
                    "details": f"Plan how {name} will change or grow throughout the story",
                    "implementation": f"Consider {name}'s goals, obstacles, and transformation",
                }
            )

        return suggestions

    async def _generate_structure_suggestions(
        self, content_plan: Dict[str, Any], style: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate structural suggestions"""
        suggestions = []
        structure = content_plan.get("structure", {})
        elements = structure.get("elements", [])

        for element in elements:
            suggestions.append(
                {
                    "type": "structure_element",
                    "priority": "medium",
                    "suggestion": f"Develop the {element} section",
                    "details": f"Create {style['structure']} approach to {element}",
                    "implementation": f"Focus on {element} with {style['approach']}",
                }
            )

        # Pattern-based suggestions
        patterns = content_plan.get("patterns", [])
        if patterns:
            pattern = patterns[0]
            suggestions.append(
                {
                    "type": "narrative_pattern",
                    "priority": "high",
                    "suggestion": f"Follow {pattern} structure",
                    "details": f"Organize content using the {pattern} framework",
                    "implementation": f"Structure sections according to {pattern} principles",
                }
            )

        return suggestions

    async def _generate_style_suggestions(
        self, perception_data: Dict[str, Any], style: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate style and tone suggestions"""
        suggestions = []
        current_tone = perception_data.get("tone", "neutral")
        current_pov = perception_data.get("pov", "unknown")

        # Tone enhancement
        if current_tone != style["tone"]:
            suggestions.append(
                {
                    "type": "tone_adjustment",
                    "priority": "medium",
                    "suggestion": f"Adjust tone to be more {style['tone']}",
                    "details": f"Current tone is {current_tone}, consider shifting towards {style['tone']}",
                    "implementation": "Revise word choice and sentence structure to match target tone",
                }
            )

        # POV consistency
        if current_pov == "mixed":
            suggestions.append(
                {
                    "type": "pov_consistency",
                    "priority": "high",
                    "suggestion": "Maintain consistent point of view",
                    "details": "Current text uses mixed POV, choose one perspective and stick with it",
                    "implementation": "Review and revise to use consistent first, second, or third person",
                }
            )

        return suggestions

    async def _generate_enhancement_suggestions(
        self, topic_content: str, content_plan: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate content enhancement suggestions"""
        suggestions = []

        # Length analysis
        word_count = len(topic_content.split())
        target_words = content_plan.get("structure", {}).get("target_words", 500)

        if word_count < target_words * 0.5:
            suggestions.append(
                {
                    "type": "content_expansion",
                    "priority": "high",
                    "suggestion": "Expand content to meet target length",
                    "details": f"Current: {word_count} words, Target: {target_words} words",
                    "implementation": "Add more details, examples, or sections",
                }
            )
        elif word_count > target_words * 1.5:
            suggestions.append(
                {
                    "type": "content_reduction",
                    "priority": "medium",
                    "suggestion": "Consider condensing content",
                    "details": f"Current: {word_count} words, Target: {target_words} words",
                    "implementation": "Remove redundant content or combine similar sections",
                }
            )

        return suggestions

    async def _generate_llm_suggestions(
        self,
        topic_content: str,
        content_plan: Dict[str, Any],
        perception_data: Dict[str, Any],
        topic_mode: str,
    ) -> List[Dict[str, Any]]:
        """Use LLM to generate additional creative suggestions"""
        if not self.llm_provider:
            return []

        prompt = f"""
        As a creative content advisor, analyze this content and provide suggestions:
        
        Content: {topic_content[:800]}
        
        Plan: {content_plan.get('content_type', 'story')} in {topic_mode} mode
        Analysis: POV={perception_data.get('pov')}, Tone={perception_data.get('tone')}
        
        Provide 3-5 specific, actionable suggestions for improvement.
        Focus on creativity, engagement, and structural enhancement.
        Format as JSON list with type, priority, suggestion, details, implementation.
        """

        try:
            response = await self.llm_provider.invoke(prompt)
            # Parse JSON response (simplified for now)
            return [
                {"type": "llm_generated", "suggestion": response, "priority": "medium"}
            ]
        except Exception as e:
            logger.error(f"LLM suggestion generation failed: {e}")
            return []

    async def _create_outline(
        self, content_plan: Dict[str, Any], suggestions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Create structured outline based on plan and suggestions"""
        outline = []
        structure = content_plan.get("structure", {})
        elements = structure.get("elements", [])
        flow = content_plan.get("flow", [])

        for i, element in enumerate(elements):
            # Get corresponding flow stage
            flow_stage = flow[i] if i < len(flow) else element

            # Find relevant suggestions for this element
            relevant_suggestions = [
                s
                for s in suggestions
                if element.lower() in s.get("suggestion", "").lower()
                or element.lower() in s.get("details", "").lower()
            ]

            outline_item = {
                "section": element,
                "flow_stage": flow_stage,
                "order": i + 1,
                "suggestions": relevant_suggestions[:3],  # Top 3 relevant suggestions
                "estimated_length": structure.get("target_words", 500) // len(elements),
                "key_points": self._generate_key_points(element, content_plan),
            }

            outline.append(outline_item)

        return outline

    def _generate_key_points(
        self, element: str, content_plan: Dict[str, Any]
    ) -> List[str]:
        """Generate key points for an outline element"""
        content_type = content_plan.get("content_type", "story")

        key_points_map = {
            "story": {
                "setting": ["Time period", "Location", "Atmosphere"],
                "characters": [
                    "Main character",
                    "Supporting characters",
                    "Relationships",
                ],
                "conflict": ["Central problem", "Stakes", "Obstacles"],
                "plot": ["Key events", "Rising tension", "Turning points"],
                "resolution": ["Conflict resolution", "Character growth", "Conclusion"],
            },
            "lesson_plan": {
                "objectives": ["Learning goals", "Outcomes", "Assessment criteria"],
                "materials": ["Required resources", "Technology needs", "Handouts"],
                "activities": ["Main instruction", "Student practice", "Group work"],
                "assessment": ["Formative checks", "Summative evaluation", "Feedback"],
                "extension": ["Advanced activities", "Enrichment", "Connections"],
            },
            "study_guide": {
                "key_concepts": ["Main ideas", "Definitions", "Principles"],
                "examples": ["Concrete instances", "Case studies", "Applications"],
                "practice": ["Exercises", "Problems", "Scenarios"],
                "summary": ["Key takeaways", "Review points", "Connections"],
                "resources": ["Further reading", "References", "Tools"],
            },
        }

        type_map = key_points_map.get(content_type, key_points_map["story"])
        return type_map.get(
            element, ["Key aspects", "Important details", "Relevant information"]
        )

    async def _generate_next_steps(
        self, content_plan: Dict[str, Any], workspace: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate actionable next steps for content development"""
        next_steps = []

        # Current content status
        current_content = workspace.get("topic_content", "")
        word_count = len(current_content.split()) if current_content else 0
        target_words = content_plan.get("structure", {}).get("target_words", 500)

        # Step 1: Content development priority
        if word_count < 50:
            next_steps.append(
                {
                    "step": 1,
                    "action": "Begin content creation",
                    "description": "Start writing the main content based on the outline",
                    "priority": "high",
                    "estimated_time": "30-60 minutes",
                }
            )
        elif word_count < target_words * 0.7:
            next_steps.append(
                {
                    "step": 1,
                    "action": "Expand existing content",
                    "description": "Add more details to reach target length",
                    "priority": "high",
                    "estimated_time": "20-40 minutes",
                }
            )
        else:
            next_steps.append(
                {
                    "step": 1,
                    "action": "Review and refine content",
                    "description": "Polish existing content for quality and flow",
                    "priority": "medium",
                    "estimated_time": "15-30 minutes",
                }
            )

        # Step 2: Structural improvements
        next_steps.append(
            {
                "step": 2,
                "action": "Implement structural suggestions",
                "description": "Apply the highest priority structural recommendations",
                "priority": "medium",
                "estimated_time": "15-25 minutes",
            }
        )

        # Step 3: Style and tone
        next_steps.append(
            {
                "step": 3,
                "action": "Enhance style and tone",
                "description": f"Adjust content to match {content_plan.get('mode', 'balanced')} style",
                "priority": "medium",
                "estimated_time": "10-20 minutes",
            }
        )

        # Step 4: Final review
        next_steps.append(
            {
                "step": 4,
                "action": "Final review and editing",
                "description": "Proofread and make final adjustments",
                "priority": "low",
                "estimated_time": "10-15 minutes",
            }
        )

        return next_steps


# Factory function for agent creation
async def create_planner_generator_agent(
    config: Dict[str, Any], llm_provider=None
) -> PlannerGeneratorAgent:
    """Create and initialize planner generator agent"""
    return PlannerGeneratorAgent(config, llm_provider)
