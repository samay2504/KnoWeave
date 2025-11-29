"""
Configuration management with dynamic path resolution
Production-ready configuration system
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, Union
import logging

try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
except ImportError:
    # Fallback for older pydantic versions
    try:
        from pydantic import BaseSettings, Field
    except ImportError:
        # Mock for environments without pydantic
        class BaseSettings:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        def Field(**kwargs):
            return kwargs.get('default')

from .imports import import_manager

logger = logging.getLogger(__name__)

class DynamicConfig(BaseSettings):
    """
    Production-grade configuration system for Human-AI Co-Creation Platform
    
    Copyright (c) 2025 Samay Mehar. All rights reserved.
    Patent Pending - Samay Mehar
    
    Dynamic path resolution and environment variable support with secure defaults.
    """
    
    # Environment
    environment: str = Field(default="production", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    reload: bool = Field(default=True, env="RELOAD")
    
    # Frontend Configuration
    frontend_url: str = Field(default="http://localhost:3000", env="FRONTEND_URL")
    
    # Database Configuration
    database_mode: str = Field(default="both", env="DATABASE_MODE")
    mongo_uri: str = Field(default="mongodb://localhost:27017", env="MONGO_URI")
    mongodb_database: str = Field(default="human_ai_co_create", env="MONGODB_DATABASE")
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    arango_url: str = Field(default="http://localhost:8529", env="ARANGO_URL")
    arango_user: str = Field(default="root", env="ARANGO_USER")
    arango_password: str = Field(default="", env="ARANGO_PASSWORD")
    arango_database: str = Field(default="human_ai_co_create", env="ARANGO_DATABASE")
    
    # Authentication & Security
    jwt_secret: str = Field(default="dev-secret-key", env="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expire_seconds: int = Field(default=3600, env="JWT_EXPIRE_SECONDS")
    cookie_secure: bool = Field(default=True, env="COOKIE_SECURE")
    cookie_samesite: str = Field(default="Lax", env="COOKIE_SAMESITE")
    
    # Google OAuth
    google_oauth_json_path: Optional[str] = Field(default=None, env="GOOGLE_OAUTH_JSON_PATH")
    google_oauth_client_id: Optional[str] = Field(default=None, env="GOOGLE_OAUTH_CLIENT_ID")
    google_oauth_client_secret: Optional[str] = Field(default=None, env="GOOGLE_OAUTH_CLIENT_SECRET")
    
    # AI/LLM Configuration
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    google_api_key: Optional[str] = Field(default=None, env="GOOGLE_API_KEY") 
    groq_api_key: Optional[str] = Field(default=None, env="GROQ_API_KEY")
    openrouter_api_key: Optional[str] = Field(default=None, env="OPENROUTER_API_KEY")
    llm_provider_preference: str = Field(default='["groq", "google_genai", "huggingface", "openai", "fallback"]', env="LLM_PROVIDER_PREFERENCE")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Paths - Dynamic resolution
    _project_root: Optional[Path] = None
    _server_root: Optional[Path] = None
    _web_root: Optional[Path] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields in .env without validation errors
        
        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            """Custom source priority: env vars > .env file > init values"""
            return (env_settings, file_secret_settings, init_settings)
    
    @property
    def project_root(self) -> Path:
        """Get project root with dynamic discovery"""
        if self._project_root is None:
            from . import get_project_root
            self._project_root = get_project_root()
        return self._project_root
    
    @property
    def server_root(self) -> Path:
        """Get server root directory"""
        if self._server_root is None:
            self._server_root = self.project_root / "server"
        return self._server_root
    
    @property
    def web_root(self) -> Path:
        """Get web frontend root directory"""
        if self._web_root is None:
            self._web_root = self.project_root / "web"
        return self._web_root
    
    @property
    def web_build_path(self) -> Path:
        """Get web build directory for static files"""
        return self.web_root / "build"
    
    @property
    def logs_path(self) -> Path:
        """Get logs directory"""
        logs_dir = self.project_root / "logs"
        logs_dir.mkdir(exist_ok=True)
        return logs_dir
    
    @property
    def data_path(self) -> Path:
        """Get data directory"""
        data_dir = self.project_root / "data"
        data_dir.mkdir(exist_ok=True)
        return data_dir
    
    def get_google_oauth_credentials_path(self) -> Optional[Path]:
        """Get Google OAuth credentials file path with dynamic resolution"""
        if not self.google_oauth_json_path:
            return None
            
        # Handle relative paths
        cred_path = Path(self.google_oauth_json_path)
        if not cred_path.is_absolute():
            cred_path = self.project_root / cred_path
            
        return cred_path if cred_path.exists() else None
    
    def validate_paths(self) -> Dict[str, bool]:
        """Validate all important paths exist"""
        validations = {
            "project_root": self.project_root.exists(),
            "server_root": self.server_root.exists(),
            "web_root": self.web_root.exists(),
            "web_build": self.web_build_path.exists(),
        }
        
        if self.google_oauth_json_path:
            validations["google_oauth_credentials"] = (
                self.get_google_oauth_credentials_path() is not None
            )
        
        return validations
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary (excluding sensitive data)"""
        sensitive_fields = {
            'jwt_secret', 'arango_password', 'google_oauth_client_secret'
        }
        
        result = {}
        for field_name, field_value in self.__dict__.items():
            if not field_name.startswith('_') and field_name not in sensitive_fields:
                if isinstance(field_value, Path):
                    result[field_name] = str(field_value)
                else:
                    result[field_name] = field_value
        
        return result

def load_config(env_file: Optional[Union[str, Path]] = None) -> DynamicConfig:
    """
    Load configuration with automatic .env file discovery
    
    Args:
        env_file: Optional path to .env file
        
    Returns:
        Configured DynamicConfig instance
    """
    # Auto-discover .env file if not specified
    if env_file is None:
        from . import get_project_root
        project_root = get_project_root()
        env_candidates = [
            project_root / ".env",
            project_root / "server" / ".env",
            Path.cwd() / ".env"
        ]
        
        for candidate in env_candidates:
            if candidate.exists():
                env_file = candidate
                logger.debug(f"Found .env file at: {env_file}")
                break
    
    # Explicitly load .env file into environment
    if env_file:
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            logger.info(f"Loaded configuration from: {env_file}")
        except ImportError:
            logger.warning("python-dotenv not available, falling back to manual parsing")
            # Fallback manual parsing if dotenv not available
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ.setdefault(key.strip(), value.strip())
    
    return DynamicConfig()

# Global configuration instance
config = load_config()

__all__ = [
    'DynamicConfig',
    'load_config', 
    'config'
]
