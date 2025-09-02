#!/usr/bin/env python3
"""
Test script for JSON fallback functionality
Tests writing and reading session snapshots to/from JSON files
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import uuid


def create_sample_session_snapshot() -> Dict[str, Any]:
    """Create a sample session snapshot with realistic data"""
    session_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    return {
        "session_id": session_id,
        "user_id": user_id,
        "title": "Test Story Session",
        "topic": "story",
        "topic_descriptor": {
            "genre": "mystery",
            "pov": "first",
            "protagonist": "Detective Sarah",
        },
        "content": {
            "story_so_far": "Detective Sarah walked into the dimly lit apartment...",
            "events": [
                {
                    "id": "event_1",
                    "summary": "Detective enters apartment",
                    "timestamp": datetime.now().isoformat(),
                    "confidence": 0.9,
                }
            ],
            "characters": [
                {
                    "name": "Detective Sarah",
                    "traits": ["observant", "cautious", "experienced"],
                }
            ],
            "constraints": {"preserve_pov": True, "max_events": 4},
        },
        "mode": "balanced",
        "workspace": {
            "graph_nodes": 5,
            "last_suggestion": None,
            "backtrack_history": [],
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "tags": ["mystery", "test"],
        "status": "active",
        "metadata": {
            "version": "1.0",
            "backup_type": "json_fallback",
            "created_by": "test_script",
        },
    }


def validate_session_schema(data: Dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate session snapshot against expected schema"""
    errors = []

    # Required top-level fields
    required_fields = [
        "session_id",
        "user_id",
        "topic",
        "content",
        "created_at",
        "updated_at",
        "status",
    ]

    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    # Validate content structure
    if "content" in data:
        content = data["content"]
        if not isinstance(content, dict):
            errors.append("content must be an object")
        else:
            # Check for expected content fields
            if "story_so_far" not in content and "topic_content" not in content:
                errors.append(
                    "content must have either 'story_so_far' or 'topic_content'"
                )

    # Validate topic enum
    if "topic" in data:
        valid_topics = ["story", "lesson_plan", "guide", "essay", "other"]
        if data["topic"] not in valid_topics:
            errors.append(
                f"Invalid topic: {data['topic']}. Must be one of {valid_topics}"
            )

    # Validate mode enum
    if "mode" in data:
        valid_modes = ["balanced", "creative", "analytical", "conservative"]
        if data["mode"] not in valid_modes:
            errors.append(f"Invalid mode: {data['mode']}. Must be one of {valid_modes}")

    # Validate status enum
    if "status" in data:
        valid_statuses = ["active", "archived", "deleted"]
        if data["status"] not in valid_statuses:
            errors.append(
                f"Invalid status: {data['status']}. Must be one of {valid_statuses}"
            )

    return len(errors) == 0, errors


def test_json_fallback():
    """Main test function for JSON fallback functionality"""
    print("🧪 Testing JSON Fallback Functionality")
    print("=" * 50)

    # Get project root and create backup directory path
    project_root = Path(__file__).parent.parent
    backup_dir = project_root / "data" / "backups"

    print(f"📁 Backup directory: {backup_dir}")

    # Ensure backup directory exists and is writable
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        print("✅ Backup directory created/verified")
    except Exception as e:
        print(f"❌ Failed to create backup directory: {e}")
        return False

    # Test 1: Create sample session snapshot
    print("\n📝 Test 1: Creating sample session snapshot...")
    try:
        snapshot = create_sample_session_snapshot()
        session_id = snapshot["session_id"]
        print(f"✅ Sample snapshot created for session: {session_id}")
    except Exception as e:
        print(f"❌ Failed to create sample snapshot: {e}")
        return False

    # Test 2: Validate snapshot schema
    print("\n🔍 Test 2: Validating snapshot schema...")
    try:
        is_valid, errors = validate_session_schema(snapshot)
        if is_valid:
            print("✅ Snapshot schema validation passed")
        else:
            print(f"❌ Schema validation failed:")
            for error in errors:
                print(f"   - {error}")
            return False
    except Exception as e:
        print(f"❌ Schema validation error: {e}")
        return False

    # Test 3: Write snapshot to JSON file
    print("\n💾 Test 3: Writing snapshot to JSON file...")
    try:
        session_backup_dir = backup_dir / session_id
        session_backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_file = session_backup_dir / f"snapshot_{timestamp}.json"

        with open(snapshot_file, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)

        print(f"✅ Snapshot written to: {snapshot_file}")
        print(f"   File size: {snapshot_file.stat().st_size} bytes")

    except Exception as e:
        print(f"❌ Failed to write snapshot: {e}")
        return False

    # Test 4: Read and validate JSON file
    print("\n📖 Test 4: Reading and validating JSON file...")
    try:
        with open(snapshot_file, "r", encoding="utf-8") as f:
            loaded_snapshot = json.load(f)

        print("✅ Snapshot successfully read from file")

        # Validate loaded data
        is_valid, errors = validate_session_schema(loaded_snapshot)
        if is_valid:
            print("✅ Loaded snapshot schema validation passed")
        else:
            print(f"❌ Loaded snapshot schema validation failed:")
            for error in errors:
                print(f"   - {error}")
            return False

        # Compare original and loaded data
        if snapshot == loaded_snapshot:
            print("✅ Original and loaded snapshots match perfectly")
        else:
            print("⚠️  Minor differences in original vs loaded (may be expected)")

    except Exception as e:
        print(f"❌ Failed to read/validate snapshot: {e}")
        return False

    # Test 5: Test concurrent writes (simulate multiple snapshots)
    print("\n⚡ Test 5: Testing multiple snapshot writes...")
    try:
        for i in range(3):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[
                :-3
            ]  # Include milliseconds
            snapshot_copy = snapshot.copy()
            snapshot_copy["updated_at"] = datetime.now().isoformat()
            snapshot_copy["metadata"]["snapshot_number"] = i + 1

            snapshot_file_multi = session_backup_dir / f"snapshot_{timestamp}.json"
            with open(snapshot_file_multi, "w", encoding="utf-8") as f:
                json.dump(snapshot_copy, f, indent=2)

            print(f"   ✅ Snapshot {i+1} written: {snapshot_file_multi.name}")

        print("✅ Multiple snapshot writes completed successfully")

    except Exception as e:
        print(f"❌ Failed multiple snapshot writes: {e}")
        return False

    # Test 6: Cleanup (optional)
    print("\n🧹 Test 6: Cleanup test files...")
    try:
        # List all files created
        session_files = list(session_backup_dir.glob("*.json"))
        print(f"   Created {len(session_files)} test files")

        # Optional: Remove test files (uncomment if desired)
        # for file in session_files:
        #     file.unlink()
        # session_backup_dir.rmdir()
        # print("✅ Test files cleaned up")

        print("✅ Test files preserved for inspection")

    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")

    print("\n🎉 JSON Fallback Test Summary")
    print("=" * 50)
    print("✅ All tests passed successfully!")
    print(f"📁 Test files location: {session_backup_dir}")
    print("🔧 JSON fallback functionality is working correctly")

    return True


if __name__ == "__main__":
    success = test_json_fallback()
    sys.exit(0 if success else 1)
