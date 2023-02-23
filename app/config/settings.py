from pydantic import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    hsdb_url: str
    hsdb_email: str
    hsdb_password: str
    hsdb_client_id: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_created_at: Optional[int] = None

    class Config:
        env_file: str = ".env"
        env_file_encoding: str = 'utf-8'


settings: Settings = Settings()
