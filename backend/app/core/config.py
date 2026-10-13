from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    database_url: str = "sqlite:///./reconforge.db"
    frontend_origin: str = "http://localhost:5173"
    local_token_path: str = str(PROJECT_ROOT / ".local" / "token")
    host: str = "127.0.0.1"
    port: int = 8000

    model_config = SettingsConfigDict(
        env_file=[str(PROJECT_ROOT / ".env"), ".env", "../.env"],
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
