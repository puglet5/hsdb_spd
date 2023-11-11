from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    hsdb_url: str = Field(default=...)
    hsdb_email: str = Field(default=...)
    hsdb_password: str = Field(default=...)
    hsdb_client_id: str = Field(default=...)
    access_token: str | None = None
    refresh_token: str | None = None
    token_created_at: int | None = None

    class Config:
        env_file: str = ".env"
        env_file_encoding: str = "utf-8"


settings: Settings = Settings()
