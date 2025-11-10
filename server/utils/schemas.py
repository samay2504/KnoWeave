"""
Pydantic schemas for data validation and serialization
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

# Try to import pydantic v2 first, fall back to v1
try:
    from pydantic import BaseModel, Field, ConfigDict
    from pydantic import validator, field_validator

    PYDANTIC_V2 = True
except ImportError:
    try:
        from pydantic import BaseModel, Field
        from pydantic import validator

        PYDANTIC_V2 = False
        field_validator = validator  # Alias for compatibility
    except ImportError:
        # Fallback to dataclasses if pydantic not available
        BaseModel = object
        Field = lambda default=None, **kwargs: default
        validator = lambda *args, **kwargs: lambda f: f
        field_validator = validator
        PYDANTIC_V2 = False


class TopicType(str, Enum):
    """Supported topic types"""

    STORY = "story"
    LESSON_PLAN = "lesson_plan"
    STUDY_GUIDE = "study_guide"
    ARTICLE = "article"
    RESEARCH = "research"
    OTHER = "other"


class SuggestionMode(str, Enum):
    """Suggestion modes"""

    ON_DEMAND = "on_demand"
    IDLE_SMART = "idle_smart"
    PROACTIVE = "proactive"


class BranchType(str, Enum):
    """Branch generation types"""

    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    CREATIVE = "creative"


# Base schemas
if BaseModel != object:

    class BaseSchema(BaseModel):
        """Base schema with common configuration"""
        if PYDANTIC_V2:
            model_config = ConfigDict(
                extra="forbid", validate_assignment=True, use_enum_values=True
            )
        else:
            class Config:
                extra = "forbid"
                validate_assignment = True
                use_enum_values = True

else:

    @dataclass
    class BaseSchema:
        """Fallback base schema using dataclasses"""

        def dict(self, **kwargs):
            """Convert to dictionary for compatibility"""
            from dataclasses import asdict

            return asdict(self)

        def json(self, **kwargs):
            """Convert to JSON string"""
            import json

            return json.dumps(self.dict())

        @classmethod
        def parse_obj(cls, obj):
            """Parse from dictionary"""
            if isinstance(obj, dict):
                return cls(**obj)
            return obj


# Event schemas
class EventSchema(BaseSchema):
    """Schema for story/topic events"""

    id: str = Field(..., description="Unique event identifier")
    summary: str = Field(..., description="Brief event summary")
    actor: Optional[str] = Field(None, description="Primary actor in the event")
    time: Optional[str] = Field(None, description="Temporal reference")
    confidence: float = Field(0.9, ge=0.0, le=1.0, description="Event confidence score")
    embedding: Optional[List[float]] = Field(None, description="Event embedding vector")


class CharacterSchema(BaseSchema):
    """Schema for character information"""

    name: str = Field(..., description="Character name")
    traits: List[str] = Field(default_factory=list, description="Character traits")
    appearance: Optional[str] = Field(None, description="Character appearance")
    background: Optional[str] = Field(None, description="Character background")
    relationships: Dict[str, str] = Field(
        default_factory=dict, description="Character relationships"
    )


# Projection schemas
class ProjectionSchema(BaseSchema):
    """Schema for story/topic projections (branches)"""

    title: str = Field(..., description="Branch title")
    events: List[EventSchema] = Field(
        default_factory=list, description="Events in this branch"
    )
    paragraph: str = Field("", description="Textual representation of the branch")  # Made optional with default
    flags: Dict[str, List[str]] = Field(
        default_factory=dict, description="Flags for unverified facts, etc."
    )
    branch_type: BranchType = Field(
        BranchType.BALANCED, description="Type of branch generation"
    )
    score: Optional[float] = Field(
        None, ge=0.0, le=10.0, description="Branch quality score"
    )
    
    class Config:
        extra = "ignore"  # Ignore extra fields like 'meta' from LLM


# Session and workspace schemas
class PolicySchema(BaseSchema):
    """Schema for session policies"""

    max_backtrack: int = Field(2, ge=0, le=10, description="Maximum backtrack depth")
    suggestion_mode: SuggestionMode = Field(
        SuggestionMode.ON_DEMAND, description="When to suggest"
    )
    max_branches: int = Field(3, ge=1, le=5, description="Maximum branches to generate")
    preserve_characters: bool = Field(
        True, description="Preserve character consistency"
    )
    preserve_pov: bool = Field(True, description="Preserve point of view")
    strict_mode: bool = Field(False, description="Strict fact checking mode")
    include_morals: bool = Field(False, description="Include moral lessons")


class MetadataSchema(BaseSchema):
    """Schema for session metadata (allows extra fields for forward compatibility)"""
    title: Optional[str] = Field(None, description="Session title")
    description: Optional[str] = Field(None, description="Session description")
    tags: List[str] = Field(default_factory=list, description="Session tags")
    word_count: int = Field(0, ge=0, description="Current word count")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")
    user_notes: str = Field("", description="User notes")

    class Config:
        extra = "allow"


class WorkspaceSchema(BaseSchema):
    """Schema for the main workspace/session"""

    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User identifier")
    topic: TopicType = Field(TopicType.STORY, description="Topic type")
    topic_descriptor: Optional[str] = Field(
        None, description="Topic-specific descriptor"
    )
    topic_content: str = Field(
        "", description="Main content (story_so_far or topic content)"
    )
    events: List[EventSchema] = Field(
        default_factory=list, description="Timeline of events"
    )
    characters: Dict[str, CharacterSchema] = Field(
        default_factory=dict, description="Character profiles"
    )
    kb_triples: List[List[str]] = Field(
        default_factory=list, description="Knowledge base triples"
    )
    projections: Dict[str, Optional[ProjectionSchema]] = Field(
        default_factory=dict, description="Generated projections"
    )
    history: List[Dict[str, Any]] = Field(
        default_factory=list, description="Action history"
    )
    graph: Dict[str, Any] = Field(
        default_factory=dict, description="Knowledge graph representation"
    )
    policy: PolicySchema = Field(
        default_factory=PolicySchema, description="Session policies"
    )
    metadata: MetadataSchema = Field(
        default_factory=MetadataSchema, description="Session metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    last_modified: datetime = Field(
        default_factory=datetime.utcnow, description="Last modification timestamp"
    )


# API request/response schemas
class NewSessionRequest(BaseSchema):
    """Request to create a new session"""

    user_id: str = Field(..., description="User identifier")
    topic: TopicType = Field(TopicType.STORY, description="Topic type")
    topic_descriptor: Optional[str] = Field(
        None, description="Topic-specific descriptor"
    )
    initial_content: str = Field("", description="Initial content")
    policy: Optional[PolicySchema] = Field(None, description="Session policies")


class SuggestRequest(BaseSchema):
    """Request to generate suggestions"""

    mode: SuggestionMode = Field(
        SuggestionMode.ON_DEMAND, description="Suggestion mode"
    )
    options: Dict[str, Any] = Field(
        default_factory=dict, description="Additional options"
    )
    constraints: Dict[str, Any] = Field(
        default_factory=dict, description="Generation constraints"
    )


class AcceptBranchRequest(BaseSchema):
    """Request to accept a branch"""

    branch_id: str = Field(..., description="Branch identifier to accept")
    merge_strategy: str = Field("append", description="How to merge the branch")


class BacktrackRequest(BaseSchema):
    """Request to backtrack to a previous state"""

    node_id: str = Field(..., description="Node to backtrack to")
    preserve_branches: bool = Field(
        True, description="Whether to preserve existing branches"
    )


# Response schemas
class SessionResponse(BaseSchema):
    """Response containing session information"""

    session_id: str = Field(..., description="Session identifier")
    workspace: WorkspaceSchema = Field(..., description="Current workspace state")
    status: str = Field("ok", description="Response status")
    message: Optional[str] = Field(None, description="Status message")


class SuggestionsResponse(BaseSchema):
    """Response containing generated suggestions"""

    session_id: str = Field(..., description="Session identifier")
    projections: Dict[str, Optional[ProjectionSchema]] = Field(
        ..., description="Generated projections"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Generation metadata"
    )
    status: str = Field("ok", description="Response status")


class BacktrackResponse(BaseSchema):
    """Response for backtrack operation"""

    session_id: str = Field(..., description="Session identifier")
    new_projections: Dict[str, Optional[ProjectionSchema]] = Field(
        default_factory=dict, description="New projections after backtrack"
    )
    reverted_to: str = Field(..., description="Node that was reverted to")
    status: str = Field("ok", description="Response status")


class SnapshotResponse(BaseSchema):
    """Response containing workspace snapshot"""

    session_id: str = Field(..., description="Session identifier")
    snapshot: Dict[str, Any] = Field(..., description="Workspace snapshot")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Snapshot timestamp"
    )


# Graph schemas
class GraphNodeSchema(BaseSchema):
    """Schema for graph nodes"""

    id: str = Field(..., description="Node identifier")
    type: str = Field(..., description="Node type (event/entity)")
    summary: str = Field(..., description="Node summary")
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Node properties"
    )
    embedding: Optional[List[float]] = Field(None, description="Node embedding")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Node confidence")
    timestamp: Optional[str] = Field(None, description="Node timestamp")


class GraphEdgeSchema(BaseSchema):
    """Schema for graph edges"""

    from_node: str = Field(..., description="Source node ID")
    to_node: str = Field(..., description="Target node ID")
    type: str = Field(..., description="Edge type")
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Edge properties"
    )
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Edge confidence")


# Error schemas
class ErrorResponse(BaseSchema):
    """Error response schema"""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    status_code: int = Field(500, description="HTTP status code")


# Agent output schemas
class PerceptionOutput(BaseSchema):
    """Output from perception agent"""

    tokens: List[str] = Field(default_factory=list, description="Extracted tokens")
    pos_tags: List[str] = Field(default_factory=list, description="POS tags")
    entities: List[Dict[str, Any]] = Field(
        default_factory=list, description="Named entities"
    )
    tone: Optional[str] = Field(None, description="Detected tone")
    pov: Optional[str] = Field(None, description="Point of view")
    summary: str = Field("", description="Content summary")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class VerificationOutput(BaseSchema):
    """Output from verification agent"""

    grammar_score: float = Field(
        1.0, ge=0.0, le=1.0, description="Grammar quality score"
    )
    pov_consistent: bool = Field(True, description="POV consistency check")
    character_consistent: bool = Field(True, description="Character consistency check")
    verified_facts: List[str] = Field(
        default_factory=list, description="Verified facts"
    )
    unverified_facts: List[str] = Field(
        default_factory=list, description="Unverified facts"
    )
    violations: List[str] = Field(
        default_factory=list, description="Consistency violations"
    )
    suggestions: List[str] = Field(
        default_factory=list, description="Improvement suggestions"
    )


class EvaluationOutput(BaseSchema):
    """Output from evaluation agent"""

    coherence_score: float = Field(0.0, ge=0.0, le=10.0, description="Coherence score")
    causal_strength: float = Field(0.0, ge=0.0, le=1.0, description="Causal strength")
    character_consistency: float = Field(
        1.0, ge=0.0, le=1.0, description="Character consistency score"
    )
    factual_accuracy: float = Field(
        1.0, ge=0.0, le=1.0, description="Factual accuracy score"
    )
    novelty_score: float = Field(0.5, ge=0.0, le=1.0, description="Novelty score")
    acceptability_score: float = Field(
        0.0, ge=0.0, le=10.0, description="Overall acceptability score"
    )
    ranking: int = Field(1, ge=1, description="Ranking among alternatives")


# Validation functions
if BaseModel != object and hasattr(field_validator, "__call__"):

    @field_validator("topic_content", mode="before")
    @classmethod
    def validate_topic_content(cls, v):
        """Validate topic content is not too long"""
        if isinstance(v, str) and len(v) > 100000:  # 100k character limit
            raise ValueError("Topic content too long (max 100k characters)")
        return v

    @field_validator("events", mode="before")
    @classmethod
    def validate_events_list(cls, v):
        """Validate events list is not too long"""
        if isinstance(v, list) and len(v) > 1000:  # 1000 events limit
            raise ValueError("Too many events (max 1000)")
        return v
