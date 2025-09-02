"""
Workspace (Blackboard) System for Human-AI Co-Creation
Manages session state, persistence to MongoDB and JSON fallback
"""

import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import logging

try:
    from motor.motor_asyncio import AsyncIOMotorClient

    MOTOR_AVAILABLE = True
except ImportError:
    MOTOR_AVAILABLE = False

try:
    # Try importing aioredis with fallback for compatibility issues
    try:
        import aioredis

        REDIS_AVAILABLE = True
    except (ImportError, TypeError) as e:
        # Handle both missing package and Python 3.12+ compatibility issues
        REDIS_AVAILABLE = False
        print(f"Redis not available: {e}")
except Exception:
    REDIS_AVAILABLE = False

from server_config import ServerConfig
from utils.schemas import WorkspaceSchema

logger = logging.getLogger(__name__)


class Workspace:
    """
    Core workspace (blackboard) implementing the blueprint specification.

    Manages session state with MongoDB primary storage and JSON fallback.
    Supports checkpointing, snapshots, and delta operations.
    """

    def __init__(self, session_id: str, config: ServerConfig):
        self.session_id = session_id
        self.config = config
        self.data: Dict[str, Any] = self._get_default_workspace()
        self.mongo_client: Optional[AsyncIOMotorClient] = None
        self.redis_client: Optional[Any] = None
        self.last_save_time = 0
        self.checkpoint_interval = 300  # 5 minutes

    def _get_default_workspace(self) -> Dict[str, Any]:
        """Get default workspace structure per blueprint"""
        return {
            "session_id": self.session_id,
            "topic": "story",
            "story_so_far": "",  # Also supports topic_content for other topics
            "topic_content": "",
            "events": [],
            "characters": {},
            "kb_triples": [],
            "projections": {"A": None, "B": None, "C": None},
            "history": [],
            "graph": {"nodes": [], "edges": []},
            "policy": {
                "max_backtrack": 2,
                "suggestion_mode": "smart",
                "max_branches": 3,
            },
            "metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "last_modified": datetime.utcnow().isoformat(),
                "version": "1.0",
                "user_id": None,
            },
        }

    async def initialize(self) -> None:
        """Initialize database connections"""
        try:
            if MOTOR_AVAILABLE and self.config.MONGODB_URL:
                self.mongo_client = AsyncIOMotorClient(self.config.MONGODB_URL)
                # Test connection
                await self.mongo_client.admin.command("ping")
                logger.info("MongoDB connection established")

            if REDIS_AVAILABLE and self.config.REDIS_URL:
                self.redis_client = await aioredis.from_url(self.config.REDIS_URL)
                await self.redis_client.ping()
                logger.info("Redis connection established")

        except Exception as e:
            logger.warning(f"Database connection failed, using JSON fallback only: {e}")

    async def load(self) -> bool:
        """Load workspace from MongoDB or JSON fallback"""
        try:
            # Try MongoDB first
            if self.mongo_client:
                db = self.mongo_client[self.config.MONGODB_DATABASE]
                collection = db.stories

                doc = await collection.find_one({"session_id": self.session_id})
                if doc:
                    doc.pop("_id", None)  # Remove MongoDB _id
                    self.data = doc
                    logger.info(f"Workspace loaded from MongoDB: {self.session_id}")
                    return True

            # Fallback to JSON
            json_path = self._get_json_path()
            if json_path.exists():
                with open(json_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                logger.info(f"Workspace loaded from JSON fallback: {self.session_id}")
                return True

            # No existing workspace found
            logger.info(f"New workspace created: {self.session_id}")
            return False

        except Exception as e:
            logger.error(f"Failed to load workspace {self.session_id}: {e}")
            return False

    async def save(self, force: bool = False) -> None:
        """Save workspace to MongoDB and JSON fallback"""
        current_time = time.time()

        # Check if we need to save (throttling)
        if (
            not force and (current_time - self.last_save_time) < 30
        ):  # 30 second throttle
            return

        self.data["metadata"]["last_modified"] = datetime.utcnow().isoformat()

        try:
            # Save to MongoDB
            if self.mongo_client:
                db = self.mongo_client[self.config.MONGODB_DATABASE]
                collection = db.stories

                await collection.update_one(
                    {"session_id": self.session_id}, {"$set": self.data}, upsert=True
                )
                logger.debug(f"Workspace saved to MongoDB: {self.session_id}")

            # Always save JSON fallback
            await self._save_json_snapshot()

            self.last_save_time = current_time

        except Exception as e:
            logger.error(f"Failed to save workspace {self.session_id}: {e}")
            # Ensure JSON fallback even if MongoDB fails
            await self._save_json_snapshot()

    async def _save_json_snapshot(self) -> None:
        """Save JSON snapshot to local fallback"""
        try:
            json_path = self._get_json_path()
            json_path.parent.mkdir(parents=True, exist_ok=True)

            # Create timestamped snapshot
            snapshot_dir = json_path.parent / "snapshots"
            snapshot_dir.mkdir(exist_ok=True)

            timestamp = int(time.time())
            snapshot_path = snapshot_dir / f"snapshot_{timestamp}.json"

            # Save current state
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)

            # Save timestamped snapshot
            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)

            # Clean old snapshots (keep last 10)
            snapshots = sorted(snapshot_dir.glob("snapshot_*.json"))
            for old_snapshot in snapshots[:-10]:
                old_snapshot.unlink()

            logger.debug(f"JSON snapshot saved: {json_path}")

        except Exception as e:
            logger.error(f"Failed to save JSON snapshot: {e}")

    def _get_json_path(self) -> Path:
        """Get JSON file path for this workspace"""
        return Path("data/backups") / self.session_id / "workspace.json"

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from workspace"""
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set value in workspace"""
        self.data[key] = value

    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple values in workspace"""
        self.data.update(updates)

    def get_story_content(self) -> str:
        """Get the main content (story_so_far or topic_content)"""
        return self.data.get("story_so_far", self.data.get("topic_content", ""))

    def set_story_content(self, content: str) -> None:
        """Set the main content"""
        topic = self.data.get("topic", "story")
        if topic == "story":
            self.data["story_so_far"] = content
        else:
            self.data["topic_content"] = content

    def add_event(self, event: Dict[str, Any]) -> None:
        """Add event to workspace"""
        if "events" not in self.data:
            self.data["events"] = []

        event.setdefault("timestamp", datetime.utcnow().isoformat())
        event.setdefault("id", f"e_{len(self.data['events'])}")

        self.data["events"].append(event)

    def add_character(self, name: str, character_data: Dict[str, Any]) -> None:
        """Add or update character"""
        if "characters" not in self.data:
            self.data["characters"] = {}

        self.data["characters"][name] = character_data

    def set_projections(self, projections: Dict[str, Any]) -> None:
        """Set current projections (A, B, C)"""
        self.data["projections"] = projections

    def get_projections(self) -> Dict[str, Any]:
        """Get current projections"""
        return self.data.get("projections", {"A": None, "B": None, "C": None})

    def add_to_history(self, action: str, data: Dict[str, Any]) -> None:
        """Add action to history for backtracking"""
        if "history" not in self.data:
            self.data["history"] = []

        history_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "data": data,
        }

        self.data["history"].append(history_entry)

        # Limit history size based on policy
        max_backtrack = self.data.get("policy", {}).get("max_backtrack", 2)
        max_history = max_backtrack * 5  # Keep extra for flexibility

        if len(self.data["history"]) > max_history:
            self.data["history"] = self.data["history"][-max_history:]

    def get_policy(self) -> Dict[str, Any]:
        """Get session policy"""
        return self.data.get("policy", {})

    def update_policy(self, policy_updates: Dict[str, Any]) -> None:
        """Update session policy"""
        if "policy" not in self.data:
            self.data["policy"] = {}
        self.data["policy"].update(policy_updates)

    def to_dict(self) -> Dict[str, Any]:
        """Convert workspace to dictionary"""
        return self.data.copy()

    def to_schema(self) -> WorkspaceSchema:
        """Convert to Pydantic schema"""
        try:
            return WorkspaceSchema.parse_obj(self.data)
        except Exception as e:
            logger.error(f"Failed to convert to schema: {e}")
            # Return minimal valid schema
            return WorkspaceSchema(
                session_id=self.session_id,
                topic=self.data.get("topic", "story"),
                story_so_far=self.get_story_content(),
                events=self.data.get("events", []),
                characters=self.data.get("characters", {}),
                projections=self.data.get("projections", {}),
                metadata=self.data.get("metadata", {}),
            )

    async def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            if self.redis_client:
                await self.redis_client.close()
            if self.mongo_client:
                self.mongo_client.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


class WorkspaceManager:
    """Manager for multiple workspaces"""

    def __init__(self, config: ServerConfig):
        self.config = config
        self.active_workspaces: Dict[str, Workspace] = {}

    async def get_workspace(self, session_id: str) -> Workspace:
        """Get or create workspace for session"""
        if session_id not in self.active_workspaces:
            workspace = Workspace(session_id, self.config)
            await workspace.initialize()
            await workspace.load()
            self.active_workspaces[session_id] = workspace

        return self.active_workspaces[session_id]

    async def save_workspace(self, session_id: str, force: bool = False) -> None:
        """Save specific workspace"""
        if session_id in self.active_workspaces:
            await self.active_workspaces[session_id].save(force=force)

    async def save_all_workspaces(self, force: bool = False) -> None:
        """Save all active workspaces"""
        tasks = []
        for workspace in self.active_workspaces.values():
            tasks.append(workspace.save(force=force))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def cleanup(self) -> None:
        """Cleanup all workspaces"""
        await self.save_all_workspaces(force=True)

        for workspace in self.active_workspaces.values():
            await workspace.cleanup()

        self.active_workspaces.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get workspace manager statistics"""
        return {
            "active_workspaces": len(self.active_workspaces),
            "workspace_ids": list(self.active_workspaces.keys()),
        }
