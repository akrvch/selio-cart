from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(alias="DATABASE_URL", default="")
    http_port: int = Field(alias="HTTP_PORT", default=8080)
    grpc_port: int = Field(alias="GRPC_PORT", default=50051)
    app_env: str = Field(alias="APP_ENV", default="dev")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

def _load_yaml_defaults(env: str) -> dict[str, Any]:
    cfg_path = Path(__file__).parent / "config" / f"{env}.yaml"
    if cfg_path.exists():
        with cfg_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return {
                "DATABASE_URL": data.get("database_url", ""),
                "HTTP_PORT": data.get("http_port", 8080),
                "GRPC_PORT": data.get("grpc_port", 50051),
            }
    return {}


def load_settings() -> Settings:
    env = os.getenv("APP_ENV", "dev")
    defaults = _load_yaml_defaults(env)
    # Apply defaults only if not set in environment
    for key, value in defaults.items():
        os.environ.setdefault(key, str(value))
    return Settings()


settings = load_settings()


