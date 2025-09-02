"""
Dependency Injection Container for Production
Provides centralized dependency management with dynamic imports
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from contextlib import asynccontextmanager

# Use production-ready import system
from core.imports import import_manager
from core.config import config as global_config

# Import with fallbacks using dynamic import system
def get_server_config():
    """Get ServerConfig class with fallback"""
    return import_manager.get_attribute(
        'server.server_config', 'ServerConfig',
        default=type('MockConfig', (), {'database_mode': 'mongodb'})
    )

def get_mongo_components():
    """Get MongoDB components with fallback"""
    MongoClient = import_manager.get_attribute('server.db.mongo_client', 'MongoClient')
    create_mongo_client = import_manager.get_attribute('server.db.mongo_client', 'create_mongo_client')
    return MongoClient, create_mongo_client

def get_arango_components():
    """Get ArangoDB components with fallback"""
    ArangoGraphClient = import_manager.get_attribute('server.db.arango_client', 'ArangoGraphClient')
    create_arango_client = import_manager.get_attribute('server.db.arango_client', 'create_arango_client')
    return ArangoGraphClient, create_arango_client

logger = logging.getLogger(__name__)


class DependencyContainer:
    """Central dependency injection container"""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self._mongo_client: Optional[MongoClient] = None
        self._arango_client: Optional[ArangoGraphClient] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize all dependencies"""
        if self._initialized:
            return
            
        logger.info("Initializing dependency container...")
        
        # Initialize MongoDB client
        if self.config.database_mode in ["mongodb", "both"]:
            try:
                client_config = {
                    "uri": self.config.mongo_uri,
                    "database": "human_ai_co_create",
                    "database_mode": self.config.database_mode
                }
                self._mongo_client = await create_mongo_client(client_config)
                if self._mongo_client:
                    await self._mongo_client.connect()
                    logger.info("MongoDB client initialized successfully")
                else:
                    logger.warning("MongoDB client could not be initialized")
            except Exception as e:
                logger.error(f"Failed to initialize MongoDB client: {e}")
                # Continue with fallback mode
        
        # Initialize ArangoDB client
        if self.config.database_mode in ["arangodb", "both"]:
            try:
                arango_config = {
                    "url": self.config.arango_url,
                    "user": self.config.arango_user,
                    "password": self.config.arango_password,
                    "database": self.config.arango_database
                }
                self._arango_client = await create_arango_client(arango_config)
                if self._arango_client:
                    await self._arango_client.connect()
                    logger.info("ArangoDB client initialized successfully")
                else:
                    logger.warning("ArangoDB client could not be initialized")
            except Exception as e:
                logger.error(f"Failed to initialize ArangoDB client: {e}")
                # Continue with fallback mode
        
        self._initialized = True
        logger.info("Dependency container initialized")
    
    async def cleanup(self):
        """Cleanup dependencies"""
        logger.info("Cleaning up dependencies...")
        
        if self._mongo_client:
            try:
                await self._mongo_client.close()
                logger.info("MongoDB client closed")
            except Exception as e:
                logger.error(f"Error closing MongoDB client: {e}")
        
        if self._arango_client:
            try:
                await self._arango_client.close()
                logger.info("ArangoDB client closed")
            except Exception as e:
                logger.error(f"Error closing ArangoDB client: {e}")
        
        self._initialized = False
    
    def get_mongo_client(self) -> Optional[MongoClient]:
        """Get MongoDB client instance"""
        if not self._initialized:
            logger.warning("Dependency container not initialized")
            return None
        return self._mongo_client
    
    def get_arango_client(self) -> Optional[ArangoGraphClient]:
        """Get ArangoDB client instance"""
        if not self._initialized:
            logger.warning("Dependency container not initialized")
            return None
        return self._arango_client
    
    def get_config(self) -> ServerConfig:
        """Get server configuration"""
        return self.config


# Global dependency container instance
_container: Optional[DependencyContainer] = None


def get_container() -> DependencyContainer:
    """Get the global dependency container"""
    global _container
    if _container is None:
        raise RuntimeError("Dependency container not initialized")
    return _container


def set_container(container: DependencyContainer):
    """Set the global dependency container"""
    global _container
    _container = container


# Dependency injection functions for FastAPI
def get_mongo_client() -> Optional[MongoClient]:
    """FastAPI dependency for MongoDB client"""
    return get_container().get_mongo_client()


def get_arango_client() -> Optional[ArangoGraphClient]:
    """FastAPI dependency for ArangoDB client"""
    return get_container().get_arango_client()


def get_server_config() -> ServerConfig:
    """FastAPI dependency for server configuration"""
    return get_container().get_config()


@asynccontextmanager
async def setup_dependencies(config: ServerConfig):
    """Context manager for dependency setup"""
    container = DependencyContainer(config)
    set_container(container)
    
    try:
        await container.initialize()
        yield container
    finally:
        await container.cleanup()


def setup_container(config: Optional[ServerConfig] = None):
    """Setup dependency container for tests"""
    if config is None:
        from server_config import config as default_config
        config = default_config
    
    container = DependencyContainer(config)
    set_container(container)
    return container


def cleanup_container():
    """Cleanup dependency container"""
    global _container
    if _container is not None:
        # Close MongoDB client if it exists
        if hasattr(_container, '_mongo_client') and _container._mongo_client:
            _container._mongo_client.close()
        _container = None
