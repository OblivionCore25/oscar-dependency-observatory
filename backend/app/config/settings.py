"""
OSCAR Dependency Graph Observatory — Application Configuration

Environment-based configuration using Pydantic BaseSettings.
Supports .env files and environment variable overrides.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- Application ---
    app_name: str = "OSCAR Dependency Graph Observatory"
    app_version: str = "0.1.0"
    debug: bool = False

    # --- Registry Base URLs ---
    npm_registry_url: str = "https://registry.npmjs.org"
    pypi_registry_url: str = "https://pypi.org/pypi"

    # --- Ingestion Defaults ---
    default_ingestion_depth: int = 3
    request_timeout_seconds: int = 30
    max_retries: int = 3

    # --- Storage ---
    storage_mode: str = "file"  # "file" | "sqlite" | "postgres"
    data_directory: str = "data"

    model_config = {
        "env_prefix": "OSCAR_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


# Singleton settings instance
settings = Settings()
