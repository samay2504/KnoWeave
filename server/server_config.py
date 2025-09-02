"""
Server Configuration Module
Handles environment var    # OAuth settings
    google_oauth_json_path: Optional[str] = Field(
        default=None, alias="GOOGLE_OAUTH_JSON_PATH"
    )
    google_oauth_json: Optional[str] = Field(default=None, alias="GOOGLE_OAUTH_JSON")
    google_oauth_client_id: Optional[str] = Field(
        default=None, alias="GOOGLE_OAUTH_CLIENT_ID"
    )
    google_oauth_client_secret: Optional[str] = Field(
        default=None, alias="GOOGLE_OAUTH_CLIENT_SECRET"
    )

    # JWT & Security settings
    jwt_secret: str = Field(default="change_me_in_production", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_seconds: int = Field(default=3600, alias="JWT_EXPIRE_SECONDS")
    cookie_secure: bool = Field(default=True, alias="COOKIE_SECURE")
    cookie_samesite: str = Field(default="Lax", alias="COOKIE_SAMESITE")ration settings including Google OAuth
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, ConfigDict

# Import global constants
try:
    from .constants import Ports, URLs, OAuth, Database, App
except ImportError:
    from constants import Ports, URLs, OAuth, Database, App

# Load environment variables from env file
try:
    from dotenv import load_dotenv

    # Try loading from root directory first, then server directory
    root_env_path = Path(__file__).parent.parent / ".env"
    server_env_path = Path(__file__).parent / ".env"

    if root_env_path.exists():
        load_dotenv(dotenv_path=root_env_path, verbose=True)
        print(f"Loaded .env file from: {root_env_path}")
    elif server_env_path.exists():
        load_dotenv(dotenv_path=server_env_path, verbose=True)
        print(f"Loaded .env file from: {server_env_path}")
    else:
        print("No .env file found in root or server directory")

except ImportError:
    print("python-dotenv not available - environment variables from system only")
except Exception as e:
    print(f"Error loading .env file: {e}")


class ServerConfig(BaseSettings):
    """Server configuration with environment variable support"""

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Environment settings
    environment: str = Field(default="development", alias="ENVIRONMENT")

    # Server settings - using global constants
    host: str = Field(default=Ports.BACKEND_HOST, alias="HOST")
    port: int = Field(default=Ports.BACKEND_PORT, alias="PORT")
    backend_port: int = Field(default=Ports.BACKEND_PORT, alias="BACKEND_PORT")
    frontend_port: int = Field(default=Ports.FRONTEND_PORT, alias="FRONTEND_PORT")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Database settings - using global constants
    database_mode: str = Field(default="mongodb", alias="DATABASE_MODE")  # mongodb, arangodb, or both
    mongo_uri: str = Field(
        default=URLs.mongodb_url(), alias="MONGO_URI"
    )
    arango_url: str = Field(default=URLs.arangodb_url(), alias="ARANGO_URL")
    arango_user: str = Field(default=Database.ARANGO_USERNAME, alias="ARANGO_USER")
    arango_password: str = Field(default="password", alias="ARANGO_PASSWORD")
    arango_database: str = Field(default=Database.ARANGO_DATABASE, alias="ARANGO_DATABASE")
    redis_url: str = Field(default=URLs.redis_url(), alias="REDIS_URL")

    # Google OAuth Configuration
    google_oauth_json_path: Optional[str] = Field(
        default=None, alias="GOOGLE_OAUTH_JSON_PATH"
    )
    google_oauth_json_file: Optional[str] = Field(
        default=None, alias="GOOGLE_OAUTH_JSON_FILE"
    )
    google_oauth_json: Optional[str] = Field(default=None, alias="GOOGLE_OAUTH_JSON")
    google_oauth_client_id: Optional[str] = Field(
        default=None, alias="GOOGLE_OAUTH_CLIENT_ID"
    )
    google_oauth_client_secret: Optional[str] = Field(
        default=None, alias="GOOGLE_OAUTH_CLIENT_SECRET"
    )

    # JWT & Security settings
    jwt_secret: str = Field(default="change_me_in_production", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_seconds: int = Field(default=3600, alias="JWT_EXPIRE_SECONDS")
    cookie_secure: bool = Field(default=True, alias="COOKIE_SECURE")
    cookie_samesite: str = Field(default="Lax", alias="COOKIE_SAMESITE")

    # Frontend Configuration - using global constants
    frontend_url: str = Field(default=URLs.frontend_url(), alias="FRONTEND_URL")

    # LLM Provider settings
    llm_provider_preference: List[str] = Field(
        default=[
            "google_genai",
            "groq",
            "openrouter",
            "huggingface",
            "openai",
            "fallback",
        ],
        alias="LLM_PROVIDER_PREFERENCE",
    )

    # API Keys
    huggingface_api_token: Optional[str] = Field(
        default=None, alias="HUGGINGFACEHUB_API_TOKEN"
    )
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    openrouter_api_key: Optional[str] = Field(default=None, alias="OPENROUTER_API_KEY")

    def get_google_oauth_config(self) -> Dict[str, Any]:
        """
        Get Google OAuth configuration from JSON file or environment variable
        Returns the OAuth configuration dict or raises an error if not found
        """
        # Try to load from JSON file first (GOOGLE_OAUTH_JSON_PATH)
        json_path_to_check = self.google_oauth_json_path or self.google_oauth_json_file
        
        if json_path_to_check:
            json_path = Path(json_path_to_check)
            if not json_path.is_absolute():
                # Get the directory where this config file is located (server directory)
                server_dir = Path(__file__).parent
                json_path = server_dir / json_path

            if json_path.exists():
                try:
                    with open(json_path, "r") as f:
                        oauth_config = json.load(f)

                    # Validate structure
                    if "installed" in oauth_config:
                        return oauth_config["installed"]
                    elif "web" in oauth_config:
                        return oauth_config["web"]
                    else:
                        logging.warning(f"Invalid OAuth JSON structure in {json_path}")

                except json.JSONDecodeError as e:
                    logging.error(f"Invalid JSON in OAuth file {json_path}: {e}")
                except Exception as e:
                    logging.error(f"Error reading OAuth file {json_path}: {e}")

        # Try to load from environment variable as JSON string
        if self.google_oauth_json:
            try:
                oauth_config = json.loads(self.google_oauth_json)
                if "installed" in oauth_config:
                    return oauth_config["installed"]
                elif "web" in oauth_config:
                    return oauth_config["web"]
                else:
                    return oauth_config
            except json.JSONDecodeError as e:
                logging.error(
                    f"Invalid JSON in GOOGLE_OAUTH_JSON environment variable: {e}"
                )

        # Fallback to individual environment variables
        if self.google_oauth_client_id and self.google_oauth_client_secret:
            return {
                "client_id": self.google_oauth_client_id,
                "client_secret": self.google_oauth_client_secret,
                "auth_uri": OAuth.AUTH_URI,
                "token_uri": OAuth.TOKEN_URI,
                "redirect_uris": OAuth.REDIRECT_URIS,
            }

        # No OAuth configuration found
        error_msg = (
            "Google OAuth configuration not found. Please set one of:\n"
            "1. GOOGLE_OAUTH_JSON_PATH or GOOGLE_OAUTH_JSON_FILE pointing to a valid JSON file\n"
            "2. GOOGLE_OAUTH_JSON as a JSON string\n"
            "3. GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET\n"
            "See .env.example for configuration details."
        )

        # Write to ERRORS.md for the developer
        error_file = Path(__file__).parent.parent / "ERRORS.md"
        try:
            with open(error_file, "a") as f:
                f.write(f"\n## Google OAuth Configuration Error\n")
                f.write(
                    f"Timestamp: {logging.Formatter().formatTime(logging.LogRecord('', 0, '', 0, '', (), None))}\n"
                )
                f.write(f"Error: {error_msg}\n")
                f.write(f"Expected paths checked:\n")
                f.write(f"- GOOGLE_OAUTH_JSON_PATH: {self.google_oauth_json_path}\n")
                f.write(f"- GOOGLE_OAUTH_JSON_FILE: {self.google_oauth_json_file}\n")
                f.write(
                    f"- File exists: {Path(json_path_to_check).exists() if json_path_to_check else 'N/A'}\n"
                )
                f.write(f"\n")
        except Exception:
            pass  # Ignore errors writing to ERRORS.md

        raise ValueError(error_msg)

    # Frontend settings
    frontend_url: str = Field(default="http://localhost:3000", alias="FRONTEND_URL")
    backend_url: str = Field(default="http://localhost:8000", alias="BACKEND_URL")

    # Local LLM settings
    local_llm_url: str = Field(default="http://localhost:5000", alias="LOCAL_LLM_URL")
    local_llm_enabled: bool = Field(default=False, alias="LOCAL_LLM_ENABLED")

    # Session settings
    session_timeout: int = Field(default=3600, alias="SESSION_TIMEOUT")
    max_backtrack_depth: int = Field(default=2, alias="MAX_BACKTRACK_DEPTH")
    max_branches: int = Field(default=3, alias="MAX_BRANCHES")
    idle_timeout: int = Field(default=60, alias="IDLE_TIMEOUT")
    suggestion_cooldown: int = Field(default=300, alias="SUGGESTION_COOLDOWN")

    # Performance settings
    chunk_size: int = Field(default=1000, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, alias="CHUNK_OVERLAP")
    embedding_batch_size: int = Field(default=32, alias="EMBEDDING_BATCH_SIZE")
    max_graph_nodes: int = Field(default=1000, alias="MAX_GRAPH_NODES")

    # Security & Auth
    secret_key: str = Field(
        default="your-secret-key-change-in-production", alias="SECRET_KEY"
    )
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # OAuth Settings
    google_oauth_client_id: Optional[str] = Field(
        default=None, alias="GOOGLE_OAUTH_CLIENT_ID"
    )
    google_oauth_client_secret: Optional[str] = Field(
        default=None, alias="GOOGLE_OAUTH_CLIENT_SECRET"
    )
    oauth_redirect_uri: str = Field(
        default="http://localhost:3000/auth/callback", alias="OAUTH_REDIRECT_URI"
    )
    jwt_secret: str = Field(
        default="your-jwt-secret-change-in-production", alias="JWT_SECRET"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_seconds: int = Field(default=86400, alias="JWT_EXPIRE_SECONDS")
    cookie_domain: Optional[str] = Field(default=None, alias="COOKIE_DOMAIN")
    cookie_secure: bool = Field(default=False, alias="COOKIE_SECURE")

    @field_validator("llm_provider_preference", mode="before")
    @classmethod
    def parse_provider_preference(cls, v):
        if isinstance(v, str):
            return [p.strip() for p in v.split(",")]
        return v

    def get_google_oauth_credentials(self) -> Optional[Dict[str, Any]]:
        """Get Google OAuth credentials from file or environment variable"""
        if self.google_oauth_json_path:
            # Resolve path relative to server directory
            json_path = Path(self.google_oauth_json_path)
            if not json_path.is_absolute():
                # Get the directory where this config file is located (server directory)
                server_dir = Path(__file__).parent
                json_path = server_dir / json_path

            if json_path.exists():
                try:
                    with open(json_path, "r") as f:
                        return json.load(f)
                except Exception as e:
                    logging.warning(f"Failed to load Google OAuth from file: {e}")

        if self.google_oauth_json:
            try:
                return json.loads(self.google_oauth_json)
            except Exception as e:
                logging.warning(f"Failed to parse Google OAuth JSON: {e}")

        return None

    @property
    def GOOGLE_OAUTH_CLIENT_ID(self) -> str:
        """Get Google OAuth Client ID"""
        if self.google_oauth_client_id:
            return self.google_oauth_client_id

        creds = self.get_google_oauth_credentials()
        if creds and "web" in creds:
            return creds["web"]["client_id"]
        raise ValueError("Google OAuth Client ID not configured")

    @property
    def GOOGLE_OAUTH_CLIENT_SECRET(self) -> str:
        """Get Google OAuth Client Secret"""
        if self.google_oauth_client_secret:
            return self.google_oauth_client_secret

        creds = self.get_google_oauth_credentials()
        if creds and "web" in creds:
            return creds["web"]["client_secret"]
        raise ValueError("Google OAuth Client Secret not configured")

    @property
    def OAUTH_REDIRECT_URI(self) -> str:
        """Get OAuth redirect URI"""
        return self.oauth_redirect_uri

    @property
    def JWT_SECRET(self) -> str:
        """Get JWT secret"""
        return self.jwt_secret

    @property
    def JWT_ALGORITHM(self) -> str:
        """Get JWT algorithm"""
        return self.jwt_algorithm

    @property
    def JWT_EXPIRE_SECONDS(self) -> int:
        """Get JWT expiration seconds"""
        return self.jwt_expire_seconds

    @property
    def COOKIE_DOMAIN(self) -> Optional[str]:
        """Get cookie domain"""
        return self.cookie_domain

    @property
    def COOKIE_SECURE(self) -> bool:
        """Get cookie secure flag"""
        return self.cookie_secure

    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration for provider initialization"""
        return {
            "provider_preference": self.llm_provider_preference,
            "temperature": 0.39,
            "max_tokens": 2048,
            "api_keys": {
                "huggingface": self.huggingface_api_token,
                "google": self.google_api_key,
                "openai": self.openai_api_key,
                "groq": self.groq_api_key,
            },
            "local_llm": {
                "enabled": self.local_llm_enabled,
                "url": self.local_llm_url,
            },
        }

    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return {
            "mongo": {"uri": self.mongo_uri, "database": "human_ai_cocreation"},
            "arango": {
                "url": self.arango_url,
                "user": self.arango_user,
                "password": self.arango_password,
                "database": self.arango_database,
            },
            "redis": {"url": self.redis_url},
        }


# Remove old Config class - using model_config instead


logger = logging.getLogger(__name__)


# Validate configuration on import
def validate_config() -> None:
    """Validate essential configuration settings"""
    try:
        config = ServerConfig()
    except Exception as e:
        logging.warning(f"Configuration validation failed: {e}")
        return

    issues = []

    # Check if at least one LLM provider is configured
    has_llm_provider = any(
        [
            config.huggingface_api_token,
            config.google_api_key,
            config.openai_api_key,
            config.groq_api_key,
            config.openrouter_api_key,
            config.local_llm_enabled,
        ]
    )

    if not has_llm_provider:
        issues.append(
            "No LLM provider configured. Set at least one API key or enable local LLM."
        )

    # Check Google OAuth configuration
    try:
        oauth_creds = config.get_google_oauth_credentials()
        if not oauth_creds:
            issues.append(
                "Google OAuth not configured. Set GOOGLE_OAUTH_JSON_FILE or GOOGLE_OAUTH_JSON."
            )
    except Exception:
        issues.append("Google OAuth configuration error.")

    if issues:
        logger.warning(f"Configuration issues detected: {'; '.join(issues)}")
        logger.info("The system will use fallback modes where possible.")


# Validate configuration
validate_config()

# Export global config instance
config = ServerConfig()
