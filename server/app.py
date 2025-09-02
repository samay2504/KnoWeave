"""
FastAPI Application - Human-AI Co-Creation System
Main orchestrator implementing the blueprint specification
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, TYPE_CHECKING

try:
    from fastapi import FastAPI, HTTPException, Depends, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    if TYPE_CHECKING:
        from fastapi import FastAPI
    else:
        FastAPI = None

# Use production-ready import system
try:
    from core.config import config as server_config
    from core.imports import import_manager
    PRODUCTION_IMPORTS = True
except ImportError:
    # Fallback to old import system during transition
    from server_config import ServerConfig
    server_config = ServerConfig()
    PRODUCTION_IMPORTS = False

from utils.logging_cfg import setup_logging, get_logger
from dependencies import setup_dependencies, get_container

# from api.health import get_health_router  # Temporarily disabled due to aioredis compatibility issue
from api.routes import router as api_router

# Import agents with production-ready system
if PRODUCTION_IMPORTS:
    # Use dynamic imports for better resilience
    SessionManager = import_manager.get_attribute('server.agents.session_manager', 'SessionManager')
    PerceptionAgent = import_manager.get_attribute('server.agents.perception_agent', 'PerceptionAgent')
    PlannerGeneratorAgent = import_manager.get_attribute('server.agents.planner_generator_agent', 'PlannerGeneratorAgent')
    GraphManagerAgent = import_manager.get_attribute('server.agents.graph_manager_agent', 'GraphManagerAgent')
    VerifierAgent = import_manager.get_attribute('server.agents.verifier_agent', 'VerifierAgent')
    EvaluatorAgent = import_manager.get_attribute('server.agents.evaluator_agent', 'EvaluatorAgent')
else:
    # Fallback imports
    from agents.session_manager import SessionManager
    from agents.perception_agent import PerceptionAgent
    from agents.planner_generator_agent import PlannerGeneratorAgent
    from agents.graph_manager_agent import GraphManagerAgent
    from agents.verifier_agent import VerifierAgent
from agents.evaluator_agent import EvaluatorAgent

# Import schemas
from utils.schemas import (
    NewSessionRequest,
    SessionResponse,
    SuggestRequest,
    SuggestionsResponse,
    AcceptBranchRequest,
    BacktrackRequest,
    BacktrackResponse,
    SnapshotResponse,
)

# Initialize logging
setup_logging()
logger = get_logger("app")

# Server configuration
# Load configuration
if PRODUCTION_IMPORTS:
    config = server_config
else:
    config = server_config

# Global agent instances - Use Any for dynamic imports
session_manager: Optional[Any] = None
agents: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: "FastAPI"):
    """Application lifespan manager"""
    global session_manager, agents

    # Startup
    logger.info("Starting Human-AI Co-Creation System")
    logger.info(f"Server config: Host={config.host}:{config.port}, Debug={config.debug}")

    try:
        # Setup dependencies first
        async with setup_dependencies(config) as container:
            # Initialize session manager
            session_manager = SessionManager(config)
            await session_manager.initialize()

            # Initialize agents
            agents = {
                "perception": PerceptionAgent(config),
                "planner": PlannerGeneratorAgent(config),
                "graph_manager": GraphManagerAgent(config),
                "verifier": VerifierAgent(config),
                "evaluator": EvaluatorAgent(config),
            }

            # Initialize all agents
            for agent_name, agent in agents.items():
                await agent.initialize()
                logger.info(f"Initialized {agent_name} agent")

            logger.info("All services initialized successfully")

            yield

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down Human-AI Co-Creation System")
        if session_manager:
            await session_manager.cleanup()


def create_app() -> "FastAPI":
    """Create and configure FastAPI application"""
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI is required but not installed")

    # Create rate limiter
    limiter = Limiter(key_func=get_remote_address)

    # Create FastAPI app
    app = FastAPI(
        title="Human-AI Co-Creation System",
        description="AI-powered writing assistance with multi-agent orchestration",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Setup rate limiter state and exception handler
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include auth routes
    from routes.auth_routes import router as auth_router
    app.include_router(auth_router)

    # Include health endpoints - temporarily disabled due to compatibility issues
    # app.include_router(get_health_router())

    # Include API routes
    app.include_router(api_router)

    # Session endpoints
    @app.post("/api/session/new", response_model=SessionResponse)
    async def create_new_session(request: NewSessionRequest):
        """Create a new writing session"""
        try:
            if not session_manager:
                raise HTTPException(
                    status_code=500, detail="Session manager not initialized"
                )

            session_id = await session_manager.create_session(
                user_id=request.user_id,
                initial_text=request.initial_content,
                topic=getattr(request, "topic", "story"),
                policy=request.policy or {},
            )

            # Load the workspace to return in response
            workspace = await session_manager.load_workspace(session_id)

            return SessionResponse(
                session_id=session_id,
                workspace=workspace,
                status="created",
                message="Session created successfully",
            )

        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post(
        "/api/session/{session_id}/invoke_suggest", response_model=SuggestionsResponse
    )
    async def invoke_suggestions(session_id: str, request: SuggestRequest):
        """Generate writing suggestions for a session"""
        try:
            if not session_manager:
                raise HTTPException(
                    status_code=500, detail="Session manager not initialized"
                )

            # Load workspace
            workspace = await session_manager.load_workspace(session_id)
            if not workspace:
                raise HTTPException(status_code=404, detail="Session not found")

            # Run agent pipeline
            # 1. Perception
            perception_result = await agents["perception"].run(
                session_id,
                {
                    "content": workspace.get(
                        "story_so_far", workspace.get("topic_content", "")
                    )
                },
            )

            # 2. Update graph
            await agents["graph_manager"].run(
                session_id,
                {
                    "entities": perception_result.get("entities", []),
                    "events": perception_result.get("events", []),
                },
            )

            # 3. Generate projections
            max_branches = request.options.get("max_branches", 3)
            planner_result = await agents["planner"].run(
                session_id, {"max_branches": max_branches, "mode": request.mode}
            )

            # 4. Verify branches
            verified_branches = []
            verifications = []
            for branch in planner_result.get("branches", []):
                verification = await agents["verifier"].run(
                    session_id,
                    {"content": branch.get("content", ""), "branch_data": branch},
                )
                verifications.append(verification)
                verified_branches.append(branch)

            # 5. Score and rank
            evaluation = await agents["evaluator"].run(
                session_id, {"branches": verified_branches}
            )

            # Save projections to workspace
            await session_manager.save_projections(
                session_id,
                {
                    "A": verified_branches[0] if len(verified_branches) > 0 else None,
                    "B": verified_branches[1] if len(verified_branches) > 1 else None,
                    "C": verified_branches[2] if len(verified_branches) > 2 else None,
                },
            )

            return SuggestionsResponse(
                session_id=session_id,
                projections={
                    f"branch_{i}": branch
                    for i, branch in enumerate(verified_branches[:max_branches])
                },
                metadata={
                    "branch_scores": evaluation.get("branch_scores", []),
                    "verifications": verifications[:max_branches]
                },
                status="success",
            )

        except Exception as e:
            logger.error(f"Failed to generate suggestions: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/session/{session_id}/accept_branch", response_model=SessionResponse)
    async def accept_branch(session_id: str, request: AcceptBranchRequest):
        """Accept a suggested branch and update the story"""
        try:
            if not session_manager:
                raise HTTPException(
                    status_code=500, detail="Session manager not initialized"
                )

            result = await session_manager.accept_branch(session_id, request.branch_id)

            # Load the updated workspace to return in response
            workspace = await session_manager.load_workspace(session_id)

            return SessionResponse(
                session_id=session_id,
                workspace=workspace,
                status="accepted",
                message=f"Branch {request.branch_id} accepted successfully",
            )

        except Exception as e:
            logger.error(f"Failed to accept branch: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/session/{session_id}/backtrack", response_model=BacktrackResponse)
    async def backtrack_session(session_id: str, request: BacktrackRequest):
        """Backtrack to a previous point in the story"""
        try:
            if not session_manager:
                raise HTTPException(
                    status_code=500, detail="Session manager not initialized"
                )

            # Use graph manager for backtracking
            result = await agents["graph_manager"].run(
                session_id, {"action": "backtrack", "node_id": request.node_id}
            )

            return BacktrackResponse(
                session_id=session_id,
                reverted_to=request.node_id,
                new_projections=result.get("new_projections", {}),
                status="backtracked",
            )

        except Exception as e:
            logger.error(f"Failed to backtrack: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/session/{session_id}/snapshot", response_model=SnapshotResponse)
    async def get_session_snapshot(session_id: str):
        """Get current workspace snapshot"""
        try:
            if not session_manager:
                raise HTTPException(
                    status_code=500, detail="Session manager not initialized"
                )

            workspace = await session_manager.load_workspace(session_id)
            if not workspace:
                raise HTTPException(status_code=404, detail="Session not found")

            return SnapshotResponse(session_id=session_id, snapshot=workspace)

        except Exception as e:
            logger.error(f"Failed to get snapshot: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # Simple health endpoint
    @app.get("/health")
    async def health_check():
        """Basic health check endpoint"""
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}

    @app.get("/api/health")
    async def api_health_check():
        """API health check endpoint"""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "session_manager": session_manager is not None,
                "agents": len(agents) > 0
            }
        }

    # Serve static files (frontend)
    try:
        # Use absolute path to web/build directory (relative to project root)
        project_root = Path(__file__).parent.parent
        static_dir = project_root / "web" / "build"
        
        if static_dir.exists():
            app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
            logger.info(f"Serving static files from: {static_dir}")
        else:
            logger.warning(f"Static files directory not found: {static_dir}")
    except Exception as e:
        logger.warning(f"Failed to mount static files: {e}")

    return app


# Create the app instance
app = create_app() if FASTAPI_AVAILABLE else None

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server.app:app", host="0.0.0.0", port=8000, reload=True)
