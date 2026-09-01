"""Global engine configuration and environment management."""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SAEConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    workspace_root: Path = Field(default=Path("./sae_workspace"))
    db_path: Path = Field(default=Path("./sae_state.db"))
    log_level: str = Field(default="INFO")
    offline_mode: bool = Field(default=False)

    default_provider: str = Field(default="local")
    provider_priority: list[str] = Field(default=["local", "gemini", "mock"])
    
    local_provider_runtime: str = Field(default="ollama")
    local_provider_endpoint: str = Field(default="http://localhost:11434")
    local_model_name: str = Field(default="qwen3:8b")
    local_timeout_seconds: float = Field(default=60.0)

    gemini_api_key: str | None = Field(default=None)
    gemini_model_name: str = Field(default="gemini-2.5-flash")
    gemini_timeout_seconds: float = Field(default=30.0)

    max_provider_retries: int = Field(default=2)
    retry_backoff_base_seconds: float = Field(default=1.0)


settings = SAEConfig()