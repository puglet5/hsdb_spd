from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_url: str = Field(default=...)
    db_email: str = Field(default=...)
    db_password: str = Field(default=...)
    db_client_id: str = Field(default=...)
    db_parent_model: str = Field(default="sample")
    access_token: str | None = None
    refresh_token: str | None = None
    token_created_at: int | None = None

    class Config:
        extra = "allow"
        env_file: str = ".env"
        env_file_encoding: str = "utf-8"


settings: Settings = Settings()
