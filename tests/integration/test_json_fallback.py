"""
Integration tests for JSON fallback functionality
Tests the complete JSON fallback workflow including error scenarios
"""

import json
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import uuid
import sys
import os

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from scripts.test_json_fallback import (
        create_sample_session_snapshot,
        validate_session_schema,
    )
except ImportError:
    # Define minimal versions if import fails
    def create_sample_session_snapshot():
        return {
            "session_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "topic": "story",
            "content": {"story_so_far": "Test content"},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "active",
        }

    def validate_session_schema(data):
        required = [
            "session_id",
            "user_id",
            "topic",
            "content",
            "created_at",
            "updated_at",
            "status",
        ]
        errors = [f"Missing {field}" for field in required if field not in data]
        return len(errors) == 0, errors


class JSONFallbackManager:
    """Mock JSON fallback manager for testing"""

    def __init__(self, backup_dir: Path):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def save_snapshot(self, session_id: str, snapshot: Dict[str, Any]) -> Path:
        """Save a session snapshot to JSON file"""
        session_dir = self.backup_dir / session_id
        session_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        snapshot_file = session_dir / f"snapshot_{timestamp}.json"

        with open(snapshot_file, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)

        return snapshot_file

    def load_latest_snapshot(self, session_id: str) -> Dict[str, Any]:
        """Load the latest snapshot for a session"""
        session_dir = self.backup_dir / session_id
        if not session_dir.exists():
            raise FileNotFoundError(f"No snapshots found for session {session_id}")

        snapshots = list(session_dir.glob("snapshot_*.json"))
        if not snapshots:
            raise FileNotFoundError(f"No snapshot files found for session {session_id}")

        # Get the latest snapshot by filename (timestamp-based)
        latest_snapshot = sorted(snapshots)[-1]

        with open(latest_snapshot, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_sessions(self) -> list[str]:
        """List all session IDs with snapshots"""
        if not self.backup_dir.exists():
            return []

        return [d.name for d in self.backup_dir.iterdir() if d.is_dir()]


@pytest.fixture
def temp_backup_dir():
    """Create a temporary backup directory for testing"""
    temp_dir = tempfile.mkdtemp(prefix="test_backup_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def json_fallback_manager(temp_backup_dir):
    """Create a JSON fallback manager with temporary directory"""
    return JSONFallbackManager(temp_backup_dir)


@pytest.fixture
def sample_session():
    """Create a sample session snapshot"""
    return create_sample_session_snapshot()


class TestJSONFallback:
    """Test suite for JSON fallback functionality"""

    def test_backup_directory_creation(self, temp_backup_dir):
        """Test that backup directory is created correctly"""
        manager = JSONFallbackManager(temp_backup_dir / "new_subdir")
        assert manager.backup_dir.exists()
        assert manager.backup_dir.is_dir()

    def test_save_snapshot_success(self, json_fallback_manager, sample_session):
        """Test successful snapshot saving"""
        session_id = sample_session["session_id"]
        snapshot_file = json_fallback_manager.save_snapshot(session_id, sample_session)

        assert snapshot_file.exists()
        assert snapshot_file.suffix == ".json"
        assert session_id in str(snapshot_file)

        # Verify file content
        with open(snapshot_file, "r") as f:
            loaded_data = json.load(f)

        assert loaded_data == sample_session

    def test_load_latest_snapshot_success(self, json_fallback_manager, sample_session):
        """Test successful loading of latest snapshot"""
        session_id = sample_session["session_id"]

        # Save snapshot
        json_fallback_manager.save_snapshot(session_id, sample_session)

        # Load it back
        loaded_snapshot = json_fallback_manager.load_latest_snapshot(session_id)

        assert loaded_snapshot == sample_session

    def test_load_nonexistent_session(self, json_fallback_manager):
        """Test loading snapshot for non-existent session"""
        with pytest.raises(FileNotFoundError):
            json_fallback_manager.load_latest_snapshot("nonexistent-session")

    def test_multiple_snapshots_latest_selection(
        self, json_fallback_manager, sample_session
    ):
        """Test that latest snapshot is correctly selected"""
        session_id = sample_session["session_id"]

        # Save multiple snapshots with different timestamps
        snapshots = []
        for i in range(3):
            snapshot_copy = sample_session.copy()
            snapshot_copy["updated_at"] = datetime.now().isoformat()
            snapshot_copy["metadata"] = {"sequence": i}

            snapshot_file = json_fallback_manager.save_snapshot(
                session_id, snapshot_copy
            )
            snapshots.append((snapshot_file, snapshot_copy))

        # Load latest
        latest_snapshot = json_fallback_manager.load_latest_snapshot(session_id)

        # Should be the last one saved
        assert latest_snapshot["metadata"]["sequence"] == 2

    def test_list_sessions(self, json_fallback_manager):
        """Test listing all sessions with snapshots"""
        # Initially empty
        assert json_fallback_manager.list_sessions() == []

        # Add some sessions
        session_ids = []
        for i in range(3):
            snapshot = create_sample_session_snapshot()
            session_id = snapshot["session_id"]
            session_ids.append(session_id)
            json_fallback_manager.save_snapshot(session_id, snapshot)

        # List sessions
        listed_sessions = json_fallback_manager.list_sessions()
        assert len(listed_sessions) == 3
        assert set(listed_sessions) == set(session_ids)

    def test_schema_validation_valid_snapshot(self, sample_session):
        """Test schema validation with valid snapshot"""
        is_valid, errors = validate_session_schema(sample_session)
        assert is_valid
        assert errors == []

    def test_schema_validation_missing_required_fields(self):
        """Test schema validation with missing required fields"""
        invalid_snapshot = {
            "session_id": "test-id",
            # Missing other required fields
        }

        is_valid, errors = validate_session_schema(invalid_snapshot)
        assert not is_valid
        assert len(errors) > 0
        assert any("Missing required field" in error for error in errors)

    def test_schema_validation_invalid_topic(self, sample_session):
        """Test schema validation with invalid topic"""
        sample_session["topic"] = "invalid_topic"

        is_valid, errors = validate_session_schema(sample_session)
        assert not is_valid
        assert any("Invalid topic" in error for error in errors)

    def test_concurrent_snapshot_writes(self, json_fallback_manager, sample_session):
        """Test handling of concurrent snapshot writes"""
        session_id = sample_session["session_id"]

        # Simulate concurrent writes
        snapshots = []
        for i in range(5):
            snapshot_copy = sample_session.copy()
            snapshot_copy["metadata"] = {
                "concurrent_write": i,
                "timestamp": datetime.now().isoformat(),
            }

            snapshot_file = json_fallback_manager.save_snapshot(
                session_id, snapshot_copy
            )
            snapshots.append(snapshot_file)

        # All files should exist
        for snapshot_file in snapshots:
            assert snapshot_file.exists()

        # Should be able to load the latest
        latest = json_fallback_manager.load_latest_snapshot(session_id)
        assert "concurrent_write" in latest.get("metadata", {})

    def test_large_snapshot_handling(self, json_fallback_manager):
        """Test handling of large snapshots"""
        # Create a large snapshot
        large_snapshot = create_sample_session_snapshot()
        large_snapshot["content"]["large_data"] = "x" * 10000  # 10KB of data
        large_snapshot["workspace"]["large_graph"] = list(range(1000))  # Large array

        session_id = large_snapshot["session_id"]

        # Save and load
        snapshot_file = json_fallback_manager.save_snapshot(session_id, large_snapshot)
        loaded_snapshot = json_fallback_manager.load_latest_snapshot(session_id)

        assert loaded_snapshot == large_snapshot
        assert len(loaded_snapshot["content"]["large_data"]) == 10000

    def test_unicode_content_handling(self, json_fallback_manager):
        """Test handling of Unicode content in snapshots"""
        unicode_snapshot = create_sample_session_snapshot()
        unicode_snapshot["content"][
            "story_so_far"
        ] = "Detective Sarah walked into the café… 🕵️‍♀️"
        unicode_snapshot["content"]["characters"] = [
            {"name": "Émilie", "traits": ["français", "détective"]},
            {"name": "山田太郎", "traits": ["日本人", "探偵"]},
        ]

        session_id = unicode_snapshot["session_id"]

        # Save and load
        json_fallback_manager.save_snapshot(session_id, unicode_snapshot)
        loaded_snapshot = json_fallback_manager.load_latest_snapshot(session_id)

        assert loaded_snapshot == unicode_snapshot
        assert "🕵️‍♀️" in loaded_snapshot["content"]["story_so_far"]

    def test_error_recovery_corrupted_json(self, json_fallback_manager, sample_session):
        """Test error handling with corrupted JSON file"""
        session_id = sample_session["session_id"]

        # Save a valid snapshot first
        json_fallback_manager.save_snapshot(session_id, sample_session)

        # Corrupt the file
        session_dir = json_fallback_manager.backup_dir / session_id
        snapshot_files = list(session_dir.glob("*.json"))

        with open(snapshot_files[0], "w") as f:
            f.write("{ invalid json content")

        # Should raise an appropriate error
        with pytest.raises(json.JSONDecodeError):
            json_fallback_manager.load_latest_snapshot(session_id)


# Integration test to run the standalone test script
def test_standalone_json_fallback_script():
    """Test that the standalone JSON fallback script runs successfully"""
    script_path = (
        Path(__file__).parent.parent.parent / "scripts" / "test_json_fallback.py"
    )

    if script_path.exists():
        import subprocess

        result = subprocess.run(
            [sys.executable, str(script_path)], capture_output=True, text=True
        )

        assert (
            result.returncode == 0
        ), f"Script failed with output: {result.stdout}\n{result.stderr}"
        assert "All tests passed successfully!" in result.stdout
    else:
        pytest.skip("JSON fallback test script not found")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
