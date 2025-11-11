"""
API Routes - Human-AI Co-Creation System
PRODUCTION-GRADE IMPLEMENTATION with clean structure and proper error handling
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, Depends, Body, Request
from fastapi.responses import JSONResponse

from agents.session_manager import SessionManager
from utils.schemas import WorkspaceSchema, ProjectionSchema, PerceptionOutput
from utils.logging_cfg import get_api_logger
from server_config import ServerConfig

# Initialize logger
logger = get_api_logger()

# Create router - SINGLE INSTANCE
router = APIRouter(prefix="/api/session", tags=["session"])

# ============================================================================
# GLOBAL STATE - Injected from app.py for production data sharing
# ============================================================================

_global_agents: Optional[Dict[str, Any]] = None
_global_session_manager: Optional[SessionManager] = None


def set_global_dependencies(agents_dict: Dict[str, Any], session_mgr: SessionManager) -> None:
    """
    Production fix: Inject global agent instances from app.py
    
    This ensures routes use THE SAME agent instances that hold actual data,
    not new empty instances. Critical for graph visualization and analytics.
    
    Args:
        agents_dict: Dictionary of initialized agents from app.py
        session_mgr: Initialized session manager from app.py
    """
    global _global_agents, _global_session_manager
    _global_agents = agents_dict
    _global_session_manager = session_mgr
    logger.info(f"✅ Global dependencies injected: {list(agents_dict.keys())}")


# ============================================================================
# DEPENDENCY: Get Session Manager
# ============================================================================

async def get_session_manager() -> SessionManager:
    """
    Get session manager - prefers global instance, creates new as fallback
    
    Returns:
        SessionManager: Active session manager instance
        
    Raises:
        HTTPException: If session manager cannot be obtained
    """
    # Prefer global instance (has actual data)
    if _global_session_manager:
        return _global_session_manager
    
    # Fallback: create new instance (won't have existing session data)
    logger.warning("⚠️  Creating new SessionManager - existing data may not be accessible")
    config = ServerConfig()
    return SessionManager(config.model_dump() if hasattr(config, 'model_dump') else dict(config))


# ============================================================================
# SESSION ENDPOINTS
# ============================================================================

@router.post("/new", response_model=Dict[str, Any])
async def create_session(request: Request) -> Dict[str, Any]:
    """
    Create a new co-creation session
    
    Request Body:
        - topic: str (required) - Session topic/title
        - topic_descriptor: str - Domain descriptor (default: "story")
        - user_id: str - User identifier (from auth or "default_user")
        - initial_content: str - Starting content
        - policy: dict - Session policy configuration
        
    Returns:
        Dict with session_id, status, workspace data
    """
    try:
        request_data = await request.json()
        
        # Extract parameters with defaults
        topic = request_data.get("topic")
        mode = request_data.get("topic_descriptor") or request_data.get("mode", "story")
        user_id = request_data.get("user_id")
        initial_content = request_data.get("initial_content", "")
        policy = request_data.get("policy")
        
        # Try to get user from authentication
        if not user_id:
            try:
                from routes.auth_routes import get_current_user_from_request
                user = get_current_user_from_request(request)
                user_id = user.get("user_id") if user else "default_user"
            except Exception:
                user_id = "default_user"
        
        # Validate required fields
        if not topic:
            raise HTTPException(status_code=400, detail="Topic is required")
        
        # Generate session ID
        session_id = f"session_{uuid.uuid4().hex[:16]}"
        logger.info(f"Creating session {session_id} for user {user_id}, topic: {topic}")
        
        # Get session manager
        session_manager = await get_session_manager()
        
        # Create session request object
        from utils.schemas import NewSessionRequest, PolicySchema
        policy_obj = PolicySchema(**policy) if policy else PolicySchema()
        
        request_obj = NewSessionRequest(
            user_id=user_id,
            topic=topic,
            topic_descriptor=mode,
            initial_content=initial_content,
            policy=policy_obj,
        )
        
        # Create session
        workspace = await session_manager.create_session(request_obj)
        
        return {
            "session_id": workspace.session_id,
            "status": "created",
            "workspace": workspace.model_dump() if hasattr(workspace, 'model_dump') else workspace.__dict__,
            "message": "Session created successfully",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.get("/{session_id}", response_model=Dict[str, Any])
async def get_session(session_id: str) -> Dict[str, Any]:
    """
    Get session workspace data
    
    Args:
        session_id: Session identifier
        
    Returns:
        Dict with session data and workspace
    """
    try:
        logger.info(f"Retrieving session {session_id}")
        
        session_manager = await get_session_manager()
        workspace = await session_manager.get_session(session_id)
        
        if not workspace:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "session_id": session_id,
            "workspace": workspace.model_dump() if hasattr(workspace, 'model_dump') else workspace.__dict__,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/graph", response_model=Dict[str, Any])
async def get_knowledge_graph(session_id: str) -> Dict[str, Any]:
    """
    Get knowledge graph for session - PRODUCTION VERSION
    
    This endpoint uses global agents from app.py to ensure it accesses
    the actual graph data that was built during content processing.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Dict with nodes, edges, and triples
    """
    try:
        logger.info(f"📊 Getting knowledge graph for session {session_id}")
        
        # PRODUCTION FIX: Use global agents with actual data
        if _global_agents and _global_agents.get("graph_manager"):
            graph_manager = _global_agents["graph_manager"]
            session_manager = _global_session_manager
            logger.info("✅ Using global graph_manager instance with actual data")
        else:
            # Fallback: create new instance (won't have graph data)
            logger.warning("⚠️  Global agents not available - graph may be empty")
            session_manager = await get_session_manager()
            
            # Try to get graph manager from agents
            if _global_agents:
                graph_manager = _global_agents.get("graph_manager")
            else:
                # Last resort: create new instance
                from agents.graph_manager_agent import GraphManagerAgent
                config = ServerConfig()
                graph_manager = GraphManagerAgent(
                    config.model_dump() if hasattr(config, 'model_dump') else dict(config)
                )
                logger.warning("⚠️  Created new GraphManagerAgent - data may be missing")
        
        # Load workspace
        workspace = await session_manager.get_session(session_id)
        if not workspace:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get graph structure
        nodes = []
        edges = []
        triples = []
        
        if graph_manager:
            try:
                # Call method that returns actual graph data
                if hasattr(graph_manager, 'get_graph_structure'):
                    nodes, edges = await graph_manager.get_graph_structure(workspace.session_id)
                    logger.info(f"✅ Graph retrieved: {len(nodes)} nodes, {len(edges)} edges")
                else:
                    logger.error("❌ graph_manager missing get_graph_structure method")
                    raise AttributeError("GraphManagerAgent missing get_graph_structure method")
                    
            except Exception as e:
                logger.error(f"❌ Graph retrieval error: {e}")
                # Don't fail completely - return empty graph
                nodes = []
                edges = []
        
        # Get triples from workspace
        if hasattr(workspace, "kb_triples"):
            triples = workspace.kb_triples
        
        return {
            "session_id": session_id,
            "graph": {
                "nodes": nodes,
                "edges": edges,
                "triples": triples
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Graph endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}", response_model=Dict[str, Any])
async def delete_session(session_id: str) -> Dict[str, Any]:
    """
    Delete a session
    
    Args:
        session_id: Session identifier
        
    Returns:
        Dict with deletion confirmation
    """
    try:
        logger.info(f"Deleting session {session_id}")
        
        session_manager = await get_session_manager()
        success = await session_manager.delete_session(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "session_id": session_id,
            "status": "deleted",
            "message": "Session deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session deletion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "session-routes",
        "global_agents_available": _global_agents is not None,
        "global_session_manager_available": _global_session_manager is not None
    }


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = ["router", "set_global_dependencies"]
