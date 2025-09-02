"""
Human-AI Co-Creation Platform - Dependency Container System
Copyright (c) 2025 Samay Mehar. All rights reserved.
Patent Pending - Samay Mehar

Production-grade dependency injection system with dual database support.
Features automatic fallback mechanisms and secure configuration management.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Union, TYPE_CHECKING
from contextlib import asynccontextmanager

# Import the new core system
try:
    from server.core.imports import import_manager
    from server.core.config import config as global_config
    CORE_SYSTEM_AVAILABLE = True
except ImportError:
    # Fallback for transition period
    CORE_SYSTEM_AVAILABLE = False

# Type annotations for development
if TYPE_CHECKING:
    from server.server_config import ServerConfig
    from server.db.mongo_client import MongoClient
    from server.db.arango_client import ArangoGraphClient

logger = logging.getLogger(__name__)

class ProductionDependencyContainer:
    """Production-ready dependency injection container with dynamic imports"""
    
    def __init__(self, config: Optional[Any] = None):
        self.config = config or self._load_config()
        self._mongo_client: Optional[Any] = None
        self._arango_client: Optional[Any] = None
        self._initialized = False
        
        # Load components dynamically
        self._mongo_components = self._load_mongo_components()
        self._arango_components = self._load_arango_components()
    
    def _load_config(self) -> Any:
        """Load configuration with fallbacks"""
        if CORE_SYSTEM_AVAILABLE:
            return global_config
        else:
            # Fallback import
            try:
                from server.server_config import ServerConfig
                return ServerConfig()
            except ImportError:
                logger.warning("ServerConfig not available, using mock config")
                return type('MockConfig', (), {
                    'database_mode': 'mongodb',
                    'mongo_uri': 'mongodb://localhost:27017',
                    'arango_url': 'http://localhost:8529',
                    'arango_user': 'root',
                    'arango_password': '',
                    'arango_database': 'human_ai_co_create'
                })()
    
    def _load_mongo_components(self) -> Dict[str, Any]:
        """Load MongoDB components with fallbacks"""
        components = {}
        
        if CORE_SYSTEM_AVAILABLE:
            components['MongoClient'] = import_manager.get_attribute('server.db.mongo_client', 'MongoClient')
            components['create_mongo_client'] = import_manager.get_attribute('server.db.mongo_client', 'create_mongo_client')
        else:
            try:
                from server.db.mongo_client import MongoClient, create_mongo_client
                components['MongoClient'] = MongoClient
                components['create_mongo_client'] = create_mongo_client
            except ImportError:
                logger.warning("MongoDB components not available")
                components['MongoClient'] = None
                components['create_mongo_client'] = None
        
        return components
    
    def _load_arango_components(self) -> Dict[str, Any]:
        """Load ArangoDB components with fallbacks"""
        components = {}
        
        if CORE_SYSTEM_AVAILABLE:
            components['ArangoGraphClient'] = import_manager.get_attribute('server.db.arango_client', 'ArangoGraphClient')
            components['create_arango_client'] = import_manager.get_attribute('server.db.arango_client', 'create_arango_client')
        else:
            try:
                from server.db.arango_client import ArangoGraphClient, create_arango_client
                components['ArangoGraphClient'] = ArangoGraphClient
                components['create_arango_client'] = create_arango_client
            except ImportError:
                logger.warning("ArangoDB components not available")
                components['ArangoGraphClient'] = None
                components['create_arango_client'] = None
        
        return components
    
    async def initialize(self):
        """Initialize all dependencies based on configuration"""
        if self._initialized:
            return
        
        logger.info("Initializing dependency container...")
        
        try:
            # Initialize MongoDB if needed
            if self._should_init_mongo():
                await self._init_mongodb()
            
            # Initialize ArangoDB if needed  
            if self._should_init_arango():
                await self._init_arangodb()
            
            self._initialized = True
            logger.info("Dependency container initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize dependencies: {e}")
            raise
    
    def _should_init_mongo(self) -> bool:
        """Check if MongoDB should be initialized"""
        db_mode = getattr(self.config, 'database_mode', 'mongodb')
        return db_mode in ['mongodb', 'both'] and self._mongo_components['create_mongo_client'] is not None
    
    def _should_init_arango(self) -> bool:
        """Check if ArangoDB should be initialized"""
        db_mode = getattr(self.config, 'database_mode', 'mongodb')
        return db_mode in ['arangodb', 'both'] and self._arango_components['create_arango_client'] is not None
    
    async def _init_mongodb(self):
        """Initialize MongoDB client"""
        try:
            create_mongo_client = self._mongo_components['create_mongo_client']
            if create_mongo_client:
                client_config = {
                    'uri': getattr(self.config, 'mongo_uri', 'mongodb://localhost:27017'),
                    'database': 'human_ai_co_create'
                }
                self._mongo_client = await create_mongo_client(client_config)
                logger.info("MongoDB client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB: {e}")
    
    async def _init_arangodb(self):
        """Initialize ArangoDB client"""
        try:
            create_arango_client = self._arango_components['create_arango_client']
            if create_arango_client:
                arango_config = {
                    'url': getattr(self.config, 'arango_url', 'http://localhost:8529'),
                    'user': getattr(self.config, 'arango_user', 'root'),
                    'password': getattr(self.config, 'arango_password', ''),
                    'database': getattr(self.config, 'arango_database', 'human_ai_co_create')
                }
                
                logger.info("🔗 Attempting to initialize ArangoDB client...")
                self._arango_client = await create_arango_client(arango_config)
                
                if self._arango_client and hasattr(self._arango_client, 'connected') and self._arango_client.connected:
                    logger.info("✅ ArangoDB client initialized successfully")
                else:
                    logger.warning("⚠️ ArangoDB client created but not connected - continuing with MongoDB fallback")
                    
        except Exception as e:
            logger.warning(f"❌ ArangoDB client could not be initialized: {e}")
            logger.info("🔄 System will continue with MongoDB-only mode")
    
    async def cleanup(self):
        """Cleanup all dependencies"""
        logger.info("Cleaning up dependencies...")
        
        if self._mongo_client and hasattr(self._mongo_client, 'close'):
            try:
                await self._mongo_client.close()
                logger.info("MongoDB client closed")
            except Exception as e:
                logger.error(f"Error closing MongoDB: {e}")
        
        if self._arango_client and hasattr(self._arango_client, 'close'):
            try:
                await self._arango_client.close()
                logger.info("ArangoDB client closed")
            except Exception as e:
                logger.error(f"Error closing ArangoDB: {e}")
        
        self._initialized = False
    
    def get_mongo_client(self) -> Optional[Any]:
        """Get MongoDB client instance"""
        return self._mongo_client
    
    def get_arango_client(self) -> Optional[Any]:
        """Get ArangoDB client instance"""
        return self._arango_client
    
    def get_config(self) -> Any:
        """Get server configuration"""
        return self.config
    
    def is_initialized(self) -> bool:
        """Check if container is initialized"""
        return self._initialized

# Global container instance
_container: Optional[ProductionDependencyContainer] = None

def get_container() -> ProductionDependencyContainer:
    """Get or create global container instance"""
    global _container
    if _container is None:
        _container = ProductionDependencyContainer()
    return _container

def set_container(container: ProductionDependencyContainer):
    """Set global container instance"""
    global _container
    _container = container

# FastAPI dependency functions
def get_mongo_client() -> Optional[Any]:
    """FastAPI dependency for MongoDB client"""
    container = get_container()
    return container.get_mongo_client()

def get_arango_client() -> Optional[Any]:
    """FastAPI dependency for ArangoDB client"""
    container = get_container()
    return container.get_arango_client()

def get_server_config() -> Any:
    """FastAPI dependency for server configuration"""
    container = get_container()
    return container.get_config()

@asynccontextmanager
async def setup_dependencies(config: Optional[Any] = None):
    """Context manager for dependency setup"""
    container = ProductionDependencyContainer(config)
    set_container(container)
    
    try:
        await container.initialize()
        yield container
    finally:
        await container.cleanup()

def setup_container(config: Optional[Any] = None):
    """Setup dependency container for tests"""
    container = ProductionDependencyContainer(config)
    set_container(container)
    return container

def cleanup_container():
    """Cleanup dependency container"""
    global _container
    if _container:
        # Note: This is sync cleanup, use with care
        asyncio.create_task(_container.cleanup())
        _container = None

__all__ = [
    'ProductionDependencyContainer',
    'get_container',
    'set_container', 
    'get_mongo_client',
    'get_arango_client',
    'get_server_config',
    'setup_dependencies',
    'setup_container',
    'cleanup_container'
]
