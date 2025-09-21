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
        extra="ignore",  # Ignore unknown environment variables
    )

    # AI/API Configuration
    gemini_api_key: str = Field(default="", description="Google Gemini API key for NPC data extraction")
    elevenlabs_api_key: str = Field(
        default="",
        description="ElevenLabs API key for voice generation",
    )

    # Database Configuration
    database_url: str = Field(
        default="sqlite+aiosqlite:///./npc_data.db", description="Database URL for async SQLite operations"
    )
    cache_enabled: bool = Field(default=True, description="Enable caching of NPC extractions")

    # Logging Configuration
    log_mode: Literal["interactive", "production"] = Field(default="interactive", description="Logging output mode")

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="Logging verbosity level"
    )

    log_file: Path | None = Field(default=None, description="Custom log file path (overrides default)")

    # Pipeline Validation Thresholds
    confidence_threshold: float = Field(
        default=0.70, description="Minimum character analysis confidence required for voice generation (0.0-1.0)"
    )
    content_diversity_threshold: float = Field(
        default=0.5, description="Minimum content diversity ratio for valid NPC pages (0.0-1.0)"
    )
    llm_enhancement_ratio: float = Field(
        default=1.5, description="Minimum data size increase ratio for meaningful LLM enhancement"
    )
    min_enhanced_data_size: int = Field(
        default=500, description="Minimum enhanced data size in characters to consider LLM extraction successful"
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
