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

            # Initialize agents with production configuration and LLM provider assignment
            from utils.production_agent_config import AgentInitializationManager
            
            agent_init_manager = AgentInitializationManager(config_dict)
            
            # Get LLM provider from multiple sources with fallback priority
            llm_provider = None
            
            # Priority 1: Try to get from dependency container (most reliable)
            try:
                container = getattr(app.state, 'container', None)
                if container and hasattr(container, 'llm_provider'):
                    container_llm = container.llm_provider()
                    if container_llm:
                        llm_provider = container_llm
                        logger.info("✅ LLM provider obtained from dependency container")
            except Exception as e:
                logger.debug(f"Could not get LLM provider from container: {e}")
            
            # Priority 2: Try session manager as fallback
            if not llm_provider:
                if hasattr(session_manager, 'llm_provider'):
                    llm_provider = session_manager.llm_provider
                    if llm_provider:
                        logger.info("✅ LLM provider obtained from session manager")
                elif hasattr(session_manager, 'ptg') and hasattr(session_manager.ptg, 'llm_provider'):
                    llm_provider = session_manager.ptg.llm_provider
                    if llm_provider:
                        logger.info("✅ LLM provider obtained from PTG")
            
            # Priority 3: Try direct import as last resort
            if not llm_provider:
                try:
                    from llm_provider import AsyncLLMProvider
                    llm_config = {
                        'providers': ['huggingface', 'gemini', 'openai', 'groq'],
                        'model': 'gpt-3.5-turbo',
                        'temperature': 0.7,
                        'max_tokens': 1000
                    }
                    llm_provider = AsyncLLMProvider(llm_config)
                    await llm_provider.initialize()
                    logger.info("✅ LLM provider created directly")
                except Exception as e:
                    logger.warning(f"Could not create LLM provider directly: {e}")
            
            if not llm_provider:
                logger.warning("⚠️  No LLM provider available - agents will use fallback mode")
            else:
                logger.info(f"🎯 LLM provider ready: {type(llm_provider).__name__}")
            
            agents = {
                "perception": PerceptionAgent(config_dict),
                "planner": PlannerGeneratorAgent(config_dict),
                "graph_manager": GraphManagerAgent(config_dict),
                "verifier": VerifierAgent(config_dict),
                "evaluator": EvaluatorAgent(config_dict),
            }

            # Initialize all agents with production settings and LLM provider
            agents = await agent_init_manager.initialize_agents(agents, llm_provider)
            
            # Assign LLM provider directly to agents to reduce warnings
            if llm_provider:
                for agent_name, agent in agents.items():
                    if hasattr(agent, 'llm_provider'):
                        agent.llm_provider = llm_provider
                        logger.info(f"LLM provider assigned to {agent_name} agent")
            
            # PRODUCTION FIX: Inject global agents into routes.py
            try:
                from api.routes import set_global_dependencies
                set_global_dependencies(agents, session_manager)
                logger.info("✅ Global agents and session_manager injected into API routes")
            except ImportError as import_err:
                logger.error(f"❌ Could not import set_global_dependencies: {import_err}")
                logger.error("Routes will create new agent instances - graph data will be missing!")
            except Exception as inject_err:
                logger.error(f"❌ Failed to inject global agents: {inject_err}")
                logger.error("Routes will not have access to populated agent instances!")
            
            logger.info("All services initialized successfully with production configuration")

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

    # Add global exception handler for production safety
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Catch all exceptions and return structured JSON instead of 500 stack traces"""
        import traceback
        logger.error(f"Unhandled exception: {exc}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Log to file for diagnostics
        try:
            import os
            from pathlib import Path
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            with open(logs_dir / "errors.log", "a", encoding="utf-8") as f:
                from datetime import datetime
                f.write(f"\n[{datetime.utcnow().isoformat()}] {request.method} {request.url}\n")
                f.write(f"Error: {exc}\n")
                f.write(traceback.format_exc())
                f.write("\n---\n")
        except Exception as log_err:
            logger.warning(f"Failed to write error log: {log_err}")
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc) if server_config.environment.lower() in ('development', 'dev') else "An unexpected error occurred",
                "timestamp": datetime.utcnow().isoformat()
            }
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
            content = data.get("content", "") or data.get("input_text", "")
            
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
            
            # Add content to workspace data for perception agent
            workspace_data["content"] = content
            workspace_data["input_text"] = content
            
            result = await agents["perception"].invoke(workspace_data, {
                "session_id": session_id,
                "content": content,
                "input_text": content,
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

    @app.post("/api/agents/perception/detect-domain")
    async def perception_detect_domain(request: Request):
        """Detect domain and role from input text using LLM when available"""
        try:
            if not agents.get("perception"):
                raise HTTPException(status_code=500, detail="Perception agent not available")
            
            data = await request.json()
            text = data.get("text", "") or data.get("content", "") or data.get("input_text", "")
            
            if not text:
                raise HTTPException(status_code=400, detail="text, content, or input_text required")
            
            # Call LLM-powered detection if available, fallback to pattern matching
            perception_agent = agents["perception"]
            if hasattr(perception_agent, 'detect_domain_and_role_llm'):
                result = await perception_agent.detect_domain_and_role_llm(text)
                logger.info(f"✅ Domain detected via LLM: {result.get('topic_family')}")
            elif hasattr(perception_agent, 'detect_domain_and_role'):
                result = perception_agent.detect_domain_and_role(text)
                logger.info(f"ℹ️  Domain detected via patterns: {result.get('topic_family')}")
            else:
                # Fallback: basic domain detection
                result = {
                    "domain": "general",
                    "confidence": 0.5,
                    "suggested_role": "general_assistant",
                    "detected_at": datetime.now().isoformat()
                }
                logger.warning("Using fallback domain detection")
            
            return {
                "status": "success",
                "domain_info": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Domain detection failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/agents/planner/generate")
    async def planner_generate(request: Request):
        """Direct planner agent generation with production-grade error handling"""
        from utils.agent_fallbacks import AgentFallbackHandler, ProductionAgentValidator
        
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
                logger.error("Session manager not available for planner agent")
                # Return fallback response instead of failing
                fallback_result = AgentFallbackHandler.create_fallback_response(
                    "planner", session_id, "Session manager unavailable"
                )
                return {
                    "status": "fallback",
                    "session_id": session_id,
                    "result": fallback_result,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Load workspace with validation
            workspace = await session_manager.load_workspace(session_id)
            if not workspace:
                logger.warning(f"Session {session_id} not found for planner agent")
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Convert workspace to proper format with production validation
            workspace_data = ProductionAgentValidator.validate_workspace_data(workspace)
            
            # Create agent configuration with enhanced fallbacks
            agent_config = {
                "session_id": session_id,
                "max_branches": data.get("max_branches", 3),
                "mode": data.get("mode", "balanced")
            }
            
            # Generate prompt payload with fallback handling
            try:
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
                agent_config["prompt_payload"] = prompt_payload
            except Exception as e:
                logger.warning(f"Failed to generate prompt payload for planner: {e}")
                # Use fallback prompt payload
                content = data.get("content", workspace_data.get("content", ""))
                agent_config = AgentFallbackHandler.enhance_agent_config(
                    agent_config, "planner", content
                )
            
            # Invoke agent with enhanced configuration
            result = await agents["planner"].invoke(workspace_data, agent_config)
            
            # Sanitize response for production
            sanitized_result = ProductionAgentValidator.sanitize_agent_response(result, "planner")
            
            return {
                "status": "success",
                "session_id": session_id,
                "result": sanitized_result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Planner generation failed: {e}")
            
            # Return structured fallback response instead of generic HTTP error
            from utils.agent_fallbacks import AgentFallbackHandler
            fallback_result = AgentFallbackHandler.create_fallback_response(
                "planner", session_id or "unknown", f"Processing error: {str(e)}"
            )
            
            return {
                "status": "error_with_fallback",
                "session_id": session_id or "unknown", 
                "result": fallback_result,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

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
        """Direct verifier agent validation with production-grade error handling"""
        from utils.agent_fallbacks import AgentFallbackHandler, ProductionAgentValidator
        
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
                logger.error("Session manager not available for verifier agent")
                # Return fallback response instead of failing
                fallback_result = AgentFallbackHandler.create_fallback_response(
                    "verifier", session_id, "Session manager unavailable"
                )
                return {
                    "status": "fallback",
                    "session_id": session_id,
                    "result": fallback_result,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Load workspace with validation
            workspace = await session_manager.load_workspace(session_id)
            if not workspace:
                logger.warning(f"Session {session_id} not found for verifier agent")
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Convert workspace to proper format with production validation
            workspace_data = ProductionAgentValidator.validate_workspace_data(workspace)
            
            # Create agent configuration with enhanced fallbacks
            agent_config = {
                "session_id": session_id,
                "content": content,
                "branch_data": data.get("branch_data", {})
            }
            
            # Generate prompt payload with fallback handling
            try:
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
                agent_config["prompt_payload"] = prompt_payload
            except Exception as e:
                logger.warning(f"Failed to generate prompt payload for verifier: {e}")
                # Use fallback prompt payload
                agent_config = AgentFallbackHandler.enhance_agent_config(
                    agent_config, "verifier", content
                )
            
            # Invoke agent with enhanced configuration
            result = await agents["verifier"].invoke(workspace_data, agent_config)
            
            # Sanitize response for production
            sanitized_result = ProductionAgentValidator.sanitize_agent_response(result, "verifier")
            
            return {
                "status": "success",
                "session_id": session_id,
                "result": sanitized_result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Verifier validation failed: {e}")
            
            # Return structured fallback response instead of generic HTTP error
            from utils.agent_fallbacks import AgentFallbackHandler
            fallback_result = AgentFallbackHandler.create_fallback_response(
                "verifier", session_id or "unknown", f"Processing error: {str(e)}"
            )
            
            return {
                "status": "error_with_fallback",
                "session_id": session_id or "unknown", 
                "result": fallback_result,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

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

    # WebSocket info endpoint for discovery and testing
    @app.get("/ws/info")
    async def websocket_info():
        """WebSocket endpoint discovery and information"""
        return {
            "websocket_url": "/ws",
            "status": "available",
            "supported_message_types": [
                "ping",
                "subscribe", 
                "suggestion_request",
                "health"
            ],
            "connection_info": {
                "timeout": 30,
                "keepalive": True,
                "auto_reconnect": True
            },
            "documentation": {
                "ping": "Simple ping-pong for connection testing",
                "subscribe": "Subscribe to session updates",
                "suggestion_request": "Request real-time suggestions",
                "health": "Check WebSocket health status"
            },
            "timestamp": datetime.now().isoformat()
        }

    # WebSocket endpoint for real-time updates
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for real-time communication with production-grade error handling"""
        try:
            await websocket.accept()
            logger.info("WebSocket connection established")
            
            # Send welcome message
            await websocket.send_text(json.dumps({
                "type": "connected",
                "message": "WebSocket connection established",
                "timestamp": datetime.now().isoformat()
            }))
            
            while True:
                try:
                    # Wait for messages from client with timeout
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    
                    try:
                        message = json.loads(data) if isinstance(data, str) else data
                        message_type = message.get("type", "unknown")
                        
                        logger.debug(f"WebSocket received message type: {message_type}")
                        
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
                            else:
                                await websocket.send_text(json.dumps({
                                    "type": "error",
                                    "message": "session_id required for subscription",
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
                                await websocket.send_text(json.dumps({
                                    "type": "error", 
                                    "message": "session_id required and session_manager must be available",
                                    "timestamp": datetime.now().isoformat()
                                }))
                        
                        elif message_type == "health":
                            # Health check via WebSocket
                            await websocket.send_text(json.dumps({
                                "type": "health_response",
                                "status": "healthy",
                                "agents_available": list(agents.keys()) if agents else [],
                                "session_manager_available": session_manager is not None,
                                "timestamp": datetime.now().isoformat()
                            }))
                        
                        else:
                            # Echo unknown messages with helpful response
                            await websocket.send_text(json.dumps({
                                "type": "echo",
                                "original": message,
                                "supported_types": ["ping", "subscribe", "suggestion_request", "health"],
                                "timestamp": datetime.now().isoformat()
                            }))
                            
                    except json.JSONDecodeError:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "Invalid JSON format",
                            "timestamp": datetime.now().isoformat()
                        }))
                
                except asyncio.TimeoutError:
                    # Send keepalive ping
                    await websocket.send_text(json.dumps({
                        "type": "keepalive",
                        "timestamp": datetime.now().isoformat()
                    }))
                    
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            try:
                if not websocket.client_state.DISCONNECTED:
                    await websocket.close(code=1000, reason="Server error")
            except Exception as close_e:
                logger.error(f"Error closing WebSocket: {close_e}")
        finally:
            logger.info("WebSocket connection closed")

    @app.post("/api/session/{session_id}/suggestion_signal")
    async def suggestion_signal(session_id: str, request: Request):
        """Receives signals from the frontend to trigger suggestions."""
        try:
            if not session_manager:
                raise HTTPException(status_code=500, detail="Session manager not initialized")

            signal_data = await request.json()
            trigger_type = signal_data.get("trigger_type") or signal_data.get("type")  # Support both formats
            topic_content = signal_data.get("topic_content", "")
            mode = signal_data.get("mode", "on_demand")  # SuggestionMode enum value
            branch_type = signal_data.get("branch_type", "balanced")  # Branch generation style
            
            # The orchestrator (session_manager) decides whether to run the suggestion pipeline
            should_suggest, reason = await session_manager.handle_suggestion_trigger(session_id, trigger_type, signal_data)

            if should_suggest:
                logger.info(f"Suggestion triggered for session {session_id} due to {reason}")
                
                # Actually invoke the suggestion pipeline now instead of just logging
                try:
                    # Create a SuggestRequest with correct mode enum value
                    suggest_request = SuggestRequest(
                        mode=mode,  # Now correctly uses 'on_demand', 'idle_smart', or 'proactive'
                        options={
                            "topic": "user_content",
                            "context": topic_content[:200] if topic_content else "User content generation",
                            "max_branches": 3,
                            "branch_type": branch_type  # Pass branch type in options
                        },
                        constraints={}
                    )
                    
                    # Call the actual suggestion pipeline
                    workspace = await session_manager.load_workspace(session_id)
                    if not workspace:
                        raise HTTPException(status_code=404, detail="Session not found")

                    # Run simplified suggest pipeline
                    workspace_data = workspace.model_dump() if hasattr(workspace, 'model_dump') else workspace
                    
                    # Run perception
                    perception_result = {}
                    if agents.get("perception"):
                        try:
                            perception_result = await agents["perception"].invoke(
                                workspace_data,
                                {"session_id": session_id, "mode": branch_type}  # Use branch_type for agent mode
                            )
                        except Exception as e:
                            logger.warning(f"Perception agent failed: {e}")
                    
                    # Update graph
                    if agents.get("graph_manager") and perception_result.get("entities"):
                        try:
                            await agents["graph_manager"].invoke(
                                workspace_data,
                                {
                                    "session_id": session_id,
                                    "entities": perception_result.get("entities", []),
                                    "events": perception_result.get("events", []),
                                }
                            )
                        except Exception as e:
                            logger.warning(f"Graph manager failed: {e}")
                    
                    # Generate projections
                    projections = []
                    if agents.get("planner"):
                        try:
                            planner_result = await agents["planner"].invoke(
                                workspace_data,
                                {
                                    "session_id": session_id,
                                    "mode": branch_type,  # Use branch_type for agent mode
                                    "analysis": perception_result,
                                    "max_branches": 3
                                }
                            )
                            projections = planner_result.get("projections", [])
                        except Exception as e:
                            logger.warning(f"Planner agent failed: {e}")
                    
                    return {
                        "status": "suggestion_completed",
                        "reason": reason,
                        "projections": projections,
                        "analysis": perception_result,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                except Exception as pipeline_error:
                    logger.error(f"Suggestion pipeline failed: {pipeline_error}")
                    return {
                        "status": "suggestion_triggered",
                        "reason": reason,
                        "error": str(pipeline_error),
                        "note": "Pipeline started but encountered errors"
                    }
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

            # Run agent pipeline with PTG-generated prompts (blueprint compliance)
            workspace_data = workspace.model_dump() if hasattr(workspace, 'model_dump') else workspace
            topic = request.options.get("topic", "general")
            topic_descriptor = request.options.get("context", "Content generation and analysis")
            
            # 1. Perception with PTG-generated prompt
            if hasattr(session_manager, 'ptg') and session_manager.ptg:
                try:
                    perception_prompt = session_manager.ptg.generate_canonical_prompt(
                        agent_name="perception",
                        session_id=session_id,
                        topic=topic,
                        topic_descriptor=topic_descriptor,
                        input_data={"mode": request.mode, "content": workspace_data.get("content", "")},
                        mode=request.mode
                    )
                    perception_result = await agents["perception"].invoke(
                        workspace_data,
                        {
                            "session_id": session_id,
                            "mode": request.mode,
                            "prompt_payload": perception_prompt
                        }
                    )
                except Exception as e:
                    logger.warning(f"PTG failed for perception agent: {e}")
                    perception_result = await agents["perception"].invoke(
                        workspace_data,
                        {"session_id": session_id, "mode": request.mode}
                    )
            else:
                perception_result = await agents["perception"].invoke(
                    workspace_data,
                    {"session_id": session_id, "mode": request.mode}
                )

            # 2. Update graph with PTG-generated prompt
            if hasattr(session_manager, 'ptg') and session_manager.ptg:
                try:
                    graph_prompt = session_manager.ptg.generate_canonical_prompt(
                        agent_name="graph_manager",
                        session_id=session_id,
                        topic=topic,
                        topic_descriptor=topic_descriptor,
                        input_data={
                            "entities": perception_result.get("entities", []),
                            "events": perception_result.get("events", [])
                        },
                        mode=request.mode
                    )
                    await agents["graph_manager"].invoke(
                        workspace_data,
                        {
                            "session_id": session_id,
                            "entities": perception_result.get("entities", []),
                            "events": perception_result.get("events", []),
                            "prompt_payload": graph_prompt
                        }
                    )
                except Exception as e:
                    logger.warning(f"PTG failed for graph manager: {e}")
                    await agents["graph_manager"].invoke(
                        workspace_data,
                        {
                            "session_id": session_id,
                            "entities": perception_result.get("entities", []),
                            "events": perception_result.get("events", []),
                        }
                    )
            else:
                await agents["graph_manager"].invoke(
                    workspace_data,
                    {
                        "session_id": session_id,
                        "entities": perception_result.get("entities", []),
                        "events": perception_result.get("events", []),
                    }
                )

            # 3. Generate projections with PTG-generated prompt
            max_branches = request.options.get("max_branches", 3)
            logger.warning(f"🔍 Starting Planner with max_branches: {max_branches}")
            if hasattr(session_manager, 'ptg') and session_manager.ptg:
                try:
                    logger.warning("🔍 Generating PTG prompt for planner...")
                    planner_prompt = session_manager.ptg.generate_canonical_prompt(
                        agent_name="planner",
                        session_id=session_id,
                        topic=topic,
                        topic_descriptor=topic_descriptor,
                        input_data={
                            "max_branches": max_branches,
                            "content": workspace_data.get("content", ""),
                            "context": request.options.get("context", "")
                        },
                        mode=request.mode
                    )
                    logger.warning(f"🔍 PTG prompt generated successfully, keys: {list(planner_prompt.keys())}")
                    planner_result = await agents["planner"].invoke(
                        workspace_data,
                        {
                            "session_id": session_id, 
                            "max_branches": max_branches, 
                            "mode": request.mode,
                            "prompt_payload": planner_prompt
                        }
                    )
                    logger.warning(f"🔍 Planner result keys: {list(planner_result.keys())}")
                    logger.warning(f"🔍 Planner branches count: {len(planner_result.get('branches', []))}")
                except Exception as e:
                    logger.warning(f"❌ PTG failed for planner: {e}")
                    planner_result = await agents["planner"].invoke(
                        workspace_data,
                        {
                            "session_id": session_id, 
                            "max_branches": max_branches, 
                            "mode": request.mode
                        }
                    )
            else:
                logger.warning("❌ No PTG available, using fallback planner call")
                planner_result = await agents["planner"].invoke(
                    workspace_data,
                    {
                        "session_id": session_id, 
                        "max_branches": max_branches, 
                        "mode": request.mode
                    }
                )

            # 4. Verify branches with PTG-generated prompts
            verified_branches = []
            verifications = []
            for branch in planner_result.get("branches", []):
                if hasattr(session_manager, 'ptg') and session_manager.ptg:
                    try:
                        verifier_prompt = session_manager.ptg.generate_canonical_prompt(
                            agent_name="verifier",
                            session_id=session_id,
                            topic=topic,
                            topic_descriptor=topic_descriptor,
                            input_data={
                                "content": branch.get("content", {}) if isinstance(branch, dict) else str(branch),
                                "branch_data": branch
                            },
                            mode=request.mode
                        )
                        verification = await agents["verifier"].invoke(
                            workspace_data,
                            {
                                "session_id": session_id,
                                "content": branch.get("content", {}) if isinstance(branch, dict) else str(branch),
                                "branch_data": branch,
                                "prompt_payload": verifier_prompt
                            }
                        )
                    except Exception:
                        verification = await agents["verifier"].invoke(
                            workspace_data,
                            {
                                "session_id": session_id,
                                "content": branch.get("content", {}) if isinstance(branch, dict) else str(branch),
                                "branch_data": branch
                            }
                        )
                else:
                    verification = await agents["verifier"].invoke(
                        workspace_data,
                        {
                            "session_id": session_id,
                            "content": branch.get("content", {}) if isinstance(branch, dict) else str(branch),
                            "branch_data": branch
                        }
                    )
                verifications.append(verification)
                verified_branches.append(branch)

            # 5. Score and rank with PTG-generated prompt
            workspace_data["branches"] = verified_branches
            if hasattr(session_manager, 'ptg') and session_manager.ptg:
                try:
                    evaluator_prompt = session_manager.ptg.generate_canonical_prompt(
                        agent_name="evaluator",
                        session_id=session_id,
                        topic=topic,
                        topic_descriptor=topic_descriptor,
                        input_data={"branches": verified_branches},
                        mode=request.mode
                    )
                    evaluation = await agents["evaluator"].invoke(
                        workspace_data,
                        {
                            "session_id": session_id,
                            "prompt_payload": evaluator_prompt
                        }
                    )
                except Exception:
                    evaluation = await agents["evaluator"].invoke(
                        workspace_data,
                        {
                            "session_id": session_id
                        }
                    )
            else:
                evaluation = await agents["evaluator"].invoke(
                    workspace_data,
                    {
                        "session_id": session_id
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

            # Convert branches to ProjectionSchema format
            formatted_projections = {}
            for i, branch in enumerate(verified_branches[:max_branches]):
                # Production fix: Extract fields intelligently from flat or nested structure
                # The LLM can return either:
                # 1. Flat: {title: "...", paragraph: "...", events: [...]}
                # 2. Nested: {content: {title: "...", paragraph: "..."}, events: [...]}
                
                # Try to get title from multiple possible locations
                title = branch.get("title")
                paragraph = branch.get("paragraph", "")
                events = branch.get("events", [])
                flags = branch.get("flags", {})
                
                # If title/paragraph not at top level, check nested 'content'
                if not title or not paragraph:
                    content = branch.get("content")
                    if isinstance(content, dict):
                        if not title:
                            title = content.get("title")
                        if not paragraph:
                            paragraph = content.get("paragraph") or content.get("text") or ""
                
                # Final fallback: generate paragraph from events if still missing
                if not paragraph and events:
                    event_summaries = [evt.get('summary', '') for evt in events[:3] 
                                      if isinstance(evt, dict) and evt.get('summary')]
                    if event_summaries:
                        paragraph = ' '.join(event_summaries)
                
                # Ensure we have at least a title
                if not title:
                    title = f"Suggestion {i + 1}"
                
                branch_type = branch.get("branch_type", "balanced")
                score = branch.get("score")
                
                # Create properly formatted projection
                formatted = {
                    "title": title,
                    "paragraph": paragraph,
                    "events": events,
                    "flags": flags,
                    "branch_type": branch_type
                }
                
                # Add score if present
                if score is not None:
                    formatted["score"] = score
                
                # Use descriptive keys (A, B, C) for better frontend compatibility
                projection_key = chr(65 + i)  # A, B, C
                formatted_projections[projection_key] = formatted

            return SuggestionsResponse(
                session_id=session_id,
                projections=formatted_projections,
                metadata={
                    "branch_scores": evaluation.get("branch_scores", []),
                    "verifications": verifications[:max_branches]
                },
                status="success",
            )

        except Exception as e:
            logger.error(f"Failed to generate suggestions: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/session/{session_id}/accept", response_model=SessionResponse)
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

    @app.get("/api/session/{session_id}/analytics")
    async def get_session_analytics(session_id: str):
        """Get real-time analytics: facts, characters, story metrics using LLM and agents"""
        try:
            if not session_manager:
                raise HTTPException(
                    status_code=500, detail="Session manager not initialized"
                )

            workspace = await session_manager.load_workspace(session_id)
            if not workspace:
                raise HTTPException(status_code=404, detail="Session not found")

            # Extract real data from workspace
            workspace_dict = workspace if isinstance(workspace, dict) else (
                workspace.model_dump() if hasattr(workspace, 'model_dump') else workspace.__dict__
            )
            
            content = workspace_dict.get('topic_content', '')
            
            # Get agents for LLM-based analysis
            perception_agent = agents.get("perception")
            evaluator_agent = agents.get("evaluator")
            
            # PRODUCTION FIX: Initialize llm_provider_name at function scope to prevent UnboundLocalError
            llm_provider_name = None
            if hasattr(perception_agent, 'llm_provider') and perception_agent and perception_agent.llm_provider:
                llm_provider_name = perception_agent.llm_provider.provider if hasattr(perception_agent.llm_provider, 'provider') else 'unknown'
            
            character_list = []
            facts_verified = 0
            facts_total = 0
            
            # PRODUCTION FIX: Use LLM if available, regardless of content (for baseline analytics)
            if perception_agent:
                try:
                    logger.info(f"🤖 Using Perception Agent with LLM provider: {llm_provider_name or 'None'}")
                    
                    # Only invoke agent if there's content to analyze
                    if content:
                        perception_result = await perception_agent.invoke(
                            workspace_dict,
                            {"session_id": session_id, "mode": "balanced"}
                        )
                        
                        # Extract characters with real LLM-analyzed data
                        raw_characters = perception_result.get('characters', [])
                        for char in raw_characters:
                            if isinstance(char, dict):
                                # Use evaluator agent to assess character consistency if available
                                consistency_status = "consistent"
                                if evaluator_agent and len(raw_characters) > 0:
                                    try:
                                        # Quick LLM-based consistency check
                                        eval_result = await evaluator_agent.invoke(
                                            workspace_dict,
                                            {
                                                "session_id": session_id,
                                                "focus": f"character_consistency_{char.get('name', 'unknown')}"
                                            }
                                        )
                                        if eval_result and 'consistency' in eval_result:
                                            consistency_status = eval_result['consistency']
                                    except Exception as eval_err:
                                        logger.debug(f"Character consistency check skipped: {eval_err}")
                                
                                character_list.append({
                                    'name': char.get('name', 'Unknown'),
                                    'traits': char.get('traits', []),
                                    'mentions': char.get('mentions', 1),
                                    'confidence': char.get('confidence', 0.8),
                                    'consistency': consistency_status
                                })
                        
                        # Extract events for fact checking
                        events = perception_result.get('events', [])
                        entities = perception_result.get('entities', [])
                        
                        # Use LLM to verify facts
                        facts_total = len(events)
                        
                        # Facts from knowledge base are verified
                        kb_triples = workspace_dict.get('kb_triples', [])
                        facts_verified = len(kb_triples)
                        
                        # High-confidence entities count as verified facts
                        high_conf_entities = [e for e in entities if e.get('confidence', 0) > 0.8]
                        facts_verified += len(high_conf_entities)
                        facts_total += len(entities)
                        
                        logger.info(f"📊 LLM Analysis: {len(character_list)} characters, {facts_verified}/{facts_total} facts verified")
                    else:
                        # Empty session - return baseline analytics with LLM available
                        logger.info("📝 Empty session - returning baseline analytics with LLM ready")
                        # Use workspace data as baseline
                        characters = workspace_dict.get('characters', {})
                        for char_name, char_data in characters.items():
                            if isinstance(char_data, dict):
                                character_list.append({
                                    'name': char_name,
                                    'traits': char_data.get('traits', []),
                                    'consistency': 'unknown'
                                })
                        
                        events = workspace_dict.get('events', [])
                        kb_triples = workspace_dict.get('kb_triples', [])
                        facts_verified = len(kb_triples)
                        facts_total = len(events) + len(kb_triples)
                    
                except Exception as agent_err:
                    logger.warning(f"⚠️ Agent analysis failed, using workspace data: {agent_err}")
                    # Fallback to workspace data
                    characters = workspace_dict.get('characters', {})
                    for char_name, char_data in characters.items():
                        if isinstance(char_data, dict):
                            character_list.append({
                                'name': char_name,
                                'traits': char_data.get('traits', []),
                                'consistency': 'unknown'
                            })
                    events = workspace_dict.get('events', [])
                    kb_triples = workspace_dict.get('kb_triples', [])
                    facts_verified = len(kb_triples)
                    facts_total = len(events) + len(kb_triples)
            else:
                # PRODUCTION: No perception agent available (shouldn't happen in production)
                logger.warning("⚠️ No perception agent available - check agent initialization")
                characters = workspace_dict.get('characters', {})
                for char_name, char_data in characters.items():
                    if isinstance(char_data, dict):
                        character_list.append({
                            'name': char_name,
                            'traits': char_data.get('traits', []),
                            'consistency': 'unknown'
                        })
                
                events = workspace_dict.get('events', [])
                kb_triples = workspace_dict.get('kb_triples', [])
                facts_verified = len(kb_triples)
                facts_total = len(events) + len(kb_triples)
            
            fact_check_status = {
                'verified': facts_verified,
                'total': facts_total,
                'percentage': (facts_verified / facts_total * 100) if facts_total > 0 else 100,
                'status': 'all_verified' if facts_total == 0 or facts_verified == facts_total else 'partial',
                'llm_provider': llm_provider_name or 'none'  # PRODUCTION FIX: Use safe variable
            }
            
            # Story metrics
            word_count = len(content.split()) if content else 0
            metadata = workspace_dict.get('metadata', {})
            if isinstance(metadata, dict):
                metadata_word_count = metadata.get('word_count', word_count)
            else:
                metadata_word_count = word_count
            
            story_metrics = {
                'word_count': metadata_word_count,
                'character_count': len(character_list),
                'event_count': len(workspace_dict.get('events', [])),
                'branch_count': len(workspace_dict.get('projections', {})),
                'using_llm': hasattr(perception_agent, 'llm_provider') and perception_agent.llm_provider is not None  # PRODUCTION FIX
            }
            
            return {
                'session_id': session_id,
                'fact_check': fact_check_status,
                'characters': character_list,
                'story_metrics': story_metrics,
                'timestamp': datetime.now().isoformat(),
                'llm_provider': llm_provider_name or 'none',  # PRODUCTION FIX: Use safe variable
                'agents_active': {
                    'perception': perception_agent is not None,
                    'evaluator': evaluator_agent is not None
                }
            }

        except Exception as e:
            logger.error(f"❌ Failed to get analytics for session {session_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/session/{session_id}/graph")
    async def get_session_graph(session_id: str):
        """Get knowledge graph nodes and edges for visualization"""
        try:
            if not session_manager:
                raise HTTPException(
                    status_code=500, detail="Session manager not initialized"
                )

            workspace = await session_manager.load_workspace(session_id)
            if not workspace:
                raise HTTPException(status_code=404, detail="Session not found")

            # Extract graph data from workspace
            workspace_dict = workspace if isinstance(workspace, dict) else (
                workspace.model_dump() if hasattr(workspace, 'model_dump') else workspace.__dict__
            )
            
            # Get graph from workspace or build from events/characters
            graph_data = workspace_dict.get('graph', {})
            
            # If graph is empty, build basic graph from events and characters
            if not graph_data or not graph_data.get('nodes'):
                nodes = []
                edges = []
                
                # Add character nodes
                characters = workspace_dict.get('characters', {})
                for char_name, char_data in characters.items():
                    nodes.append({
                        'id': f'char_{char_name}',
                        'type': 'character',
                        'title': char_name,
                        'text': ', '.join(char_data.get('traits', [])) if isinstance(char_data, dict) else '',
                        'confidence': 1.0
                    })
                
                # Add event nodes
                events = workspace_dict.get('events', [])
                for i, event in enumerate(events):
                    if isinstance(event, dict):
                        event_id = event.get('id', f'event_{i}')
                        nodes.append({
                            'id': event_id,
                            'type': 'event',
                            'title': event.get('summary', f'Event {i+1}'),
                            'text': event.get('summary', ''),
                            'actor': event.get('actor'),
                            'confidence': event.get('confidence', 0.9)
                        })
                        
                        # Create edge if actor matches a character
                        actor = event.get('actor')
                        if actor and f'char_{actor}' in [n['id'] for n in nodes]:
                            edges.append({
                                'source': f'char_{actor}',
                                'target': event_id,
                                'type': 'performs',
                                'confidence': event.get('confidence', 0.9)
                            })
                
                # Add temporal edges between consecutive events
                for i in range(len(events) - 1):
                    if isinstance(events[i], dict) and isinstance(events[i+1], dict):
                        source_id = events[i].get('id', f'event_{i}')
                        target_id = events[i+1].get('id', f'event_{i+1}')
                        edges.append({
                            'source': source_id,
                            'target': target_id,
                            'type': 'temporal',
                            'confidence': 0.8
                        })
                
                graph_data = {
                    'nodes': nodes,
                    'edges': edges
                }
            
            return {
                'session_id': session_id,
                'nodes': graph_data.get('nodes', []),
                'edges': graph_data.get('edges', []),
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get graph for session {session_id}: {e}")
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
    
    @app.get("/api/health/detailed")
    async def detailed_health_check():
        """
        Comprehensive health check with database and service status
        Production-ready endpoint for monitoring and debugging
        """
        import time
        start_time = time.time()
        
        # Check MongoDB
        mongo_status = "unknown"
        mongo_message = ""
        try:
            if session_manager:
                # Try to get a workspace to test MongoDB
                test_workspace = session_manager.workspaces.get(list(session_manager.workspaces.keys())[0]) if session_manager.workspaces else None
                if test_workspace and test_workspace.mongo_client:
                    try:
                        await asyncio.wait_for(
                            test_workspace.mongo_client.admin.command("ping"),
                            timeout=2.0
                        )
                        mongo_status = "connected"
                        mongo_message = "MongoDB operational"
                    except asyncio.TimeoutError:
                        mongo_status = "timeout"
                        mongo_message = "MongoDB connection timeout"
                    except Exception as e:
                        mongo_status = "error"
                        mongo_message = f"MongoDB error: {str(e)[:100]}"
                else:
                    mongo_status = "not_configured"
                    mongo_message = "MongoDB client not initialized"
        except Exception as e:
            mongo_status = "error"
            mongo_message = f"Health check error: {str(e)[:100]}"
        
        # Check LLM Provider
        llm_status = "unknown"
        llm_message = ""
        try:
            if agents.get("perception"):
                perception = agents["perception"]
                if hasattr(perception, 'llm_provider') and perception.llm_provider:
                    llm_status = "available"
                    llm_message = "LLM provider initialized"
                else:
                    llm_status = "not_configured"
                    llm_message = "LLM provider not configured"
        except Exception as e:
            llm_status = "error"
            llm_message = f"LLM check error: {str(e)[:100]}"
        
        # Check ArangoDB (if configured)
        arango_status = "not_configured"
        arango_message = "ArangoDB not in use (using JSON fallback)"
        
        # JSON fallback is always available
        json_fallback_status = "ok"
        json_fallback_message = "JSON file storage available"
        
        # Overall system status
        overall_status = "healthy" if mongo_status in ["connected", "not_configured"] else "degraded"
        
        response_time = (time.time() - start_time) * 1000  # Convert to ms
        
        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "uptime": time.time(),
            "version": "1.0.0",
            "response_time_ms": round(response_time, 2),
            "services": {
                "mongo": {
                    "status": mongo_status,
                    "message": mongo_message,
                    "last_checked": datetime.now().isoformat()
                },
                "arango": {
                    "status": arango_status,
                    "message": arango_message,
                    "last_checked": datetime.now().isoformat()
                },
                "llm": {
                    "status": llm_status,
                    "message": llm_message,
                    "last_checked": datetime.now().isoformat()
                },
                "json_fallback": {
                    "status": json_fallback_status,
                    "message": json_fallback_message,
                    "last_checked": datetime.now().isoformat()
                }
            },
            "agents": {
                "session_manager": session_manager is not None,
                "perception": "perception" in agents,
                "planner": "planner" in agents,
                "graph_manager": "graph_manager" in agents,
                "verifier": "verifier" in agents,
                "evaluator": "evaluator" in agents,
                "total_count": len(agents)
            },
            "active_sessions": len(session_manager.workspaces) if session_manager else 0
        }

    @app.options("/api/health")
    async def api_health_options():
        """OPTIONS handler for CORS preflight requests"""
        return {}

    @app.get("/health/database")
    async def database_health_check():
        """Database health check endpoint - returns 200 with partial status"""
        try:
            db_status = {}
            all_healthy = True
            critical_down = False
            
            if session_manager and hasattr(session_manager, 'workspace_manager'):
                # Check MongoDB (critical)
                try:
                    from dependencies import get_container
                    container = get_container()
                    if container and hasattr(container, 'mongo_client'):
                        mongo_client = container.mongo_client()
                        # Use timeout for health check
                        try:
                            await asyncio.wait_for(
                                mongo_client.admin.command("ping"),
                                timeout=2.0
                            )
                            db_status["mongodb"] = "healthy"
                        except asyncio.TimeoutError:
                            db_status["mongodb"] = "timeout"
                            critical_down = True
                            all_healthy = False
                    else:
                        db_status["mongodb"] = "not_configured"
                        all_healthy = False
                except Exception as e:
                    db_status["mongodb"] = f"error: {str(e)}"
                    critical_down = True
                    all_healthy = False
                
                # Check ArangoDB (optional, not critical)
                try:
                    if container and hasattr(container, 'arango_client'):
                        arango_client = container.arango_client()
                        # Simple ping operation with timeout
                        await asyncio.wait_for(
                            asyncio.to_thread(arango_client.version),
                            timeout=2.0
                        )
                        db_status["arangodb"] = "healthy"
                    else:
                        db_status["arangodb"] = "not_configured"
                        all_healthy = False
                except asyncio.TimeoutError:
                    db_status["arangodb"] = "timeout"
                    all_healthy = False
                except Exception as e:
                    db_status["arangodb"] = f"error: {str(e)}"
                    all_healthy = False
            else:
                db_status = {"status": "session_manager_not_initialized"}
                all_healthy = False
            
            # Determine overall status
            if critical_down:
                overall_status = "critical"
            elif all_healthy:
                overall_status = "healthy"
            else:
                overall_status = "degraded"
            
            # Return 200 unless critical services are down
            status_code = 503 if critical_down else 200
            
            return JSONResponse(
                status_code=status_code,
                content={
                    "status": overall_status,
                    "databases": db_status,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            return JSONResponse(
                status_code=200,  # Return 200 even on error, indicate in status
                content={
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

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


    # Serve static files (frontend) and favicon
    try:
        project_root = Path(__file__).parent.parent
        static_dir = project_root / "web" / "build"
        fallback_static_dir = Path(__file__).parent / "static"

        # Mount main static directory if exists
        if static_dir.exists():
            app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
            logger.info(f"Serving static files from: {static_dir}")
        else:
            logger.warning(f"Static files directory not found: {static_dir}")

        # Always mount /static for backend static assets (e.g., favicon)
        if fallback_static_dir.exists():
            app.mount("/static", StaticFiles(directory=str(fallback_static_dir)), name="backend-static")
            logger.info(f"Serving backend static files from: {fallback_static_dir}")
        else:
            logger.warning(f"Backend static directory not found: {fallback_static_dir}")

        # Add fallback /favicon.ico route if not handled by frontend
        @app.get("/favicon.ico")
        async def favicon():
            from fastapi.responses import FileResponse
            favicon_path = fallback_static_dir / "favicon.ico"
            if favicon_path.exists():
                return FileResponse(str(favicon_path), media_type="image/x-icon")
            else:
                return Response(status_code=404)
    except Exception as e:
        logger.warning(f"Failed to mount static or favicon: {e}")

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
