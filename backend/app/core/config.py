from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AICTE ApproveFlow"
    app_env: str = "demo"
    secret_key: str = "change-me-in-production-use-a-long-random-string"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    use_sqlite: bool = True
    database_url: str = "postgresql+psycopg://approveflow:approveflow@localhost:5432/approveflow"
    sqlite_path: str = "./approveflow.db"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    upload_dir: str = "./uploads"
    max_upload_mb: int = 10

    smtp_enabled: bool = False
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from: str = "noreply@approveflow.demo"

    job_interval_seconds: int = 120
    demo_mode: bool = True
    clock_offset_days: int = 0

    @property
    def sqlalchemy_url(self) -> str:
        if self.use_sqlite:
            path = Path(self.sqlite_path).resolve()
            return f"sqlite:///{path.as_posix()}"
        return self.database_url

    @property
    def origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
