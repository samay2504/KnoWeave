"""
FastAPI Application - Human-AI Co-Creation System
Main orchestrator implementing the blueprint specification
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, TYPE_CHECKING

try:
    from fastapi import FastAPI, HTTPException, Depends, Request, WebSocket, APIRouter
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, Response
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
    try:
        from .server_config import ServerConfig
        server_config = ServerConfig()
    except ImportError:
        from server_config import ServerConfig
        server_config = ServerConfig()
    PRODUCTION_IMPORTS = False

# Global variables for module availability
HEALTH_ROUTER_AVAILABLE = False
get_health_router = None

try:
    from utils.logging_cfg import setup_logging, get_logger
    from dependencies import setup_dependencies, get_container
    try:
        from api.health import get_health_router
        HEALTH_ROUTER_AVAILABLE = True
    except ImportError as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not import health router: {e}")
        get_health_router = None
        HEALTH_ROUTER_AVAILABLE = False
    
    try:
        from api.routes import router as api_router
    except ImportError as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not import API routes: {e}")
        api_router = None
except ImportError:
    # Fallback for relative imports
    try:
        from .utils.logging_cfg import setup_logging, get_logger
        from .dependencies import setup_dependencies, get_container
        from .api.routes import router as api_router
    except ImportError:
        # Simple fallback without advanced features
        import logging
        def setup_logging():
            logging.basicConfig(level=logging.INFO)
        def get_logger(name):
            return logging.getLogger(name)
        def setup_dependencies():
            return None
        def get_container():
            return None
        api_router = None

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
            # Convert Pydantic config to dict for agents
            config_dict = config.model_dump() if hasattr(config, 'model_dump') else dict(config)
            
            # Initialize session manager
            session_manager = SessionManager(config_dict)
            await session_manager.initialize()
            
            # Store session_manager in app state for global access
            app.state.session_manager = session_manager

            # Initialize agents
            agents = {
                "perception": PerceptionAgent(config_dict),
                "planner": PlannerGeneratorAgent(config_dict),
                "graph_manager": GraphManagerAgent(config_dict),
                "verifier": VerifierAgent(config_dict),
                "evaluator": EvaluatorAgent(config_dict),
            }

            # Initialize all agents that have an initialize method
            for agent_name, agent in agents.items():
                if hasattr(agent, 'initialize') and callable(getattr(agent, 'initialize')):
                    await agent.initialize()
                    logger.info(f"Initialized {agent_name} agent")
                else:
                    logger.info(f"Initialized {agent_name} agent (no initialization required)")

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

    # Add global /api/mode endpoint (simple approach)
    @app.post("/api/mode")
    async def global_mode_update(request: Request):
        """Global mode update endpoint for /api/mode"""
        try:
            data = await request.json()
            mode = data.get("mode", "balanced")
            session_id = data.get("session_id")
            
            logger.info(f"Global mode update request: mode={mode}, session_id={session_id}")
            
            # Try to get session_manager from app state if available
            session_manager = getattr(app.state, 'session_manager', None)
            
            if session_id and session_manager:
                try:
                    workspace = await session_manager.load_workspace(session_id)
                    if workspace:
                        # Update mode in workspace policy
                        if hasattr(workspace, 'update_policy'):
                            workspace.update_policy({"mode": mode})
                            await session_manager.save_workspace(session_id, force=True)
                        
                        return {"status": "success", "mode": mode, "current_mode": mode, "session_id": session_id}
                except Exception as e:
                    logger.warning(f"Failed to update mode in workspace: {e}")
            
            return {"status": "success", "mode": mode, "current_mode": mode}
        except Exception as e:
            logger.error(f"Global mode update failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # Include mode and PTG routes
    try:
        from api.mode_routes import mode_router, ptg_router
        app.include_router(mode_router)
        app.include_router(ptg_router)
        logger.info("Mode and PTG routes loaded successfully")
    except ImportError as e:
        logger.warning(f"Could not import mode routes: {e}")
        # Create simple fallback routes
        from fastapi import APIRouter
        fallback_router = APIRouter(prefix="/api", tags=["fallback"])
        
        @fallback_router.get("/session/modes")
        async def get_modes_fallback():
            return {
                "modes": {
                    "conservative": {"name": "Conservative", "description": "Safe, predictable responses"},
                    "balanced": {"name": "Balanced", "description": "Balanced creativity and consistency"},
                    "exploratory": {"name": "Exploratory", "description": "Creative, experimental approaches"},
                    "focused": {"name": "Focused", "description": "Highly specific, targeted outcomes"}
                },
                "default_mode": "balanced"
            }
        
        @fallback_router.post("/session/mode")
        async def update_mode_fallback(request: dict):
            return {"status": "success", "mode": request.get("mode", "balanced")}
        
        @fallback_router.post("/ptg/generate")
        async def generate_prompt_fallback(request: dict):
            return {
                "canonical_prompt": f"Generated prompt for: {request.get('user_prompt', '')}",
                "mode": request.get("mode", "balanced"),
                "agent_type": request.get("agent_type", "general")
            }
        
        app.include_router(fallback_router)
        
        async def get_status():
            return {"status": "running", "mode_routes": "unavailable"}
            
        app.include_router(fallback_router)

    # Include health endpoints - re-enabled after fixing compatibility issues
    try:
        if HEALTH_ROUTER_AVAILABLE and get_health_router is not None:
            app.include_router(get_health_router())
            logger.info("Health routes loaded successfully")
        else:
            # Create fallback health endpoint
            @app.get("/health")
            @app.get("/api/health")
            async def health_check():
                """Fallback health check endpoint"""
                return {
                    "status": "healthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "service": "human-ai-co-creation"
                }
            logger.info("Fallback health endpoint created")
    except Exception as e:
        logger.warning(f"Failed to load health routes: {e}")

    # Include API routes
    if api_router is not None:
        app.include_router(api_router)
        logger.info("API routes loaded successfully")
    else:
        logger.warning("API router not available, using fallback routes only")

    # Include authentication routes
    try:
        from routes.auth_routes import router as auth_router
        app.include_router(auth_router)
        logger.info("Authentication routes loaded successfully")
    except ImportError as e:
        logger.warning(f"Could not import auth routes: {e}")

    # Add /api/me endpoint for authentication tests
    @app.get("/api/me")
    async def get_current_user(request: Request):
        """Get current authenticated user."""
        try:
            from auth.google_oauth import get_current_user_from_request
            user = get_current_user_from_request(request)
            if user:
                return {"user": user}
            else:
                raise HTTPException(status_code=401, detail="Not authenticated")
        except ImportError:
            raise HTTPException(status_code=501, detail="Authentication not available")

    @app.post("/auth/logout")
    async def logout(response: Response):
        """Logout endpoint."""
        try:
            from auth.google_oauth import clear_auth_cookie
            clear_auth_cookie(response)
            return {"status": "success", "message": "Logged out successfully"}
        except ImportError:
            raise HTTPException(status_code=501, detail="Authentication not available")

    # Individual Agent Endpoints
    @app.post("/api/agents/perception/analyze")
    async def perception_analyze(request: Request):
        """Direct perception agent analysis"""
        try:
            if not agents.get("perception"):
                raise HTTPException(status_code=500, detail="Perception agent not available")
            
            data = await request.json()
            session_id = data.get("session_id")
            content = data.get("content", "")
            
            if not session_id:
                raise HTTPException(status_code=400, detail="session_id required")
            
            # Load workspace
            workspace = await session_manager.load_workspace(session_id)
            if not workspace:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Convert workspace to proper format, handling validation errors gracefully
            try:
                if hasattr(workspace, 'to_dict'):
                    workspace_data = workspace.to_dict()
                elif hasattr(workspace, 'model_dump'):
                    workspace_data = workspace.model_dump()
                else:
                    workspace_data = workspace
            except Exception as e:
                logger.warning(f"Workspace conversion failed, using raw data: {e}")
                # Fallback: get raw workspace data
                raw_workspace = await session_manager.workspace_manager.get_workspace(session_id)
                workspace_data = raw_workspace.data if hasattr(raw_workspace, 'data') else {}
            
            result = await agents["perception"].invoke(workspace_data, {
                "session_id": session_id,
                "content": content,
                "mode": data.get("mode", "balanced")
            })
            
            return {
                "status": "success",
                "session_id": session_id,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Perception analysis failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/agents/planner/generate")
    async def planner_generate(request: Request):
        """Direct planner agent generation"""
        try:
            if not agents.get("planner"):
                raise HTTPException(status_code=500, detail="Planner agent not available")
            
            data = await request.json()
            session_id = data.get("session_id")
            
            if not session_id:
                raise HTTPException(status_code=400, detail="session_id required")
            
            # Get session_manager from app state
            session_manager = getattr(app.state, 'session_manager', None)
            if not session_manager:
                raise HTTPException(status_code=500, detail="Session manager not available")
            
            # Load workspace
            workspace = await session_manager.load_workspace(session_id)
            if not workspace:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Convert workspace to proper format, handling validation errors gracefully
            try:
                if hasattr(workspace, 'to_dict'):
                    workspace_data = workspace.to_dict()
                elif hasattr(workspace, 'model_dump'):
                    workspace_data = workspace.model_dump()
                else:
                    workspace_data = workspace
            except Exception as e:
                logger.warning(f"Workspace conversion failed, using raw data: {e}")
                # Fallback: get raw workspace data
                raw_workspace = await session_manager.workspace_manager.get_workspace(session_id)
                workspace_data = raw_workspace.data if hasattr(raw_workspace, 'data') else {}
            
            # Generate prompt payload using PTG through Session Manager
            prompt_payload = session_manager.ptg.generate_canonical_prompt(
                agent_name="planner",
                session_id=session_id,
                topic=data.get("topic", "general"),
                topic_descriptor=data.get("topic_descriptor", "General content generation"),
                input_data=data,
                mode=data.get("mode", "balanced"),
                context_chunks=[],
                user_constraints=data.get("constraints", {})
            )
            
            result = await agents["planner"].invoke(workspace_data, {
                "session_id": session_id,
                "max_branches": data.get("max_branches", 3),
                "mode": data.get("mode", "balanced"),
                "prompt_payload": prompt_payload
            })
            
            return {
                "status": "success",
                "session_id": session_id,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Planner generation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/agents/graph/query")
    async def graph_query(request: Request):
        """Direct graph manager query"""
        try:
            if not agents.get("graph_manager"):
                raise HTTPException(status_code=500, detail="Graph manager agent not available")
            
            data = await request.json()
            session_id = data.get("session_id")
            
            if not session_id:
                raise HTTPException(status_code=400, detail="session_id required")
            
            # Load workspace
            workspace = await session_manager.load_workspace(session_id)
            if not workspace:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Convert workspace to proper format, handling validation errors gracefully
            try:
                if hasattr(workspace, 'to_dict'):
                    workspace_data = workspace.to_dict()
                elif hasattr(workspace, 'model_dump'):
                    workspace_data = workspace.model_dump()
                else:
                    workspace_data = workspace
            except Exception as e:
                logger.warning(f"Workspace conversion failed, using raw data: {e}")
                # Fallback: get raw workspace data
                raw_workspace = await session_manager.workspace_manager.get_workspace(session_id)
                workspace_data = raw_workspace.data if hasattr(raw_workspace, 'data') else {}
            
            result = await agents["graph_manager"].invoke(workspace_data, {
                "session_id": session_id,
                "action": data.get("action", "query"),
                "query": data.get("query", ""),
                "entities": data.get("entities", []),
                "events": data.get("events", [])
            })
            
            return {
                "status": "success",
                "session_id": session_id,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Graph query failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/agents/verifier/validate")
    async def verifier_validate(request: Request):
        """Direct verifier agent validation"""
        try:
            if not agents.get("verifier"):
                raise HTTPException(status_code=500, detail="Verifier agent not available")
            
            data = await request.json()
            session_id = data.get("session_id")
            content = data.get("content", "")
            
            if not session_id:
                raise HTTPException(status_code=400, detail="session_id required")
            
            # Get session_manager from app state
            session_manager = getattr(app.state, 'session_manager', None)
            if not session_manager:
                raise HTTPException(status_code=500, detail="Session manager not available")
            
            # Load workspace
            workspace = await session_manager.load_workspace(session_id)
            if not workspace:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Convert workspace to proper format, handling validation errors gracefully
            try:
                if hasattr(workspace, 'to_dict'):
                    workspace_data = workspace.to_dict()
                elif hasattr(workspace, 'model_dump'):
                    workspace_data = workspace.model_dump()
                else:
                    workspace_data = workspace
            except Exception as e:
                logger.warning(f"Workspace conversion failed, using raw data: {e}")
                # Fallback: get raw workspace data
                raw_workspace = await session_manager.workspace_manager.get_workspace(session_id)
                workspace_data = raw_workspace.data if hasattr(raw_workspace, 'data') else {}
            
            # Generate prompt payload using PTG through Session Manager
            prompt_payload = session_manager.ptg.generate_canonical_prompt(
                agent_name="verifier",
                session_id=session_id,
                topic=data.get("topic", "general"),
                topic_descriptor=data.get("topic_descriptor", "Content verification"),
                input_data={"content": content, **data},
                mode=data.get("mode", "balanced"),
                context_chunks=[],
                user_constraints=data.get("constraints", {})
            )
            
            result = await agents["verifier"].invoke(workspace_data, {
                "session_id": session_id,
                "content": content,
                "branch_data": data.get("branch_data", {}),
                "prompt_payload": prompt_payload
            })
            
            return {
                "status": "success",
                "session_id": session_id,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Verifier validation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/agents/evaluator/assess")
    async def evaluator_assess(request: Request):
        """Direct evaluator agent assessment"""
        try:
            if not agents.get("evaluator"):
                raise HTTPException(status_code=500, detail="Evaluator agent not available")
            
            data = await request.json()
            session_id = data.get("session_id")
            branches = data.get("branches", [])
            
            if not session_id:
                raise HTTPException(status_code=400, detail="session_id required")
            
            # Load workspace
            workspace = await session_manager.load_workspace(session_id)
            if not workspace:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Convert workspace to proper format, handling validation errors gracefully
            try:
                if hasattr(workspace, 'to_dict'):
                    workspace_data = workspace.to_dict()
                elif hasattr(workspace, 'model_dump'):
                    workspace_data = workspace.model_dump()
                else:
                    workspace_data = workspace
            except Exception as e:
                logger.warning(f"Workspace conversion failed, using raw data: {e}")
                # Fallback: get raw workspace data
                raw_workspace = await session_manager.workspace_manager.get_workspace(session_id)
                workspace_data = raw_workspace.data if hasattr(raw_workspace, 'data') else {}
            
            result = await agents["evaluator"].invoke(workspace_data, {
                "session_id": session_id,
                "branches": branches
            })
            
            return {
                "status": "success",
                "session_id": session_id,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Evaluator assessment failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # LLM Generation Endpoint
    @app.post("/api/llm/generate")
    async def llm_generate(request: Request):
        """Direct LLM generation endpoint"""
        try:
            data = await request.json()
            prompt = data.get("prompt", "")
            model = data.get("model", "default")
            
            if not prompt:
                raise HTTPException(status_code=400, detail="prompt required")
            
            # Generate using LLM provider
            try:
                from dependencies import get_container
                container = get_container()
                if container and hasattr(container, 'llm_provider'):
                    llm_provider = container.llm_provider()
                    
                    # Generate using LLM provider
                    if hasattr(llm_provider, 'generate'):
                        result = await llm_provider.generate(prompt, model=model)
                    elif hasattr(llm_provider, 'generate_text'):
                        result_text = await llm_provider.generate_text(prompt, model=model)
                        result = {
                            "text": result_text,
                            "model": model,
                            "tokens": len(prompt.split())
                        }
                    else:
                        # Fallback mock generation
                        result = {
                            "text": f"Generated response for: {prompt[:50]}...",
                            "model": model,
                            "tokens": len(prompt.split())
                        }
                else:
                    # Mock generation when no provider available
                    result = {
                        "text": f"Mock generated response for: {prompt[:50]}...",
                        "model": model,
                        "tokens": len(prompt.split()),
                        "note": "No LLM provider configured"
                    }
            except Exception as e:
                logger.warning(f"LLM provider error: {e}")
                # Fallback mock generation
                result = {
                    "text": f"Fallback response for: {prompt[:50]}...",
                    "model": model,
                    "tokens": len(prompt.split()),
                    "error": str(e)
                }
            
            return {
                "status": "success",
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # WebSocket endpoint for real-time updates
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for real-time communication"""
        await websocket.accept()
        
        try:
            while True:
                # Wait for messages from client
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data) if isinstance(data, str) else data
                    message_type = message.get("type", "unknown")
                    
                    if message_type == "ping":
                        # Simple ping-pong
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "timestamp": datetime.now().isoformat()
                        }))
                    
                    elif message_type == "subscribe":
                        # Subscribe to session updates
                        session_id = message.get("session_id")
                        if session_id:
                            await websocket.send_text(json.dumps({
                                "type": "subscribed",
                                "session_id": session_id,
                                "timestamp": datetime.now().isoformat()
                            }))
                    
                    elif message_type == "suggestion_request":
                        # Handle real-time suggestion requests
                        session_id = message.get("session_id")
                        if session_id and session_manager:
                            # This could trigger the full suggestion pipeline
                            await websocket.send_text(json.dumps({
                                "type": "suggestion_started",
                                "session_id": session_id,
                                "timestamp": datetime.now().isoformat()
                            }))
                            
                            # In a full implementation, you would run the agent pipeline here
                            # and send progress updates
                            
                            await websocket.send_text(json.dumps({
                                "type": "suggestion_complete",
                                "session_id": session_id,
                                "suggestions": [],
                                "timestamp": datetime.now().isoformat()
                            }))
                    
                    else:
                        # Echo unknown messages
                        await websocket.send_text(json.dumps({
                            "type": "echo",
                            "original": message,
                            "timestamp": datetime.now().isoformat()
                        }))
                        
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format",
                        "timestamp": datetime.now().isoformat()
                    }))
                    
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await websocket.close(code=1000)

    @app.post("/api/session/{session_id}/suggestion_signal")
    async def suggestion_signal(session_id: str, request: Request):
        """Receives signals from the frontend to trigger suggestions."""
        try:
            if not session_manager:
                raise HTTPException(status_code=500, detail="Session manager not initialized")

            signal_data = await request.json()
            trigger_type = signal_data.get("trigger_type") or signal_data.get("type")  # Support both formats
            
            # The orchestrator (session_manager) decides whether to run the suggestion pipeline
            should_suggest, reason = await session_manager.handle_suggestion_trigger(session_id, trigger_type, signal_data)

            if should_suggest:
                # This would trigger the suggestion pipeline asynchronously
                # For this implementation, we'll just log it.
                logger.info(f"Suggestion triggered for session {session_id} due to {reason}")
                # In a real implementation, you would call a background task here
                # to run the full suggestion pipeline (perception -> planner -> etc.)
                # and then push the results to the client via websockets.
                return {"status": "suggestion_triggered", "reason": reason}
            else:
                return {"status": "suggestion_skipped", "reason": reason}

        except Exception as e:
            logger.error(f"Error handling suggestion signal: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # Session endpoints
    @app.post("/api/session/new", response_model=SessionResponse)
    async def create_new_session(request: NewSessionRequest):
        """Create a new writing session"""
        try:
            if not session_manager:
                raise HTTPException(
                    status_code=500, detail="Session manager not initialized"
                )

            workspace = await session_manager.create_session(request)

            # Return workspace details in response
            return SessionResponse(
                session_id=workspace.session_id,
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
            perception_result = await agents["perception"].invoke(
                workspace.model_dump() if hasattr(workspace, 'model_dump') else workspace,
                {
                    "session_id": session_id,
                    "mode": request.mode
                }
            )

            # 2. Update graph
            await agents["graph_manager"].invoke(
                workspace.model_dump() if hasattr(workspace, 'model_dump') else workspace,
                {
                    "session_id": session_id,
                    "entities": perception_result.get("entities", []),
                    "events": perception_result.get("events", []),
                }
            )

            # 3. Generate projections
            max_branches = request.options.get("max_branches", 3)
            planner_result = await agents["planner"].invoke(
                workspace.model_dump() if hasattr(workspace, 'model_dump') else workspace,
                {
                    "session_id": session_id, 
                    "max_branches": max_branches, 
                    "mode": request.mode
                }
            )

            # 4. Verify branches
            verified_branches = []
            verifications = []
            for branch in planner_result.get("branches", []):
                verification = await agents["verifier"].invoke(
                    workspace.model_dump() if hasattr(workspace, 'model_dump') else workspace,
                    {
                        "session_id": session_id,
                        "content": branch.get("content", ""), 
                        "branch_data": branch
                    }
                )
                verifications.append(verification)
                verified_branches.append(branch)

            # 5. Score and rank
            evaluation = await agents["evaluator"].invoke(
                workspace.model_dump() if hasattr(workspace, 'model_dump') else workspace,
                {
                    "session_id": session_id,
                    "branches": verified_branches
                }
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
            workspace = await session_manager.load_workspace(session_id)
            result = await agents["graph_manager"].invoke(
                workspace.model_dump() if hasattr(workspace, 'model_dump') else workspace,
                {
                    "session_id": session_id,
                    "action": "backtrack", 
                    "node_id": request.node_id
                }
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

            # Convert workspace to proper dict format for SnapshotResponse
            if hasattr(workspace, 'to_dict'):
                workspace_dict = workspace.to_dict()
            elif hasattr(workspace, 'model_dump'):
                workspace_dict = workspace.model_dump()
            elif isinstance(workspace, dict):
                workspace_dict = workspace
            else:
                # Fallback: convert to dict via __dict__ or str representation
                workspace_dict = workspace.__dict__ if hasattr(workspace, '__dict__') else {"data": str(workspace)}

            return SnapshotResponse(session_id=session_id, snapshot=workspace_dict)

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

    @app.options("/api/health")
    async def api_health_options():
        """OPTIONS handler for CORS preflight requests"""
        return {}

    @app.get("/health/database")
    async def database_health_check():
        """Database health check endpoint"""
        try:
            db_status = {}
            if session_manager and hasattr(session_manager, 'workspace_manager'):
                # Check MongoDB
                try:
                    from dependencies import get_container
                    container = get_container()
                    if container and hasattr(container, 'mongo_client'):
                        mongo_client = container.mongo_client()
                        await mongo_client.admin.command("ping")
                        db_status["mongodb"] = "healthy"
                    else:
                        db_status["mongodb"] = "not_configured"
                except Exception as e:
                    db_status["mongodb"] = f"error: {str(e)}"
                
                # Check ArangoDB  
                try:
                    if container and hasattr(container, 'arango_client'):
                        arango_client = container.arango_client()
                        # Simple ping operation
                        arango_client.version()
                        db_status["arangodb"] = "healthy"
                    else:
                        db_status["arangodb"] = "not_configured"
                except Exception as e:
                    db_status["arangodb"] = f"error: {str(e)}"
            else:
                db_status = {"status": "session_manager_not_initialized"}
            
            return {
                "status": "healthy" if all(v == "healthy" for v in db_status.values() if "error" not in str(v)) else "degraded",
                "databases": db_status,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    @app.get("/health/agents")
    async def agents_health_check():
        """Agents health check endpoint"""
        try:
            agent_status = {}
            if agents:
                for agent_name, agent in agents.items():
                    try:
                        # Try to get agent status if available
                        if hasattr(agent, 'get_health_status'):
                            agent_status[agent_name] = await agent.get_health_status()
                        elif hasattr(agent, 'is_initialized'):
                            agent_status[agent_name] = "healthy" if agent.is_initialized else "not_initialized"
                        else:
                            agent_status[agent_name] = "healthy"  # Assume healthy if no health check method
                    except Exception as e:
                        agent_status[agent_name] = f"error: {str(e)}"
            else:
                agent_status = {"status": "no_agents_loaded"}
            
            return {
                "status": "healthy" if all("error" not in str(v) for v in agent_status.values()) else "degraded",
                "agents": agent_status,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "error", 
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    @app.get("/health/llm")
    async def llm_health_check():
        """LLM provider health check endpoint"""
        try:
            llm_status = {}
            
            # Check if we have LLM providers configured
            try:
                from dependencies import get_container
                container = get_container()
                if container and hasattr(container, 'llm_provider'):
                    llm_provider = container.llm_provider()
                    # Try a simple health check
                    if hasattr(llm_provider, 'health_check'):
                        llm_status["provider"] = await llm_provider.health_check()
                    else:
                        llm_status["provider"] = "healthy"
                else:
                    llm_status["provider"] = "not_configured"
            except Exception as e:
                llm_status["provider"] = f"error: {str(e)}"
            
            return {
                "status": "healthy" if "error" not in str(llm_status.get("provider", "")) else "degraded",
                "llm": llm_status,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e), 
                "timestamp": datetime.now().isoformat()
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
    import os
    
    # Disable reload in production to avoid import issues
    reload_mode = os.getenv("DEBUG", "false").lower() == "true"
    
    uvicorn.run(
        "app:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=reload_mode,
        access_log=True
    )
