from pydantic import BaseSettings


class Settings(BaseSettings):
    hsdb_url: str
    hsdb_email: str
    hsdb_password: str
    hsdb_client_id: str
    access_token: str | None = None
    refresh_token: str | None = None
    token_created_at: int | None = None

    class Config:
        env_file: str = ".env"
        env_file_encoding: str = "utf-8"


settings: Settings = Settings()
