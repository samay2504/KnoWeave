from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import logging
from datetime import datetime

try:
    from ..agents.session_manager import SessionManager
    from ..constants import PTG_MODES, BACKEND_PORT
except ImportError:
    try:
        from agents.session_manager import SessionManager
        from constants import PTG_MODES, BACKEND_PORT
    except ImportError:
        # Fallback if SessionManager not available
        class SessionManager:
            def __init__(self):
                self.current_mode = 'balanced'
                self.ptg = self
            
            def generate_canonical_prompt(self, user_prompt, agent_type="general", mode="balanced"):
                return f"[{mode.upper()} MODE] {user_prompt}"
        
        PTG_MODES = {
            'conservative': {'name': 'Conservative', 'temperature': 0.3},
            'balanced': {'name': 'Balanced', 'temperature': 0.5},
            'exploratory': {'name': 'Exploratory', 'temperature': 0.8},
            'focused': {'name': 'Focused', 'temperature': 0.2},
        }
        BACKEND_PORT = 8000

logger = logging.getLogger(__name__)

# Initialize router
mode_router = APIRouter(prefix="/api/session", tags=["mode"])

# Pydantic models for request/response
class ModeUpdateRequest(BaseModel):
    mode: str = Field(..., description="Mode to set (conservative, balanced, exploratory, focused)")
    config: Optional[Dict[str, Any]] = Field(None, description="Optional mode configuration")

class ModeUpdateResponse(BaseModel):
    status: str
    mode: str
    config: Dict[str, Any]
    timestamp: datetime

class PromptGenerationRequest(BaseModel):
    user_prompt: str = Field(..., description="User's input prompt")
    agent_type: str = Field(default="general", description="Type of agent to use")
    mode: Optional[str] = Field(None, description="Override mode for this request")
    mode_config: Optional[Dict[str, Any]] = Field(None, description="Override mode config")

class PromptGenerationResponse(BaseModel):
    canonical_prompt: str
    mode: str
    agent_type: str
    metadata: Dict[str, Any]

# Dependency to get session manager
async def get_session_manager() -> SessionManager:
    """Get the global session manager instance"""
    # Import at runtime to avoid circular imports
    import sys
    app_module = sys.modules.get('server.app')
    if app_module is None:
        # Try alternative import
        try:
            from server import app as app_module
        except ImportError:
            try:
                import app as app_module
            except ImportError:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Unable to access application module"
                )
    
    session_manager = getattr(app_module, 'session_manager', None)
    if session_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session manager not initialized"
        )
    return session_manager

@mode_router.post("/mode", response_model=ModeUpdateResponse)
async def update_mode(
    request: ModeUpdateRequest,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Update the current AI interaction mode
    """
    try:
        # Validate mode
        if request.mode not in PTG_MODES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mode. Must be one of: {list(PTG_MODES.keys())}"
            )

        # Update session manager mode
        session_manager.current_mode = request.mode
        
        # Get mode configuration
        mode_config = PTG_MODES[request.mode].copy()
        if request.config:
            mode_config.update(request.config)

        logger.info(f"Mode updated to: {request.mode}")

        return ModeUpdateResponse(
            status="success",
            mode=request.mode,
            config=mode_config,
            timestamp=datetime.now()
        )

    except Exception as e:
        logger.error(f"Error updating mode: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@mode_router.get("/modes")
async def get_available_modes():
    """
    Get all available AI interaction modes
    """
    try:
        modes_data = {}
        for mode_key, mode_config in PTG_MODES.items():
            modes_data[mode_key] = {
                "name": mode_config.get("name", mode_key.title()),
                "description": mode_config.get("description", ""),
                "temperature": mode_config.get("temperature", 0.5),
                "creativity": mode_config.get("creativity", 0.5),
                "consistency": mode_config.get("consistency", 0.5),
            }

        return {
            "modes": modes_data,
            "default_mode": "balanced"
        }

    except Exception as e:
        logger.error(f"Error getting available modes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@mode_router.get("/mode")
async def get_current_mode(
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Get the current AI interaction mode
    """
    try:
        current_mode = getattr(session_manager, 'current_mode', 'balanced')
        mode_config = PTG_MODES.get(current_mode, PTG_MODES['balanced'])

        return {
            "mode": current_mode,
            "config": mode_config,
            "timestamp": datetime.now()
        }

    except Exception as e:
        logger.error(f"Error getting current mode: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# PTG router for prompt generation
ptg_router = APIRouter(prefix="/api/ptg", tags=["ptg"])

@ptg_router.post("/generate", response_model=PromptGenerationResponse)
async def generate_prompt(
    request: PromptGenerationRequest,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Generate a canonical prompt using the PTG system with mode-specific instructions
    """
    try:
        # Determine mode to use
        mode = request.mode or getattr(session_manager, 'current_mode', 'balanced')
        
        # Validate mode
        if mode not in PTG_MODES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mode. Must be one of: {list(PTG_MODES.keys())}"
            )

        # Generate canonical prompt using PTG
        canonical_prompt = session_manager.ptg.generate_canonical_prompt(
            user_prompt=request.user_prompt,
            agent_type=request.agent_type,
            mode=mode
        )

        # Get mode configuration
        mode_config = PTG_MODES[mode].copy()
        if request.mode_config:
            mode_config.update(request.mode_config)

        logger.info(f"Generated prompt for mode: {mode}, agent: {request.agent_type}")

        return PromptGenerationResponse(
            canonical_prompt=canonical_prompt,
            mode=mode,
            agent_type=request.agent_type,
            metadata={
                "mode_config": mode_config,
                "timestamp": datetime.now().isoformat(),
                "prompt_length": len(canonical_prompt),
                "user_prompt_length": len(request.user_prompt)
            }
        )

    except Exception as e:
        logger.error(f"Error generating prompt: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@ptg_router.get("/status")
async def get_ptg_status(
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Get PTG system status and capabilities
    """
    try:
        return {
            "status": "active",
            "available_modes": list(PTG_MODES.keys()),
            "current_mode": getattr(session_manager, 'current_mode', 'balanced'),
            "ptg_version": "1.0.0",
            "supported_agents": [
                "general", "creative", "analytical", 
                "technical", "research", "writing"
            ]
        }

    except Exception as e:
        logger.error(f"Error getting PTG status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
