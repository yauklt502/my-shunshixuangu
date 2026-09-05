from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SSP_", env_file=".env", extra="ignore")

    default_provider: str = "eastmoney"
    tdx_host: str = "115.238.90.165:7709"
    tdx_timeout: float = 6.0
    tdx_probe: bool = True
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()