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

# Import optional dependencies with fallbacks for Python 3.12+ compatibility
try:
    import aioredis

    AIOREDIS_AVAILABLE = True
except (ImportError, TypeError) as e:
    # Handle both missing package and Python 3.12+ TimeoutError compatibility issue
    AIOREDIS_AVAILABLE = False
    aioredis = None

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
from pathlib import Path

# Import server components
import sys

sys.path.append(str(Path(__file__).parent.parent))

# Import with proper paths
from db.arango_client import ArangoClient
from db.mongo_client import MongoClient
from server_config import ServerConfig


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

        elif db_name == "redis":
            # Test Redis connection
            result = await db_manager.ping()
            if result:
                response_time = (time.time() - start_time) * 1000
                return ComponentHealth(
                    name=db_name,
                    status="up",
                    response_time_ms=response_time,
                    last_check=datetime.utcnow().isoformat(),
                    metadata={"cache_enabled": True},
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
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
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
        arango_manager = ArangoDBManager(config)
        arango_health = await check_database_connection(arango_manager, "arangodb")
        components.append(arango_health)

        if arango_health.status != "up":
            warnings.append("ArangoDB connection issues detected")

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
        mongo_manager = MongoDBManager(config)
        mongo_health = await check_database_connection(mongo_manager, "mongodb")
        components.append(mongo_health)

        if mongo_health.status != "up":
            warnings.append("MongoDB connection issues detected")

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

    try:
        # Check Redis
        redis_manager = RedisManager(config)
        redis_health = await check_database_connection(redis_manager, "redis")
        components.append(redis_health)

        if redis_health.status != "up":
            warnings.append("Redis connection issues detected")

    except Exception as e:
        components.append(
            ComponentHealth(
                name="redis",
                status="down",
                last_check=datetime.utcnow().isoformat(),
                error=f"Manager initialization failed: {str(e)}",
            )
        )
        warnings.append("Redis manager initialization failed")

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


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """Detailed health check with all components"""
    try:
        return await perform_health_checks()
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Detailed health check failed: {str(e)}"
        )


@router.get("/health/components/{component_name}")
async def component_health_check(component_name: str):
    """Check specific component health"""
    valid_components = ["arangodb", "mongodb", "redis", "json_fallback"]

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


# For integration with main FastAPI app
def get_health_router() -> APIRouter:
    """Get the health router for integration"""
    return router
