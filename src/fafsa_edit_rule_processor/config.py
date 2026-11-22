from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Service configuration, read from environment variables prefixed with FAFSA_."""

    model_config = SettingsConfigDict(env_prefix="FAFSA_")

    rules_path: Path = Path("config/rules.yaml")
    log_level: str = "INFO"
