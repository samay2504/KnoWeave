#!/usr/bin/env python3
"""
Test server for Human-AI Co-Creation platform
Provides basic endpoints for frontend testing without heavy ML dependencies
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
import asyncio
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Human-AI Co-Creation Test Server",
    description="Test server for frontend validation",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data for testing
MOCK_SESSIONS = [
    {
        "session_id": "test-session-1",
        "name": "Sample Creative Session",
        "created_at": "2025-01-09T01:00:00Z",
        "status": "active",
        "graph": {
            "nodes": [
                {"id": "1", "text": "Initial idea", "type": "concept", "x": 100, "y": 100},
                {"id": "2", "text": "Refined concept", "type": "development", "x": 200, "y": 150},
                {"id": "3", "text": "Final implementation", "type": "solution", "x": 300, "y": 100}
            ],
            "links": [
                {"source": "1", "target": "2", "relationship": "develops_into"},
                {"source": "2", "target": "3", "relationship": "leads_to"}
            ]
        }
    },
    {
        "session_id": "test-session-2", 
        "name": "Another Session",
        "created_at": "2025-01-08T15:30:00Z",
        "status": "completed",
        "graph": {
            "nodes": [
                {"id": "a", "text": "Problem statement", "type": "problem", "x": 50, "y": 80},
                {"id": "b", "text": "Analysis", "type": "analysis", "x": 150, "y": 120}
            ],
            "links": [
                {"source": "a", "target": "b", "relationship": "analyzed_by"}
            ]
        }
    }
]

MOCK_USER = {
    "id": "test-user-123",
    "name": "Test User",
    "email": "test@example.com",
    "picture": "https://via.placeholder.com/64",
    "created_at": "2025-01-01T00:00:00Z"
}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Human-AI Co-Creation Test Server",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0-test",
        "uptime": 3600,  # Mock uptime
        "services": {
            "api": "up",
            "database": "up"
        },
        "environment": "development",
        "debug": True
    }

@app.get("/api/health/detailed")
async def detailed_health_check():
    """Detailed health check endpoint"""
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
    """Get list of sessions"""
    return {
        "success": True,
        "sessions": MOCK_SESSIONS
    }

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get specific session"""
    session = next((s for s in MOCK_SESSIONS if s["session_id"] == session_id), None)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "success": True,
        "session": session
    }

@app.get("/api/sessions/{session_id}/graph")
async def get_session_graph(session_id: str):
    """Get session graph data"""
    session = next((s for s in MOCK_SESSIONS if s["session_id"] == session_id), None)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "success": True,
        "graph": session.get("graph", {"nodes": [], "links": []})
    }

@app.post("/api/sessions")
async def create_session(data: dict):
    """Create new session"""
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
    """Generate suggestions for session"""
    await asyncio.sleep(0.5)  # Simulate processing time
    
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
        },
        {
            "id": "suggestion-3",
            "text": "Try connecting this idea to previous concepts",
            "type": "connection",
            "confidence": 0.91
        }
    ]
    
    return {
        "success": True,
        "suggestions": suggestions
    }

@app.post("/api/sessions/{session_id}/evaluate")
async def evaluate_session(session_id: str, data: dict):
    """Evaluate session progress"""
    await asyncio.sleep(1.0)  # Simulate evaluation time
    
    return {
        "success": True,
        "evaluation": {
            "overall_score": 0.78,
            "creativity_score": 0.82,
            "coherence_score": 0.75,
            "completeness_score": 0.68,
            "strengths": [
                "Creative idea generation",
                "Good concept development",
                "Clear progression"
            ],
            "areas_for_improvement": [
                "More detailed analysis needed",
                "Consider alternative perspectives",
                "Expand on implementation details"
            ]
        }
    }

@app.get("/api/user/profile")
async def get_user_profile():
    """Get user profile"""
    return {
        "success": True,
        "user": MOCK_USER
    }

@app.get("/auth/google/login")
async def google_login():
    """Mock Google OAuth login"""
    # In real implementation, this would redirect to Google
    return {
        "auth_url": "http://localhost:3000/callback?code=mock_code&state=mock_state",
        "success": True
    }

@app.get("/auth/google/callback") 
async def google_callback(code: str, state: str):
    """Mock Google OAuth callback"""
    if code == "mock_code" and state == "mock_state":
        return {
            "success": True,
            "user": MOCK_USER,
            "session_id": "test-session-1"
        }
    else:
        raise HTTPException(status_code=400, detail="Invalid authentication")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
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
    print("🚀 Starting Human-AI Co-Creation Test Server...")
    print("📊 Health Check: http://localhost:8001/health")
    print("🔍 API Docs: http://localhost:8001/docs")
    print("⚡ Frontend can connect to: http://localhost:8001")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        reload=False,  # Disable reload for test server
        log_level="info"
    )

class BacktrackResponse(BaseModel):
    session_id: str
    reverted_to: str
    new_projections: Dict[str, Any] = {}
    status: str = "backtracked"

class SnapshotResponse(BaseModel):
    session_id: str
    snapshot: Dict[str, Any]

# Create FastAPI app
app = FastAPI(
    title="Human-AI Co-Creation Test Server",
    description="Simplified server for UI testing",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": 0,
        "version": "1.0.0",
        "environment": "test"
    }

@app.get("/api/me")
async def get_current_user():
    """Get current user - returns 401 for testing"""
    raise HTTPException(status_code=401, detail="Authentication required")

@app.post("/api/session/new", response_model=SessionResponse)
async def create_new_session(request: NewSessionRequest):
    """Create a new writing session"""
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    
    workspace = {
        "session_id": session_id,
        "user_id": request.user_id,
        "topic": request.topic,
        "story_so_far": request.initial_content,
        "events": [
            {
                "id": "event_1",
                "summary": "Story initialization",
                "confidence": 0.95,
                "timestamp": datetime.utcnow().isoformat()
            }
        ],
        "characters": {
            "protagonist": {"name": "Hero", "description": "Main character"}
        },
        "created_at": datetime.utcnow().isoformat(),
        "last_updated": datetime.utcnow().isoformat()
    }
    
    sessions_db[session_id] = workspace
    snapshots_db[session_id] = workspace.copy()
    
    return SessionResponse(
        session_id=session_id,
        workspace=workspace,
        status="created",
        message="Session created successfully"
    )

@app.get("/api/session/{session_id}/snapshot", response_model=SnapshotResponse)
async def get_session_snapshot(session_id: str):
    """Get current workspace snapshot"""
    if session_id not in snapshots_db:
        raise HTTPException(status_code=404, detail="Session not found")
    
    snapshot = snapshots_db[session_id]
    
    # Add some mock graph data
    snapshot.update({
        "nodes": [
            {"id": "node_1", "title": "Beginning", "text": "Story start", "score": 0.9},
            {"id": "node_2", "title": "Middle", "text": "Plot development", "score": 0.8},
            {"id": "node_3", "title": "End", "text": "Resolution", "score": 0.7}
        ],
        "edges": [
            {"from": "node_1", "to": "node_2", "relationship": "leads_to"},
            {"from": "node_2", "to": "node_3", "relationship": "concludes_with"}
        ],
        "graph_stats": {
            "node_count": 3,
            "edge_count": 2,
            "avg_confidence": 0.8
        }
    })
    
    return SnapshotResponse(session_id=session_id, snapshot=snapshot)

@app.post("/api/session/{session_id}/invoke_suggest", response_model=SuggestionsResponse)
async def invoke_suggestions(session_id: str, request: SuggestRequest):
    """Generate writing suggestions for a session"""
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Mock suggestions
    projections = {
        "branch_0": {
            "content": "The hero discovered a hidden door...",
            "confidence": 0.85,
            "reasoning": "Adds mystery element"
        },
        "branch_1": {
            "content": "A mysterious stranger appeared...",
            "confidence": 0.78,
            "reasoning": "Introduces new character"
        },
        "branch_2": {
            "content": "The weather suddenly changed...",
            "confidence": 0.72,
            "reasoning": "Creates atmospheric tension"
        }
    }
    
    return SuggestionsResponse(
        session_id=session_id,
        projections=projections,
        metadata={
            "branch_scores": [0.85, 0.78, 0.72],
            "generation_time": 0.5
        },
        status="success"
    )

@app.post("/api/session/{session_id}/accept_branch", response_model=SessionResponse)
async def accept_branch(session_id: str, request: AcceptBranchRequest):
    """Accept a suggested branch and update the story"""
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail="Session not found")
    
    workspace = sessions_db[session_id]
    workspace["last_updated"] = datetime.utcnow().isoformat()
    workspace["story_so_far"] += f"\n\nAccepted branch: {request.branch_id}"
    
    return SessionResponse(
        session_id=session_id,
        workspace=workspace,
        status="accepted",
        message=f"Branch {request.branch_id} accepted successfully"
    )

@app.post("/api/session/{session_id}/backtrack", response_model=BacktrackResponse)
async def backtrack_session(session_id: str, request: BacktrackRequest):
    """Backtrack to a previous point in the story"""
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return BacktrackResponse(
        session_id=session_id,
        reverted_to=request.node_id,
        new_projections={
            "branch_0": {"content": "Reverted content...", "confidence": 0.8}
        },
        status="backtracked"
    )

@app.get("/auth/google/login")
async def google_login():
    """Mock Google OAuth login"""
    return {
        "auth_url": "https://accounts.google.com/oauth/authorize?mock=true",
        "state": "mock_state_123"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
