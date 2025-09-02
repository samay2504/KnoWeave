#!/usr/bin/env python3
"""
Simple test server for Human-AI Co-Creation platform
Provides basic endpoints for frontend testing without complex dependencies
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import json
import asyncio
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Human-AI Co-Creation Test Server",
    description="Simple test server for frontend validation",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data
MOCK_SESSIONS = [
    {
        "session_id": "test-session-1",
        "name": "Sample Creative Session",
        "created_at": "2025-01-09T01:00:00Z",
        "status": "active",
        "graph": {
            "nodes": [
                {"id": "1", "text": "Initial idea", "type": "concept", "x": 100, "y": 100},
                {"id": "2", "text": "Refined concept", "type": "development", "x": 200, "y": 150}
            ],
            "links": [
                {"source": "1", "target": "2", "relationship": "develops_into"}
            ]
        }
    }
]

MOCK_USER = {
    "id": "test-user-123",
    "name": "Test User",
    "email": "test@example.com",
    "picture": "https://via.placeholder.com/64"
}

@app.get("/")
async def root():
    return {
        "message": "Human-AI Co-Creation Test Server",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0-test",
        "uptime": 3600,
        "services": {
            "api": "up",
            "database": "up"
        },
        "environment": "development",
        "debug": True
    }

@app.get("/api/health/detailed")
async def detailed_health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0-test",
        "uptime": 3600,
        "services": {
            "session_manager": {"status": "up", "response_time": 12},
            "perception_agent": {"status": "up", "response_time": 8},
            "planner_agent": {"status": "up", "response_time": 15},
            "graph_manager": {"status": "up", "response_time": 6},
            "verifier_agent": {"status": "up", "response_time": 9},
            "evaluator_agent": {"status": "up", "response_time": 11}
        },
        "database": {
            "status": "up",
            "type": "MongoDB",
            "response_time": 5
        },
        "environment": {
            "mode": "development",
            "debug": True
        },
        "performance": {
            "response_time": 45,
            "memory_usage": 68,
            "cpu_usage": 15,
            "requests_per_minute": 24
        },
        "warnings": [
            "Running in test mode - ML features disabled"
        ]
    }

@app.get("/api/sessions")
async def get_sessions():
    return {
        "success": True,
        "sessions": MOCK_SESSIONS
    }

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    session = next((s for s in MOCK_SESSIONS if s["session_id"] == session_id), None)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "success": True,
        "session": session
    }

@app.get("/api/sessions/{session_id}/graph")
async def get_session_graph(session_id: str):
    session = next((s for s in MOCK_SESSIONS if s["session_id"] == session_id), None)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "success": True,
        "graph": session.get("graph", {"nodes": [], "links": []})
    }

@app.post("/api/sessions")
async def create_session(data: dict):
    new_session = {
        "session_id": f"test-session-{len(MOCK_SESSIONS) + 1}",
        "name": data.get("name", "New Session"),
        "created_at": datetime.now().isoformat(),
        "status": "active",
        "graph": {"nodes": [], "links": []}
    }
    MOCK_SESSIONS.append(new_session)
    
    return {
        "success": True,
        "session": new_session
    }

@app.post("/api/sessions/{session_id}/suggestions")
async def get_suggestions(session_id: str, data: dict):
    await asyncio.sleep(0.5)
    
    suggestions = [
        {
            "id": "suggestion-1",
            "text": "Consider exploring alternative approaches",
            "type": "exploration",
            "confidence": 0.85
        },
        {
            "id": "suggestion-2", 
            "text": "This concept could benefit from more detail",
            "type": "development",
            "confidence": 0.72
        }
    ]
    
    return {
        "success": True,
        "suggestions": suggestions
    }

@app.get("/api/user/profile")
async def get_user_profile():
    return {
        "success": True,
        "user": MOCK_USER
    }

@app.get("/api/me")
async def get_current_user():
    """Get current authenticated user - mock endpoint"""
    return {
        "success": True,
        "user": MOCK_USER,
        "authenticated": True
    }

@app.get("/auth/google")
async def google_auth_redirect():
    """Mock Google OAuth redirect"""
    return {
        "auth_url": "http://localhost:3000/callback?code=mock_auth_code&state=mock_state",
        "success": True
    }

@app.get("/auth/google/login")
async def google_auth_login():
    """Mock Google OAuth login endpoint"""
    return {
        "auth_url": "http://localhost:3000/callback?code=mock_auth_code&state=mock_state",
        "authorization_url": "http://localhost:3000/callback?code=mock_auth_code&state=mock_state",
        "success": True
    }

@app.post("/api/auth/google")
async def api_google_auth(data: dict = {}):
    """Alternative Google auth endpoint"""
    return {
        "auth_url": "http://localhost:3000/callback?code=mock_auth_code&state=mock_state",
        "authorization_url": "http://localhost:3000/callback?code=mock_auth_code&state=mock_state",
        "url": "http://localhost:3000/callback?code=mock_auth_code&state=mock_state",
        "success": True
    }

@app.get("/auth/google/callback") 
async def google_auth_callback(code: str = None, state: str = None):
    """Mock Google OAuth callback"""
    if code and state:
        return {
            "success": True,
            "user": MOCK_USER,
            "token": "mock_jwt_token_12345",
            "session_id": "test-session-1"
        }
    else:
        raise HTTPException(status_code=400, detail="Missing authentication parameters")

@app.post("/auth/logout")
async def logout():
    """Mock logout endpoint"""
    return {
        "success": True,
        "message": "Logged out successfully"
    }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "message": str(exc)
        }
    )

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Simple Test Server...")
    print("📊 Health Check: http://localhost:8001/health")
    print("🔍 API Docs: http://localhost:8001/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )
