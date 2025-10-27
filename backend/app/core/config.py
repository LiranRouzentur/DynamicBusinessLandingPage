"""Configuration and settings - Ref: Product.md lines 909-914"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Google Maps API
    google_maps_api_key: str = Field(default="", env="GOOGLE_MAPS_API_KEY")
    
    # OpenAI API
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    
    # Asset Storage
    asset_store: str = Field(default="./artifacts", env="ASSET_STORE")
    inline_threshold_kb: int = Field(default=60, env="INLINE_THRESHOLD_KB")
    
    # Cache Settings
    cache_ttl_days: int = Field(default=14, env="CACHE_TTL_DAYS")
    
    # Server
    backend_host: str = Field(default="localhost", env="BACKEND_HOST")
    backend_port: int = Field(default=8000, env="BACKEND_PORT")
    
    # Frontend
    frontend_url: str = Field(default="http://localhost:5173", env="FRONTEND_URL")
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # API Configuration
    api_title: str = "Dynamic Business Landing Page API"
    api_version: str = "0.1.0"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


