import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from server.app import app


def create_session(client):
    resp = client.post("/api/session/new", json={
        "user_id": "test_user",
        "topic": "story",
        "topic_descriptor": "story",
        "initial_content": "Detective Mira entered the dimly lit study, her eyes drawn to a sealed envelope on the desk.",
        "policy": {}
    })
    assert resp.status_code == 200
    return resp.json()["session_id"]


def test_agent_pipeline_end_to_end():
    with TestClient(app) as client:
        session_id = create_session(client)
        suggest_body = {
            "mode": "on_demand",
            "options": {
                "topic": "story",
                "context": "Detective Mira entered the dimly lit study, her eyes drawn to a sealed envelope on the desk.",
                "max_branches": 3
            },
            "constraints": {}
        }
        resp = client.post(f"/api/session/{session_id}/invoke_suggest", json=suggest_body)
        assert resp.status_code == 200
        data = resp.json()
        # Validate planner output
        assert "projections" in data
        assert isinstance(data["projections"], dict)
        for branch in data["projections"].values():
            if branch is not None:
                assert "title" in branch
                assert "paragraph" in branch
                assert "events" in branch
                assert "flags" in branch
                assert "branch_type" in branch
        # Validate verifier and evaluator outputs in metadata
        assert "metadata" in data
        meta = data["metadata"]
        if "verifications" in meta:
            for v in meta["verifications"]:
                if v is not None:
                    assert "accept_reject" in v or "confidence" in v
        if "branch_scores" in meta:
            for s in meta["branch_scores"]:
                if s is not None:
                    assert "composite_score" in s or "scores" in s
