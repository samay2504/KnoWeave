"""
Production-grade global constants and configuration
Centralized port and endpoint management for the entire application
"""

# =============================================================================
# NETWORK CONFIGURATION - PRODUCTION CONSTANTS
# =============================================================================

# Core Application Ports
class Ports:
    """Global port configuration - modify here only"""
    # Backend API Server
    BACKEND_PORT = 8000
    BACKEND_HOST = "0.0.0.0"
    
    # Frontend Development Server  
    FRONTEND_PORT = 3000
    FRONTEND_HOST = "localhost"
    
    # Database Ports
    MONGODB_PORT = 27017
    ARANGODB_PORT = 8529
    REDIS_PORT = 6379
    
    # External Services
    POSTGRES_PORT = 5432
    ELASTICSEARCH_PORT = 9200

# URL Construction
class URLs:
    """Centralized URL construction"""
    @staticmethod
    def backend_url(path: str = "") -> str:
        return f"http://{Ports.BACKEND_HOST}:{Ports.BACKEND_PORT}{path}"
    
    @staticmethod
    def frontend_url(path: str = "") -> str:
        return f"http://{Ports.FRONTEND_HOST}:{Ports.FRONTEND_PORT}{path}"
    
    @staticmethod
    def mongodb_url(database: str = "human_ai_co_create") -> str:
        return f"mongodb://localhost:{Ports.MONGODB_PORT}/{database}"
    
    @staticmethod
    def arangodb_url() -> str:
        return f"http://localhost:{Ports.ARANGODB_PORT}"
    
    @staticmethod
    def redis_url() -> str:
        return f"redis://localhost:{Ports.REDIS_PORT}"

# =============================================================================
# GOOGLE OAUTH CONFIGURATION - PRODUCTION CONSTANTS
# =============================================================================

class OAuth:
    """Google OAuth production configuration"""
    # OAuth Redirect URIs - must be consistent across all files
    REDIRECT_URIS = [
        URLs.frontend_url("/auth/callback"),
        URLs.backend_url("/api/auth/callback"),
        "http://localhost:3000/auth/callback",  # Development fallback
        "http://127.0.0.1:3000/auth/callback"   # Alternative localhost
    ]
    
    # OAuth Scopes
    SCOPES = [
        "openid",
        "email", 
        "profile"
    ]
    
    # OAuth Endpoints
    AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
    TOKEN_URI = "https://oauth2.googleapis.com/token"
    USERINFO_URI = "https://www.googleapis.com/oauth2/v2/userinfo"

# =============================================================================
# APPLICATION CONFIGURATION CONSTANTS
# =============================================================================

class App:
    """Application-wide constants"""
    NAME = "Human-AI Co-Creation"
    VERSION = "1.0.0"
    API_PREFIX = "/api"
    
    # Session Configuration
    SESSION_TIMEOUT = 3600  # 1 hour
    MAX_BACKTRACK_DEPTH = 2
    MAX_SUGGESTIONS = 3
    
    # File Paths
    BACKUP_DIR = "data/backups"
    PROMPTS_DIR = "prompts"
    WEB_BUILD_DIR = "web/build"
    
    # Rate Limiting
    REQUEST_RATE_LIMIT = "100/minute"
    SUGGESTION_COOLDOWN = 300  # 5 minutes

# =============================================================================
# DATABASE CONFIGURATION CONSTANTS  
# =============================================================================

class Database:
    """Database configuration constants"""
    
    # Collection/Table Names
    SESSIONS_COLLECTION = "sessions"
    USERS_COLLECTION = "users"
    GRAPHS_COLLECTION = "graphs"
    SNAPSHOTS_COLLECTION = "snapshots"
    
    # MongoDB Configuration
    MONGODB_DATABASE = "human_ai_co_create"
    MONGODB_MAX_POOL_SIZE = 10
    MONGODB_TIMEOUT_MS = 5000
    
    # ArangoDB Configuration
    ARANGO_DATABASE = "human_ai_co_create"
    ARANGO_USERNAME = "root"
    ARANGO_TIMEOUT = 10
    
    # Redis Configuration
    REDIS_DATABASE = 0
    REDIS_TIMEOUT = 5

# =============================================================================
# AGENT CONFIGURATION CONSTANTS
# =============================================================================

class Agents:
    """Agent system configuration constants"""
    
    # Agent Names (must match blueprint)
    SESSION_MANAGER = "session_manager"
    PERCEPTION = "perception"
    PLANNER = "planner"
    GRAPH_MANAGER = "graph_manager"
    VERIFIER = "verifier"
    EVALUATOR = "evaluator"
    
    # Agent Processing Limits
    MAX_TOKENS = {
        SESSION_MANAGER: 2048,
        PERCEPTION: 1024,
        PLANNER: 4096,
        GRAPH_MANAGER: 2048,
        VERIFIER: 1024,
        EVALUATOR: 1024
    }
    
    # Temperature Settings
    TEMPERATURE = {
        SESSION_MANAGER: 0.1,
        PERCEPTION: 0.0,
        PLANNER: 0.7,
        GRAPH_MANAGER: 0.3,
        VERIFIER: 0.0,
        EVALUATOR: 0.2
    }

# =============================================================================
# PROMPT TEMPLATE GENERATOR CONSTANTS
# =============================================================================

class PTG:
    """Prompt Template Generator constants"""
    
    # Mode Configurations
    MODES = {
        "conservative": {
            "temperature": 0.3,
            "creativity_weight": 0.2,
            "consistency_weight": 0.8,
            "description": "Safe, predictable continuations"
        },
        "balanced": {
            "temperature": 0.5,
            "creativity_weight": 0.5,
            "consistency_weight": 0.5,
            "description": "Balanced creativity and consistency"
        },
        "exploratory": {
            "temperature": 0.8,
            "creativity_weight": 0.8,
            "consistency_weight": 0.2,
            "description": "Creative, experimental approaches"
        },
        "focused": {
            "temperature": 0.2,
            "creativity_weight": 0.1,
            "consistency_weight": 0.9,
            "description": "Highly focused, specific outcomes"
        }
    }
    
    # Schema Version
    SCHEMA_VERSION = "1.0.0"
    
    # Example Bank Limits
    MAX_EXAMPLES_PER_AGENT = 3
    MIN_EXAMPLES_PER_AGENT = 2

# =============================================================================
# TESTING CONSTANTS
# =============================================================================

class Testing:
    """Testing and validation constants"""
    
    # Test Configuration
    TEST_SESSION_PREFIX = "test_"
    TEST_TIMEOUT = 30  # seconds
    
    # Performance Thresholds
    MAX_RESPONSE_TIME_MS = 5000
    MIN_SUCCESS_RATE = 0.8
    
    # Validation Thresholds
    MIN_PROMPT_SCHEMA_COVERAGE = 0.75
    MIN_AGENT_SUCCESS_RATE = 0.8

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_full_backend_url(path: str = "") -> str:
    """Get complete backend URL with path"""
    return URLs.backend_url(path)

def get_full_frontend_url(path: str = "") -> str:
    """Get complete frontend URL with path"""
    return URLs.frontend_url(path)

def get_oauth_redirect_uri() -> str:
    """Get primary OAuth redirect URI"""
    return OAuth.REDIRECT_URIS[0]

def get_database_config(db_type: str = "mongodb") -> dict:
    """Get database configuration"""
    if db_type == "mongodb":
        return {
            "uri": URLs.mongodb_url(),
            "database": Database.MONGODB_DATABASE,
            "timeout": Database.MONGODB_TIMEOUT_MS
        }
    elif db_type == "arangodb":
        return {
            "url": URLs.arangodb_url(),
            "database": Database.ARANGO_DATABASE,
            "timeout": Database.ARANGO_TIMEOUT
        }
    elif db_type == "redis":
        return {
            "url": URLs.redis_url(),
            "database": Database.REDIS_DATABASE,
            "timeout": Database.REDIS_TIMEOUT
        }
    else:
        raise ValueError(f"Unknown database type: {db_type}")

# Export all constants for easy importing  
__all__ = [
    'Ports', 'URLs', 'OAuth', 'App', 'Database', 'Agents', 'PTG', 'Testing',
    'PTG_MODES', 'BACKEND_PORT', 'FRONTEND_PORT',
    'get_full_backend_url', 'get_full_frontend_url', 'get_oauth_redirect_uri',
    'get_database_config'
]

# Legacy exports for backward compatibility
BACKEND_PORT = Ports.BACKEND_PORT
FRONTEND_PORT = Ports.FRONTEND_PORT

# PTG Modes Export
PTG_MODES = PTG.MODES
