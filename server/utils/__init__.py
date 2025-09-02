# Utils package - lightweight imports to avoid heavy dependencies
from .chunker import TextChunker, TextChunk, chunk_text, chunk_text_with_metadata

# Import embeddings with graceful fallback handling
from .embeddings import (
    EmbeddingsProvider,
    EmbeddingResult,
    create_embeddings_provider,
    cosine_similarity_score,
    get_embeddings,
)

from .schemas import (
    BaseSchema,
    TopicType,
    SuggestionMode,
    BranchType,
    EventSchema,
    CharacterSchema,
    ProjectionSchema,
    PolicySchema,
    MetadataSchema,
    WorkspaceSchema,
    NewSessionRequest,
    SuggestRequest,
    AcceptBranchRequest,
    BacktrackRequest,
    SessionResponse,
    SuggestionsResponse,
    BacktrackResponse,
    SnapshotResponse,
    GraphNodeSchema,
    GraphEdgeSchema,
    ErrorResponse,
    PerceptionOutput,
    VerificationOutput,
    EvaluationOutput,
)
from .logging_cfg import (
    setup_logging,
    get_logger,
    get_agent_logger,
    get_db_logger,
    get_api_logger,
    get_llm_logger,
)

__all__ = [
    # Chunker
    "TextChunker",
    "TextChunk",
    "chunk_text",
    "chunk_text_with_metadata",
    # Embeddings
    "EmbeddingsProvider",
    "EmbeddingResult",
    "create_embeddings_provider",
    "cosine_similarity_score",
    "get_embeddings",
    # Schemas
    "BaseSchema",
    "TopicType",
    "SuggestionMode",
    "BranchType",
    "EventSchema",
    "CharacterSchema",
    "ProjectionSchema",
    "PolicySchema",
    "MetadataSchema",
    "WorkspaceSchema",
    "NewSessionRequest",
    "SuggestRequest",
    "AcceptBranchRequest",
    "BacktrackRequest",
    "SessionResponse",
    "SuggestionsResponse",
    "BacktrackResponse",
    "SnapshotResponse",
    "GraphNodeSchema",
    "GraphEdgeSchema",
    "ErrorResponse",
    "PerceptionOutput",
    "VerificationOutput",
    "EvaluationOutput",
    # Logging
    "setup_logging",
    "get_logger",
    "get_agent_logger",
    "get_db_logger",
    "get_api_logger",
    "get_llm_logger",
]
