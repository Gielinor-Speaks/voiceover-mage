# ABOUTME: Application configuration using Pydantic Settings for environment variables
# ABOUTME: Provides type-safe access to API keys, logging config, and other runtime settings

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Application configuration with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_prefix="VOICEOVER_MAGE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore unknown environment variables
    )
    
    # AI/API Configuration
    gemini_api_key: str = Field(
        default="",
        description="Google Gemini API key for NPC data extraction"
    )
    
    # Logging Configuration
    log_mode: Literal["interactive", "production"] = Field(
        default="interactive",
        description="Logging output mode"
    )
    
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging verbosity level"
    )
    
    log_file: Path | None = Field(
        default=None,
        description="Custom log file path (overrides default)"
    )


# Global config instance - lazy loaded when first accessed
_config_instance: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance.
    
    Creates the config on first access, subsequent calls return the same instance.
    
    Returns:
        Config: The application configuration instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


def reload_config() -> Config:
    """Reload configuration from environment variables.
    
    Useful for testing or when environment variables change at runtime.
    
    Returns:
        Config: A fresh configuration instance
    """
    global _config_instance
    _config_instance = Config()
    return _config_instance