"""
JSON Fallback Storage for local backup and offline operation
"""

import json
import logging
import asyncio
import aiofiles
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class FileSnapshot:
    """File snapshot metadata"""

    session_id: str
    timestamp: datetime
    file_path: str
    file_size: int
    checksum: Optional[str] = None


class JSONFallbackClient:
    """JSON file-based storage for fallback and local development"""

    def __init__(self, base_path: str = "data/backups"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Initialize directory structure
        self.sessions_dir = self.base_path / "sessions"
        self.snapshots_dir = self.base_path / "snapshots"
        self.archive_dir = self.base_path / "archive"

        for directory in [self.sessions_dir, self.snapshots_dir, self.archive_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def _get_session_file(self, session_id: str) -> Path:
        """Get the file path for a session"""
        return self.sessions_dir / f"{session_id}.json"

    def _get_snapshot_file(self, session_id: str, timestamp: datetime) -> Path:
        """Get the file path for a snapshot"""
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S_%f")
        return self.snapshots_dir / session_id / f"snapshot_{timestamp_str}.json"

    async def save_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Save session data to JSON file"""
        try:
            session_file = self._get_session_file(session_id)

            # Add metadata
            data_with_meta = {
                **data,
                "session_id": session_id,
                "saved_at": datetime.utcnow().isoformat(),
                "format_version": "1.0",
            }

            # Write file asynchronously
            async with aiofiles.open(session_file, "w", encoding="utf-8") as f:
                await f.write(
                    json.dumps(
                        data_with_meta, indent=2, ensure_ascii=False, default=str
                    )
                )

            logger.debug(f"Saved session {session_id} to {session_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save session {session_id} to JSON: {e}")
            return False

    async def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session data from JSON file"""
        try:
            session_file = self._get_session_file(session_id)

            if not session_file.exists():
                return None

            async with aiofiles.open(session_file, "r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)

            logger.debug(f"Loaded session {session_id} from {session_file}")
            return data

        except Exception as e:
            logger.error(f"Failed to load session {session_id} from JSON: {e}")
            return None

    async def delete_session(self, session_id: str) -> bool:
        """Delete session file and its snapshots"""
        try:
            # Delete main session file
            session_file = self._get_session_file(session_id)
            if session_file.exists():
                session_file.unlink()

            # Delete snapshots directory
            snapshots_dir = self.snapshots_dir / session_id
            if snapshots_dir.exists():
                for snapshot_file in snapshots_dir.glob("*.json"):
                    snapshot_file.unlink()
                snapshots_dir.rmdir()

            logger.debug(f"Deleted session {session_id} and its snapshots")
            return True

        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    async def save_snapshot(
        self, session_id: str, data: Dict[str, Any], snapshot_type: str = "auto"
    ) -> bool:
        """Save a workspace snapshot"""
        try:
            timestamp = datetime.utcnow()
            snapshot_file = self._get_snapshot_file(session_id, timestamp)

            # Ensure directory exists
            snapshot_file.parent.mkdir(parents=True, exist_ok=True)

            # Add metadata
            snapshot_data = {
                "session_id": session_id,
                "timestamp": timestamp.isoformat(),
                "type": snapshot_type,
                "data": data,
                "format_version": "1.0",
            }

            # Write file asynchronously
            async with aiofiles.open(snapshot_file, "w", encoding="utf-8") as f:
                await f.write(
                    json.dumps(snapshot_data, indent=2, ensure_ascii=False, default=str)
                )

            logger.debug(f"Saved snapshot for session {session_id} to {snapshot_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save snapshot for session {session_id}: {e}")
            return False

    async def load_latest_snapshot(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load the latest snapshot for a session"""
        try:
            snapshots_dir = self.snapshots_dir / session_id

            if not snapshots_dir.exists():
                return None

            # Find the latest snapshot file
            snapshot_files = list(snapshots_dir.glob("snapshot_*.json"))
            if not snapshot_files:
                return None

            # Sort by modification time (latest first)
            latest_file = max(snapshot_files, key=lambda f: f.stat().st_mtime)

            async with aiofiles.open(latest_file, "r", encoding="utf-8") as f:
                content = await f.read()
                snapshot_data = json.loads(content)

            logger.debug(
                f"Loaded latest snapshot for session {session_id} from {latest_file}"
            )
            return snapshot_data.get("data")

        except Exception as e:
            logger.error(
                f"Failed to load latest snapshot for session {session_id}: {e}"
            )
            return None

    async def list_user_sessions(
        self, user_id: str = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List all sessions (simplified without user filtering in JSON mode)"""
        try:
            sessions = []

            for session_file in self.sessions_dir.glob("*.json"):
                try:
                    async with aiofiles.open(session_file, "r", encoding="utf-8") as f:
                        content = await f.read()
                        data = json.loads(content)

                    # Extract session info
                    session_info = {
                        "session_id": data.get("session_id"),
                        "topic": data.get("topic"),
                        "created_at": data.get("created_at"),
                        "last_modified": data.get("last_modified"),
                        "metadata": data.get("metadata", {}),
                    }

                    # Simple user filtering if user_id provided
                    if user_id is None or data.get("user_id") == user_id:
                        sessions.append(session_info)

                except Exception as e:
                    logger.warning(f"Failed to read session file {session_file}: {e}")
                    continue

            # Sort by last modified (newest first) and limit
            sessions.sort(key=lambda x: x.get("last_modified", ""), reverse=True)
            return sessions[:limit]

        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []

    async def cleanup_old_snapshots(
        self, session_id: str, keep_count: int = 10
    ) -> bool:
        """Keep only the latest N snapshots for a session"""
        try:
            snapshots_dir = self.snapshots_dir / session_id

            if not snapshots_dir.exists():
                return True

            # Get all snapshot files sorted by modification time (newest first)
            snapshot_files = sorted(
                snapshots_dir.glob("snapshot_*.json"),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )

            # Delete old snapshots if we have more than keep_count
            deleted_count = 0
            if len(snapshot_files) > keep_count:
                for old_file in snapshot_files[keep_count:]:
                    old_file.unlink()
                    deleted_count += 1

            logger.debug(
                f"Cleaned up {deleted_count} old snapshots for session {session_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to cleanup snapshots for session {session_id}: {e}")
            return False

    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            stats = {
                "total_sessions": 0,
                "total_snapshots": 0,
                "total_size_bytes": 0,
                "sessions_by_topic": {},
                "oldest_session": None,
                "newest_session": None,
            }

            # Count sessions and calculate stats
            session_dates = []

            for session_file in self.sessions_dir.glob("*.json"):
                try:
                    file_size = session_file.stat().st_size
                    stats["total_size_bytes"] += file_size
                    stats["total_sessions"] += 1

                    # Get creation time for date stats
                    creation_time = datetime.fromtimestamp(session_file.stat().st_ctime)
                    session_dates.append(creation_time)

                    # Read topic for topic stats
                    async with aiofiles.open(session_file, "r", encoding="utf-8") as f:
                        content = await f.read()
                        data = json.loads(content)
                        topic = data.get("topic", "unknown")
                        stats["sessions_by_topic"][topic] = (
                            stats["sessions_by_topic"].get(topic, 0) + 1
                        )

                except Exception as e:
                    logger.warning(
                        f"Failed to process session file {session_file}: {e}"
                    )
                    continue

            # Count snapshots
            for snapshots_subdir in self.snapshots_dir.iterdir():
                if snapshots_subdir.is_dir():
                    snapshot_count = len(list(snapshots_subdir.glob("snapshot_*.json")))
                    stats["total_snapshots"] += snapshot_count

                    # Add snapshot sizes
                    for snapshot_file in snapshots_subdir.glob("snapshot_*.json"):
                        stats["total_size_bytes"] += snapshot_file.stat().st_size

            # Date range stats
            if session_dates:
                stats["oldest_session"] = min(session_dates).isoformat()
                stats["newest_session"] = max(session_dates).isoformat()

            return stats

        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {}

    async def export_session(self, session_id: str, export_path: str) -> bool:
        """Export a session with all its snapshots to a single file"""
        try:
            # Load main session data
            session_data = await self.load_session(session_id)
            if not session_data:
                logger.error(f"Session {session_id} not found for export")
                return False

            # Load all snapshots
            snapshots_dir = self.snapshots_dir / session_id
            snapshots = []

            if snapshots_dir.exists():
                for snapshot_file in snapshots_dir.glob("snapshot_*.json"):
                    try:
                        async with aiofiles.open(
                            snapshot_file, "r", encoding="utf-8"
                        ) as f:
                            content = await f.read()
                            snapshot_data = json.loads(content)
                            snapshots.append(snapshot_data)
                    except Exception as e:
                        logger.warning(f"Failed to read snapshot {snapshot_file}: {e}")
                        continue

            # Create export data
            export_data = {
                "export_metadata": {
                    "session_id": session_id,
                    "exported_at": datetime.utcnow().isoformat(),
                    "format_version": "1.0",
                },
                "session_data": session_data,
                "snapshots": snapshots,
            }

            # Write export file
            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(export_file, "w", encoding="utf-8") as f:
                await f.write(
                    json.dumps(export_data, indent=2, ensure_ascii=False, default=str)
                )

            logger.info(f"Exported session {session_id} to {export_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to export session {session_id}: {e}")
            return False

    async def import_session(self, import_path: str) -> Optional[str]:
        """Import a session from an exported file"""
        try:
            import_file = Path(import_path)
            if not import_file.exists():
                logger.error(f"Import file {import_path} not found")
                return None

            # Read import file
            async with aiofiles.open(import_file, "r", encoding="utf-8") as f:
                content = await f.read()
                import_data = json.loads(content)

            session_id = import_data["export_metadata"]["session_id"]
            session_data = import_data["session_data"]
            snapshots = import_data.get("snapshots", [])

            # Save main session
            if not await self.save_session(session_id, session_data):
                return None

            # Save snapshots
            for snapshot in snapshots:
                snapshot_timestamp = datetime.fromisoformat(snapshot["timestamp"])
                snapshot_file = self._get_snapshot_file(session_id, snapshot_timestamp)

                snapshot_file.parent.mkdir(parents=True, exist_ok=True)

                async with aiofiles.open(snapshot_file, "w", encoding="utf-8") as f:
                    await f.write(
                        json.dumps(snapshot, indent=2, ensure_ascii=False, default=str)
                    )

            logger.info(f"Imported session {session_id} from {import_file}")
            return session_id

        except Exception as e:
            logger.error(f"Failed to import session from {import_path}: {e}")
            return None


def create_json_fallback_client(base_path: str = "data/backups") -> JSONFallbackClient:
    """Factory function to create JSON fallback client"""
    return JSONFallbackClient(base_path)
