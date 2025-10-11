
import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from server.app import app

def test_perception_endpoint_schema():
    client = TestClient(app)
    # Create a dummy session first (simulate /api/session/new)
    session_resp = client.post("/api/session/new", json={
        "user_id": "test_user",
        "topic": "story",
        "topic_descriptor": "story",
        "initial_content": "Alice walked into the forest.",
        "policy": {}
    })
    assert session_resp.status_code == 200
    session_id = session_resp.json()["session_id"]

    # Run workflow to trigger perception agent
    workflow_resp = client.post(
        f"/api/session/{session_id}/workflow",
        data='"Alice walked into the forest."',
        headers={"Content-Type": "application/json"}
    )
    assert workflow_resp.status_code == 200
    data = workflow_resp.json()
    assert "analysis" in data
    analysis = data["analysis"]
    # Check schema compliance
    required_keys = {"tokens", "entities", "characters", "events", "pov", "tense", "tone", "summary", "flags", "metadata"}
    assert required_keys.issubset(set(analysis.keys())), f"Missing keys: {required_keys - set(analysis.keys())}"
    # No extra keys
    assert set(analysis.keys()).issubset(required_keys), f"Extra keys: {set(analysis.keys()) - required_keys}"
    # Types
    assert isinstance(analysis["tokens"], list)
    assert isinstance(analysis["entities"], list)
    assert isinstance(analysis["characters"], list)
    assert isinstance(analysis["events"], list)
    assert isinstance(analysis["pov"], str)
    assert isinstance(analysis["tense"], str)
    assert isinstance(analysis["tone"], str)
    assert isinstance(analysis["summary"], str)
    assert isinstance(analysis["flags"], dict)
    assert isinstance(analysis["metadata"], dict)
    # Check for robust error handling
    bad_resp = client.post(
        f"/api/session/{session_id}/workflow",
        data='""',
        headers={"Content-Type": "application/json"}
    )
    assert bad_resp.status_code == 200
    bad_analysis = bad_resp.json()["analysis"]
    assert bad_analysis["metadata"].get("analysis_type") == "empty"
