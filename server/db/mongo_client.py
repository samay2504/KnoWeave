"""
MongoDB async client with fallback support
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict

# MongoDB imports
try:
    from motor.motor_asyncio import (
        AsyncIOMotorClient,
        AsyncIOMotorDatabase,
        AsyncIOMotorCollection,
    )

    MOTOR_AVAILABLE = True
except ImportError:
    MOTOR_AVAILABLE = False

# Fallback to sync pymongo
try:
    from pymongo import MongoClient
    from pymongo.database import Database
    from pymongo.collection import Collection

    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class SessionDocument:
    """Session document structure"""

    session_id: str
    user_id: str
    topic: str
    topic_content: str
    events: List[Dict[str, Any]]
    characters: Dict[str, Any]
    kb_triples: List[List[str]]
    projections: Dict[str, Any]
    history: List[Dict[str, Any]]
    graph: Dict[str, Any]
    policy: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    last_modified: datetime


class MongoClient:
    """Async MongoDB client for session and workspace storage"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = None
        self.db = None
        self.sessions_collection = None
        self.snapshots_collection = None
        self.users_collection = None
        self.connected = False
        self.use_sync = False

    async def connect(self) -> bool:
        """Connect to MongoDB with fallback handling"""
        try:
            if MOTOR_AVAILABLE:
                await self._connect_async()
            elif PYMONGO_AVAILABLE:
                await self._connect_sync()
            else:
                logger.warning("No MongoDB library available")
                return False

            await self._initialize_collections()
            self.connected = True
            logger.info("Connected to MongoDB successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False

    async def _connect_async(self) -> None:
        """Connect using async Motor client"""
        self.client = AsyncIOMotorClient(self.config["uri"])
        self.db = self.client[self.config["database"]]
        self.use_sync = False

        # Test the connection
        await self.client.admin.command("ping")

    async def _connect_sync(self) -> None:
        """Connect using sync PyMongo client in thread"""

        def _sync_connect():
            client = MongoClient(self.config["uri"])
            # Test the connection
            client.admin.command("ping")
            return client, client[self.config["database"]]

        loop = asyncio.get_event_loop()
        self.client, self.db = await loop.run_in_executor(None, _sync_connect)
        self.use_sync = True

    async def _initialize_collections(self) -> None:
        """Initialize collections and indexes"""
        if self.use_sync:
            await self._initialize_collections_sync()
        else:
            await self._initialize_collections_async()

    async def _initialize_collections_async(self) -> None:
        """Initialize collections using async client"""
        self.sessions_collection = self.db.sessions
        self.snapshots_collection = self.db.snapshots
        self.users_collection = self.db.users

        # Create indexes for better performance
        await self.sessions_collection.create_index("session_id", unique=True)
        await self.sessions_collection.create_index("user_id")
        await self.sessions_collection.create_index("last_modified")
        await self.snapshots_collection.create_index("session_id")
        await self.snapshots_collection.create_index("timestamp")
        await self.users_collection.create_index("google_id", unique=True)
        await self.users_collection.create_index("email")

    async def _initialize_collections_sync(self) -> None:
        """Initialize collections using sync client in thread"""

        def _sync_init():
            sessions_collection = self.db.sessions
            snapshots_collection = self.db.snapshots
            users_collection = self.db.users

            # Create indexes for better performance
            sessions_collection.create_index("session_id", unique=True)
            sessions_collection.create_index("user_id")
            sessions_collection.create_index("last_modified")
            snapshots_collection.create_index("session_id")
            snapshots_collection.create_index("timestamp")
            users_collection.create_index("google_id", unique=True)
            users_collection.create_index("email")

            return sessions_collection, snapshots_collection, users_collection

        loop = asyncio.get_event_loop()
        self.sessions_collection, self.snapshots_collection, self.users_collection = (
            await loop.run_in_executor(None, _sync_init)
        )

    async def save_session(self, session: SessionDocument) -> bool:
        """Save or update a session document"""
        try:
            # Update last_modified timestamp
            session.last_modified = datetime.utcnow()

            document = asdict(session)

            if self.use_sync:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.sessions_collection.replace_one(
                        {"session_id": session.session_id}, document, upsert=True
                    ),
                )
            else:
                await self.sessions_collection.replace_one(
                    {"session_id": session.session_id}, document, upsert=True
                )

            logger.debug(f"Saved session {session.session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save session {session.session_id}: {e}")
            return False

    async def load_session(self, session_id: str) -> Optional[SessionDocument]:
        """Load a session document"""
        try:
            if self.use_sync:
                loop = asyncio.get_event_loop()
                document = await loop.run_in_executor(
                    None,
                    lambda: self.sessions_collection.find_one(
                        {"session_id": session_id}
                    ),
                )
            else:
                document = await self.sessions_collection.find_one(
                    {"session_id": session_id}
                )

            if document:
                # Remove MongoDB's _id field
                document.pop("_id", None)
                return SessionDocument(**document)

            return None

        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and its snapshots"""
        try:
            if self.use_sync:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.sessions_collection.delete_one(
                        {"session_id": session_id}
                    ),
                )
                await loop.run_in_executor(
                    None,
                    lambda: self.snapshots_collection.delete_many(
                        {"session_id": session_id}
                    ),
                )
            else:
                await self.sessions_collection.delete_one({"session_id": session_id})
                await self.snapshots_collection.delete_many({"session_id": session_id})

            logger.debug(f"Deleted session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    async def list_user_sessions(
        self, user_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List sessions for a user"""
        try:
            projection = {
                "session_id": 1,
                "topic": 1,
                "created_at": 1,
                "last_modified": 1,
                "metadata.title": 1,
            }

            if self.use_sync:
                loop = asyncio.get_event_loop()
                cursor = await loop.run_in_executor(
                    None,
                    lambda: self.sessions_collection.find(
                        {"user_id": user_id}, projection
                    )
                    .sort("last_modified", -1)
                    .limit(limit),
                )
                documents = list(cursor)
            else:
                cursor = (
                    self.sessions_collection.find({"user_id": user_id}, projection)
                    .sort("last_modified", -1)
                    .limit(limit)
                )
                documents = await cursor.to_list(length=limit)

            # Clean up documents
            for doc in documents:
                doc.pop("_id", None)

            return documents

        except Exception as e:
            logger.error(f"Failed to list sessions for user {user_id}: {e}")
            return []

    async def save_snapshot(
        self,
        session_id: str,
        snapshot_data: Dict[str, Any],
        snapshot_type: str = "auto",
    ) -> bool:
        """Save a workspace snapshot"""
        try:
            document = {
                "session_id": session_id,
                "timestamp": datetime.utcnow(),
                "type": snapshot_type,
                "data": snapshot_data,
            }

            if self.use_sync:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, lambda: self.snapshots_collection.insert_one(document)
                )
            else:
                await self.snapshots_collection.insert_one(document)

            logger.debug(f"Saved snapshot for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save snapshot for session {session_id}: {e}")
            return False

    async def load_latest_snapshot(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load the latest snapshot for a session"""
        try:
            if self.use_sync:
                loop = asyncio.get_event_loop()
                document = await loop.run_in_executor(
                    None,
                    lambda: self.snapshots_collection.find_one(
                        {"session_id": session_id}, sort=[("timestamp", -1)]
                    ),
                )
            else:
                document = await self.snapshots_collection.find_one(
                    {"session_id": session_id}, sort=[("timestamp", -1)]
                )

            if document:
                return document.get("data")

            return None

        except Exception as e:
            logger.error(f"Failed to load snapshot for session {session_id}: {e}")
            return None

    async def cleanup_old_snapshots(
        self, session_id: str, keep_count: int = 10
    ) -> bool:
        """Keep only the latest N snapshots for a session"""
        try:
            if self.use_sync:
                loop = asyncio.get_event_loop()

                def _sync_cleanup():
                    # Get all snapshots sorted by timestamp (newest first)
                    snapshots = list(
                        self.snapshots_collection.find(
                            {"session_id": session_id}, {"_id": 1, "timestamp": 1}
                        ).sort("timestamp", -1)
                    )

                    # Delete old snapshots if we have more than keep_count
                    if len(snapshots) > keep_count:
                        old_ids = [s["_id"] for s in snapshots[keep_count:]]
                        self.snapshots_collection.delete_many({"_id": {"$in": old_ids}})
                        return len(old_ids)
                    return 0

                deleted_count = await loop.run_in_executor(None, _sync_cleanup)
            else:
                # Get all snapshots sorted by timestamp (newest first)
                snapshots = (
                    await self.snapshots_collection.find(
                        {"session_id": session_id}, {"_id": 1, "timestamp": 1}
                    )
                    .sort("timestamp", -1)
                    .to_list(None)
                )

                # Delete old snapshots if we have more than keep_count
                if len(snapshots) > keep_count:
                    old_ids = [s["_id"] for s in snapshots[keep_count:]]
                    result = await self.snapshots_collection.delete_many(
                        {"_id": {"$in": old_ids}}
                    )
                    deleted_count = result.deleted_count
                else:
                    deleted_count = 0

            logger.debug(
                f"Cleaned up {deleted_count} old snapshots for session {session_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to cleanup snapshots for session {session_id}: {e}")
            return False

    async def save_user(self, user_doc: Dict[str, Any]) -> bool:
        """Save or update a user document"""
        try:
            if self.use_sync:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.users_collection.update_one(
                        {"google_id": user_doc["google_id"]}, 
                        {"$set": user_doc}, 
                        upsert=True
                    ),
                )
            else:
                await self.users_collection.update_one(
                    {"google_id": user_doc["google_id"]}, 
                    {"$set": user_doc}, 
                    upsert=True
                )

            logger.debug(f"Saved user {user_doc.get('email', 'unknown')}")
            return True

        except Exception as e:
            logger.error(f"Failed to save user {user_doc.get('email', 'unknown')}: {e}")
            return False

    async def find_user(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a user document"""
        try:
            if self.use_sync:
                loop = asyncio.get_event_loop()
                document = await loop.run_in_executor(
                    None,
                    lambda: self.users_collection.find_one(query),
                )
            else:
                document = await self.users_collection.find_one(query)

            if document:
                # Remove MongoDB's _id field
                document.pop("_id", None)
                return document

            return None

        except Exception as e:
            logger.error(f"Failed to find user with query {query}: {e}")
            return None

    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            if self.use_sync:
                loop = asyncio.get_event_loop()
                stats = await loop.run_in_executor(
                    None,
                    lambda: {
                        "sessions_count": self.sessions_collection.count_documents({}),
                        "snapshots_count": self.snapshots_collection.count_documents(
                            {}
                        ),
                        "users_count": self.users_collection.count_documents({}),
                        "database_size": self.db.command("dbStats"),
                    },
                )
            else:
                stats = {
                    "sessions_count": await self.sessions_collection.count_documents(
                        {}
                    ),
                    "snapshots_count": await self.snapshots_collection.count_documents(
                        {}
                    ),
                    "users_count": await self.users_collection.count_documents({}),
                    "database_size": await self.db.command("dbStats"),
                }

            return stats

        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}

    async def close(self) -> None:
        """Close the database connection"""
        try:
            if self.client:
                if self.use_sync:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self.client.close)
                else:
                    self.client.close()
            self.connected = False
            logger.info("Closed MongoDB connection")
        except Exception as e:
            logger.error(f"Error closing MongoDB connection: {e}")


async def create_mongo_client(config: Dict[str, Any]) -> Optional[MongoClient]:
    """Factory function to create MongoDB client"""
    client = MongoClient(config)
    if await client.connect():
        return client
    return None
