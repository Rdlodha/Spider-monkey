from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://reconforge:reconforge@localhost:5432/reconforge"
    frontend_origin: str = "http://localhost:5173"
    local_token_path: str = "backend/.local/token"
    host: str = "127.0.0.1"
    port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
