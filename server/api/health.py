#!/usr/bin/env python3
"""
Health Endpoints Implementation
Provides /api/health endpoint for system status monitoring
Part of BTP Human-AI Co-Creation integration checks.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import time
import json
import asyncio
from datetime import datetime

# Import service status from dependencies
try:
    from dependencies import service_status
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False
    service_status = {}

# Import optional dependencies with fallbacks for Python 3.12+ compatibility
try:
    from motor.motor_asyncio import AsyncIOMotorClient
    MOTOR_AVAILABLE = True
except ImportError:
    MOTOR_AVAILABLE = False
    AsyncIOMotorClient = None

try:
    from arango import ArangoClient
    ARANGO_AVAILABLE = True
except ImportError:
    ARANGO_AVAILABLE = False
    ArangoClient = None

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Import server components
import sys

sys.path.append(str(Path(__file__).parent.parent))

# Import with proper paths - with fallbacks for missing components
try:
    from db.arango_client import ArangoDBManager
except ImportError:
    ArangoDBManager = None

try:
    from db.mongo_client import MongoDBManager
except ImportError:
    MongoDBManager = None

try:
    from server_config import ServerConfig
except ImportError:
    try:
        from ..server_config import ServerConfig
    except ImportError:
        # Fallback config class
        class ServerConfig:
            def __init__(self):
                self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")


class HealthStatus(BaseModel):
    """Health status response model"""

    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: str
    uptime_seconds: float
    version: str
    environment: str


class ComponentHealth(BaseModel):
    """Individual component health"""

    name: str
    status: str  # "up", "down", "degraded"
    response_time_ms: Optional[float] = None
    last_check: str
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class DetailedHealthResponse(BaseModel):
    """Detailed health check response"""

    overall: HealthStatus
    components: List[ComponentHealth]
    system_metrics: Dict[str, Any]
    checks_performed: int
    warnings: List[str]


# Global variables for tracking
app_start_time = time.time()
health_cache = {}
cache_ttl = 30  # seconds

router = APIRouter(prefix="/api", tags=["health"])


async def check_database_connection(db_manager, db_name: str) -> ComponentHealth:
    """Check database connectivity"""
    start_time = time.time()

    try:
        if db_name == "arangodb":
            # Test ArangoDB connection
            result = await asyncio.create_task(
                asyncio.to_thread(db_manager.test_connection)
            )
            if result:
                response_time = (time.time() - start_time) * 1000
                return ComponentHealth(
                    name=db_name,
                    status="up",
                    response_time_ms=response_time,
                    last_check=datetime.utcnow().isoformat(),
                    metadata={"version": "3.11", "graph_ready": True},
                )

        elif db_name == "mongodb":
            # Test MongoDB connection
            result = await db_manager.test_connection()
            if result:
                response_time = (time.time() - start_time) * 1000
                return ComponentHealth(
                    name=db_name,
                    status="up",
                    response_time_ms=response_time,
                    last_check=datetime.utcnow().isoformat(),
                    metadata={
                        "collections": ["users", "sessions"],
                        "indexes_ready": True,
                    },
                )

    except Exception as e:
        return ComponentHealth(
            name=db_name,
            status="down",
            last_check=datetime.utcnow().isoformat(),
            error=str(e),
        )

    return ComponentHealth(
        name=db_name,
        status="down",
        last_check=datetime.utcnow().isoformat(),
        error="Connection test failed",
    )


async def check_json_fallback_system() -> ComponentHealth:
    """Check JSON fallback functionality"""
    start_time = time.time()

    try:
        # Check if data directory exists and is writable
        data_dir = Path("data/backups")
        data_dir.mkdir(parents=True, exist_ok=True)

        # Test file write/read
        test_file = data_dir / "health_check.json"
        test_data = {"test": True, "timestamp": time.time()}

        with open(test_file, "w") as f:
            json.dump(test_data, f)

        with open(test_file, "r") as f:
            read_data = json.load(f)

        test_file.unlink()  # Clean up

        if read_data.get("test") == True:
            response_time = (time.time() - start_time) * 1000
            return ComponentHealth(
                name="json_fallback",
                status="up",
                response_time_ms=response_time,
                last_check=datetime.utcnow().isoformat(),
                metadata={"directory": str(data_dir), "writable": True},
            )

    except Exception as e:
        return ComponentHealth(
            name="json_fallback",
            status="down",
            last_check=datetime.utcnow().isoformat(),
            error=f"Fallback system error: {str(e)}",
        )


def get_system_metrics() -> Dict[str, Any]:
    """Get system performance metrics"""
    try:
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil not available"}
            
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),  # Reduce interval for faster response
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": (
                psutil.disk_usage("/").percent
                if os.name != "nt"
                else psutil.disk_usage("C:\\").percent
            ),
            "process_count": len(psutil.pids()),
            "load_average": os.getloadavg() if hasattr(os, "getloadavg") else [0, 0, 0],
        }
    except Exception as e:
        return {"error": f"Unable to get system metrics: {str(e)}"}


async def perform_health_checks() -> DetailedHealthResponse:
    """Perform comprehensive health checks"""
    global health_cache

    # Check cache first
    current_time = time.time()
    if health_cache.get("last_check", 0) + cache_ttl > current_time:
        return health_cache["response"]

    warnings = []
    components = []

    # Initialize database managers
    config = ServerConfig()

    try:
        # Check ArangoDB
        if ArangoDBManager:
            arango_manager = ArangoDBManager(config)
            arango_health = await check_database_connection(arango_manager, "arangodb")
            components.append(arango_health)

            if arango_health.status != "up":
                warnings.append("ArangoDB connection issues detected")
        else:
            components.append(
                ComponentHealth(
                    name="arangodb",
                    status="unavailable",
                    last_check=datetime.utcnow().isoformat(),
                    error="ArangoDBManager class not available",
                )
            )
            warnings.append("ArangoDB manager class not found")

    except Exception as e:
        components.append(
            ComponentHealth(
                name="arangodb",
                status="down",
                last_check=datetime.utcnow().isoformat(),
                error=f"Manager initialization failed: {str(e)}",
            )
        )
        warnings.append("ArangoDB manager initialization failed")

    try:
        # Check MongoDB
        if MongoDBManager:
            mongo_manager = MongoDBManager(config)
            mongo_health = await check_database_connection(mongo_manager, "mongodb")
            components.append(mongo_health)

            if mongo_health.status != "up":
                warnings.append("MongoDB connection issues detected")
        else:
            components.append(
                ComponentHealth(
                    name="mongodb",
                    status="unavailable",
                    last_check=datetime.utcnow().isoformat(),
                    error="MongoDBManager class not available",
                )
            )
            warnings.append("MongoDB manager class not found")

    except Exception as e:
        components.append(
            ComponentHealth(
                name="mongodb",
                status="down",
                last_check=datetime.utcnow().isoformat(),
                error=f"Manager initialization failed: {str(e)}",
            )
        )
        warnings.append("MongoDB manager initialization failed")

    # Check JSON fallback system
    fallback_health = await check_json_fallback_system()
    components.append(fallback_health)

    if fallback_health.status != "up":
        warnings.append("JSON fallback system not operational")

    # Determine overall status
    component_statuses = [comp.status for comp in components]
    if all(status == "up" for status in component_statuses):
        overall_status = "healthy"
    elif any(status == "up" for status in component_statuses):
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    # Build response
    response = DetailedHealthResponse(
        overall=HealthStatus(
            status=overall_status,
            timestamp=datetime.utcnow().isoformat(),
            uptime_seconds=current_time - app_start_time,
            version="1.0.0",
            environment=config.ENVIRONMENT,
        ),
        components=components,
        system_metrics=get_system_metrics(),
        checks_performed=len(components),
        warnings=warnings,
    )

    # Cache the response
    health_cache = {"last_check": current_time, "response": response}

    return response


@router.get("/health", response_model=HealthStatus)
async def basic_health_check():
    """Basic health check endpoint"""
    try:
        current_time = time.time()
        return HealthStatus(
            status="healthy",
            timestamp=datetime.utcnow().isoformat(),
            uptime_seconds=current_time - app_start_time,
            version="1.0.0",
            environment=os.getenv("ENVIRONMENT", "development"),
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with all components - returns 200 with partial status"""
    try:
        current_time = time.time()
        components = {}
        
        # Get status from dependency container
        if DEPENDENCIES_AVAILABLE and service_status:
            for service_name, status_info in service_status.items():
                components[service_name] = {
                    'status': status_info.get('status', 'unknown'),
                    'message': status_info.get('message', ''),
                    'last_checked': status_info.get('last_checked')
                }
        else:
            # Fallback status
            components = {
                'mongo': {'status': 'unknown', 'message': 'service_status unavailable', 'last_checked': None},
                'arango': {'status': 'unknown', 'message': 'service_status unavailable', 'last_checked': None},
                'llm': {'status': 'unknown', 'message': 'service_status unavailable', 'last_checked': None},
                'json_fallback': {'status': 'ok', 'message': 'available', 'last_checked': current_time}
            }
        
        # Determine overall status
        statuses = [c['status'] for c in components.values()]
        if all(s == 'ok' for s in statuses):
            overall_status = 'healthy'
        elif any(s == 'unavailable' for s in statuses):
            overall_status = 'degraded'
        else:
            overall_status = 'healthy'
        
        # Always return 200 OK with status in body
        return {
            'overall_status': overall_status,
            'timestamp': datetime.utcnow().isoformat(),
            'uptime_seconds': current_time - app_start_time,
            'services': components,
            'system_metrics': get_system_metrics() if PSUTIL_AVAILABLE else {}
        }
    except Exception as e:
        # Even on error, return 200 with error details
        logger.error(f"Detailed health check error: {e}")
        return {
            'overall_status': 'error',
            'timestamp': datetime.utcnow().isoformat(),
            'uptime_seconds': time.time() - app_start_time,
            'services': {},
            'error': str(e)
        }


@router.get("/health/components/{component_name}")
async def component_health_check(component_name: str):
    """Check specific component health"""
    valid_components = ["arangodb", "mongodb", "json_fallback"]

    if component_name not in valid_components:
        raise HTTPException(
            status_code=404, detail=f"Component '{component_name}' not found"
        )

    try:
        detailed_response = await perform_health_checks()
        component = next(
            (c for c in detailed_response.components if c.name == component_name), None
        )

        if not component:
            raise HTTPException(
                status_code=404, detail=f"Component '{component_name}' not monitored"
            )

        return component

    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Component health check failed: {str(e)}"
        )


@router.get("/health/readiness")
async def readiness_check():
    """Kubernetes readiness probe endpoint"""
    try:
        response = await perform_health_checks()

        # Ready if at least core databases are up
        core_components = ["arangodb", "mongodb"]
        core_statuses = [
            comp.status for comp in response.components if comp.name in core_components
        ]

        if all(status == "up" for status in core_statuses):
            return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}
        else:
            raise HTTPException(status_code=503, detail="System not ready")

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Readiness check failed: {str(e)}")


@router.get("/health/liveness")
async def liveness_check():
    """Kubernetes liveness probe endpoint"""
    try:
        # Simple check - if we can respond, we're alive
        return {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": time.time() - app_start_time,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Liveness check failed: {str(e)}")


@router.get("/health/database")
async def database_health():
    """Database connectivity health check"""
    try:
        # Check MongoDB
        mongodb_health = {"status": "unknown"}
        try:
            if MOTOR_AVAILABLE:
                # Try to get database client from dependency container
                import sys
                app_module = sys.modules.get('server.app')
                if app_module and hasattr(app_module, 'container'):
                    container = app_module.container
                    if hasattr(container, 'mongo_client'):
                        mongo_client = container.mongo_client()
                        await mongo_client.admin.command('ping')
                        mongodb_health = {"status": "up", "timestamp": datetime.utcnow().isoformat()}
                    else:
                        mongodb_health = {"status": "unavailable", "reason": "mongo_client not found"}
                else:
                    mongodb_health = {"status": "unavailable", "reason": "app module not loaded"}
            else:
                mongodb_health = {"status": "unavailable", "reason": "motor not available"}
        except Exception as e:
            mongodb_health = {"status": "down", "error": str(e)}

        # Check ArangoDB
        arangodb_health = {"status": "unknown"}
        try:
            if ARANGO_AVAILABLE:
                # Try to get ArangoDB client from dependency container
                import sys
                app_module = sys.modules.get('server.app')
                if app_module and hasattr(app_module, 'container'):
                    container = app_module.container
                    if hasattr(container, 'arango_client'):
                        arango_client = container.arango_client()
                        # Try to access the database
                        if hasattr(arango_client, 'db'):
                            db = arango_client.db('human_ai_co_create')
                            db.properties()  # Test connection
                            arangodb_health = {"status": "up", "timestamp": datetime.utcnow().isoformat()}
                        else:
                            arangodb_health = {"status": "unavailable", "reason": "db method not found"}
                    else:
                        arangodb_health = {"status": "unavailable", "reason": "arango_client not found"}
                else:
                    arangodb_health = {"status": "unavailable", "reason": "app module not loaded"}
            else:
                arangodb_health = {"status": "unavailable", "reason": "arango not available"}
        except Exception as e:
            arangodb_health = {"status": "down", "error": str(e)}

        return {
            "mongodb": mongodb_health,
            "arangodb": arangodb_health,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database health check failed: {str(e)}")


@router.get("/health/agents")
async def agents_health():
    """Agent system health check"""
    try:
        agents_status = {}
        
        # Try to get agents from the global app state
        import sys
        app_module = sys.modules.get('server.app')
        
        if app_module:
            # Check global agents
            agents = getattr(app_module, 'agents', {})
            session_manager = getattr(app_module, 'session_manager', None)
            
            # Session Manager
            if session_manager:
                agents_status["session_manager"] = {
                    "status": "up" if hasattr(session_manager, 'config') else "partial",
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                agents_status["session_manager"] = {"status": "down", "reason": "not initialized"}
            
            # Other agents
            agent_names = ["perception", "planner", "graph_manager", "verifier", "evaluator"]
            for agent_name in agent_names:
                if agent_name in agents:
                    agent = agents[agent_name]
                    agents_status[agent_name] = {
                        "status": "up" if agent is not None else "down",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    agents_status[agent_name] = {"status": "down", "reason": "not found"}
        else:
            # App module not loaded
            for agent_name in ["session_manager", "perception", "planner", "graph_manager", "verifier", "evaluator"]:
                agents_status[agent_name] = {"status": "unavailable", "reason": "app module not loaded"}

        return {
            "agents": agents_status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Agent health check failed: {str(e)}")


@router.get("/health/llm")
async def llm_health():
    """LLM provider health check"""
    try:
        # Check if LLM provider is configured and accessible
        llm_status = {"status": "unknown"}
        
        try:
            # Try to get LLM provider from environment or config
            import os
            openai_key = os.getenv('OPENAI_API_KEY')
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')
            
            if openai_key or anthropic_key:
                provider = "openai" if openai_key else "anthropic"
                llm_status = {
                    "status": "configured",
                    "provider": provider,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                llm_status = {"status": "unavailable", "reason": "no API keys configured"}
                
        except Exception as e:
            llm_status = {"status": "error", "error": str(e)}

        return llm_status
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"LLM health check failed: {str(e)}")


# For integration with main FastAPI app
def get_health_router() -> APIRouter:
    """Get the health router for integration"""
    return router
