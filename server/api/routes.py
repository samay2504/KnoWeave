
from fastapi import FastAPI, APIRouter
from fastapi.openapi.utils import get_openapi


app = FastAPI()

# Create router
router = APIRouter(prefix="/api/session", tags=["co-creation"])

# Mount the co-creation router
app.include_router(router)

"""
API Routes - Human-AI Co-Creation System
REST API endpoints for the server
"""

from fastapi import APIRouter, HTTPException, Depends, Body, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, List
import uuid
import logging
from datetime import datetime

# Fix relative imports
from agents.session_manager import SessionManager
from utils.schemas import WorkspaceSchema, ProjectionSchema, PerceptionOutput
from utils.logging_cfg import get_api_logger
from server_config import ServerConfig


# Create AgentOrchestrator class since it doesn't exist
class AgentOrchestrator:
    def __init__(
        self, config, database_client=None, graph_client=None, llm_provider=None
    ):
        self.config = config
        self.database_client = database_client
        self.graph_client = graph_client
        self.llm_provider = llm_provider
        self._session_manager = None

    async def get_session_manager(self):
        if self._session_manager is None:
            self._session_manager = SessionManager(self.config)
        return self._session_manager

    async def get_perception_agent(self):
        try:
            from agents.perception_agent import PerceptionAgent
            return PerceptionAgent(self.config)
        except Exception as e:
            logger.warning(f"Failed to load PerceptionAgent: {e}")
            return None

    async def get_planner_agent(self):
        try:
            from agents.planner_generator_agent import PlannerGeneratorAgent

            return PlannerGeneratorAgent(self.config, self.llm_provider)
        except Exception as e:
            logger.warning(f"Failed to load PlannerGeneratorAgent: {e}")
            return None

    async def get_verifier_agent(self):
        try:
            from agents.verifier_agent import VerifierAgent

            return VerifierAgent(self.config, self.llm_provider)
        except Exception as e:
            logger.warning(f"Failed to load VerifierAgent: {e}")
            return None

    async def get_graph_manager(self):
        try:
            from agents.graph_manager_agent import GraphManagerAgent

            return GraphManagerAgent(self.config, self.graph_client)
        except Exception as e:
            logger.warning(f"Failed to load GraphManagerAgent: {e}")
            return None

    async def run_complete_workflow(self, session_id: str, user_input: str = ""):
        try:
            session_manager = await self.get_session_manager()
            workspace = await session_manager.get_session(session_id)
            if not workspace:
                return {"error": "Session not found"}

            # Simple workflow implementation
            result = {
                "session_id": session_id,
                "message": "Workflow completed successfully",
                "workspace": (
                    workspace.dict() if hasattr(workspace, "dict") else workspace
                ),
                "user_input": user_input,
            }

            # Try to run agents if available
            perception_agent = await self.get_perception_agent()
            if perception_agent:
                try:
                    analysis = await perception_agent.invoke(workspace, {})
                    result["analysis"] = analysis
                except Exception as e:
                    logger.warning(f"Perception agent failed: {e}")

            return result
        except Exception as e:
            return {"error": f"Workflow failed: {str(e)}"}


logger = get_api_logger()

# Create router
router = APIRouter(prefix="/api/session", tags=["co-creation"])


# Dependency to get orchestrator
async def get_orchestrator() -> AgentOrchestrator:
    """Get agent orchestrator instance"""
    config = ServerConfig()

    # Initialize clients based on configuration
    database_client = None
    graph_client = None
    llm_provider = None

    try:
        # Database client
        if config.database_mode == "arangodb":
            from db.arango_client import create_arango_client

            database_client = await create_arango_client(config.get_database_config())
        elif config.database_mode == "mongodb":
            from db.mongo_client import create_mongo_client

            database_client = await create_mongo_client(config.get_database_config())
        else:
            from db.json_fallback import create_json_fallback_client

            # Use default path for fallback client
            database_client = create_json_fallback_client("data/backups")

        # Graph client (same as database for now)
        graph_client = database_client

        # LLM provider
        from llm_provider import AsyncLLMProvider

        llm_provider = AsyncLLMProvider(config)

    except Exception as e:
        logger.warning(f"Client initialization failed, using fallbacks: {e}")
        # Use JSON fallback for everything
        from db.json_fallback import create_json_fallback_client


    database_client = create_json_fallback_client("data/backups")
    graph_client = database_client

    return AgentOrchestrator(
        config=config.dict(),
        database_client=database_client,
        graph_client=graph_client,
        llm_provider=llm_provider,
    )

@router.get("/{session_id}", response_model=Dict[str, Any])
async def get_session(
    session_id: str, orchestrator: AgentOrchestrator = Depends(get_orchestrator)
):
    """Get session workspace"""
    try:
        logger.info(f"Loading session {session_id}")

        session_manager = await orchestrator.get_session_manager()
        workspace = await session_manager.get_session(session_id)

        if not workspace:
            raise HTTPException(status_code=404, detail="Session not found")

        return {
            "session_id": session_id,
            "workspace": (
                workspace.dict() if hasattr(workspace, "dict") else workspace.__dict__
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")


from fastapi import Request as FastAPIRequest
from server.routes.auth_routes import get_current_user_from_request

@router.post("/new", response_model=Dict[str, Any])
async def create_session(
    request: FastAPIRequest,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
):
    """Create a new co-creation session"""
    try:
        request_data = await request.json()
        topic = request_data.get("topic")
        # Accept both 'mode' and 'topic_descriptor' for compatibility
        mode = request_data.get("topic_descriptor") or request_data.get("mode", "story")
        user_preferences = request_data.get("user_preferences")
        initial_content = request_data.get("initial_content", "")
        policy = request_data.get("policy")
        user_id = request_data.get("user_id")

        # Try to get user_id from auth if not provided
        user_id_from_auth = None
        user = get_current_user_from_request(request)
        if user and "user_id" in user:
            user_id_from_auth = user["user_id"]
        if not user_id:
            user_id = user_id_from_auth or "default_user"

        session_id = str(uuid.uuid4())
        logger.info(f"Creating new session {session_id} for topic: {topic}")

        session_manager = await orchestrator.get_session_manager()

        from utils.schemas import NewSessionRequest, PolicySchema
        # Use provided policy or default
        policy_obj = PolicySchema(**policy) if policy else PolicySchema()

        request_obj = NewSessionRequest(
            user_id=user_id,
            topic=topic,
            topic_descriptor=mode,
            initial_content=initial_content,
            policy=policy_obj,
        )

        workspace = await session_manager.create_session(request_obj)

        return {
            "session_id": workspace.session_id,
            "workspace": (
                workspace.dict() if hasattr(workspace, "dict") else workspace.__dict__
            ),
            "message": "Session created successfully",
        }

    except Exception as e:
        logger.error(f"Session creation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create session: {str(e)}"
        )
        # Generate projections
        projections = {
            "A": {"content": "Projection A placeholder"},
            "B": {"content": "Projection B placeholder"},
            "C": {"content": "Projection C placeholder"},
        }
        if planner_agent:
            try:
                projections = await planner_agent.invoke(
                    workspace, {"num_projections": num_projections}
                )
            except Exception as e:
                logger.warning(f"Projection generation failed: {e}")

        return {
            "session_id": session_id,
            "projections": {
                k: v.dict() if hasattr(v, "dict") else v for k, v in projections.items()
            },
            "workspace": (
                workspace.dict() if hasattr(workspace, "dict") else workspace.__dict__
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Content generation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate content: {str(e)}"
        )


@router.post("/{session_id}/verify", response_model=Dict[str, Any])
async def verify_content(
    session_id: str,
    projections: Optional[Dict[str, Dict[str, Any]]] = Body(default=None),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
):
    """Verify content for consistency and accuracy"""
    try:
        logger.info(f"Verifying content for session {session_id}")

        session_manager = await orchestrator.get_session_manager()
        verifier_agent = await orchestrator.get_verifier_agent()

        workspace = await session_manager.load_workspace(session_id)
        if not workspace:
            raise HTTPException(status_code=404, detail="Session not found")

        # Convert projections if provided
        projection_schemas = {}
        if projections:
            for proj_id, proj_data in projections.items():
                try:
                    projection_schemas[proj_id] = ProjectionSchema(**proj_data)
                except Exception as e:
                    logger.warning(f"Invalid projection {proj_id}: {e}")

        # Verify projections
        verification_results = await verifier_agent.invoke(
            workspace, projection_schemas, {}
        )

        return {
            "session_id": session_id,
            "verification": {k: v.dict() for k, v in verification_results.items()},
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Content verification failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to verify content: {str(e)}"
        )


@router.post("/{session_id}/accept", response_model=Dict[str, Any])
async def accept_projection(
    session_id: str,
    projection_id: str = Body(..., description="ID of projection to accept"),
    projection_data: Dict[str, Any] = Body(
        ..., description="Projection data to accept"
    ),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
):
    """Accept a content projection and update workspace"""
    try:
        logger.info(f"Accepting projection {projection_id} for session {session_id}")

        session_manager = await orchestrator.get_session_manager()
        graph_manager = await orchestrator.get_graph_manager()

        workspace = await session_manager.get_session(session_id)
        if not workspace:
            raise HTTPException(status_code=404, detail="Session not found")

        # Create projection schema
        try:
            projection = ProjectionSchema(**projection_data)
        except Exception as e:
            logger.warning(f"Invalid projection data: {e}")
            projection = type("Projection", (), projection_data)()

        # Accept projection (add to workspace content)
        if hasattr(workspace, "topic_content"):
            workspace.topic_content += f"\n\n[Accepted Projection {projection_id}]\n{projection_data.get('content', '')}"
        elif hasattr(workspace, "story_so_far"):
            workspace.story_so_far += f"\n\n[Accepted Projection {projection_id}]\n{projection_data.get('content', '')}"

        # Update knowledge graph if manager available
        if graph_manager:
            try:
                await graph_manager.update_graph(workspace, {projection_id: projection})
            except Exception as e:
                logger.warning(f"Graph update failed: {e}")

        # Save workspace
        await session_manager.update_session(session_id, workspace)

        return {
            "session_id": session_id,
            "message": "Projection accepted successfully",
            "workspace": (
                workspace.dict() if hasattr(workspace, "dict") else workspace.__dict__
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Projection acceptance failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to accept projection: {str(e)}"
        )


@router.post("/{session_id}/workflow", response_model=Dict[str, Any])
async def run_complete_workflow(
    session_id: str,
    request: Request,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
):
    """Run complete co-creation workflow - accepts flexible payload shapes"""
    try:
        logger.info(f"Running complete workflow for session {session_id}")
        
        # Parse body flexibly to support both dict and raw string
        try:
            body = await request.json()
        except Exception:
            body = {}
        
        # Normalize user_input from various possible shapes
        if isinstance(body, dict):
            user_input = body.get("user_input") or body.get("text") or body.get("content") or ""
        elif isinstance(body, str):
            user_input = body
        else:
            user_input = ""

        result = await orchestrator.run_complete_workflow(session_id, user_input)

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to run workflow: {str(e)}")


@router.get("/{session_id}/graph", response_model=Dict[str, Any])
async def get_knowledge_graph(
    session_id: str, orchestrator: AgentOrchestrator = Depends(get_orchestrator)
):
    """Get knowledge graph for session"""
    try:
        logger.info(f"Getting knowledge graph for session {session_id}")

        session_manager = await orchestrator.get_session_manager()
        graph_manager = await orchestrator.get_graph_manager()

        workspace = await session_manager.get_session(session_id)
        if not workspace:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get graph structure
        nodes = []
        edges = []
        triples = []

        if graph_manager:
            try:
                nodes, edges = await graph_manager.get_graph_structure(
                    workspace.session_id
                )
            except Exception as e:
                logger.warning(f"Graph retrieval failed: {e}")

        # Get triples from workspace if available
        if hasattr(workspace, "kb_triples"):
            triples = workspace.kb_triples

        return {
            "session_id": session_id,
            "graph": {"nodes": nodes, "edges": edges, "triples": triples},
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Graph retrieval failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get knowledge graph: {str(e)}"
        )


@router.delete("/{session_id}", response_model=Dict[str, Any])
async def delete_session(
    session_id: str, orchestrator: AgentOrchestrator = Depends(get_orchestrator)
):
    """Delete a session"""
    try:
        logger.info(f"Deleting session {session_id}")

        session_manager = await orchestrator.get_session_manager()

        success = await session_manager.delete_session(session_id)

        if not success:
            raise HTTPException(status_code=404, detail="Session not found")

        return {"session_id": session_id, "message": "Session deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session deletion failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete session: {str(e)}"
        )


@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "human-ai-co-creation",
    }


# Add router to exports
__all__ = ["router"]
