from pydantic import BaseSettings

class Settings(BaseSettings):
    hsdb_url: str
    hsdb_email: str
    hsdb_password: str
    hsdb_client_id: str
    access_token: str
    refresh_token: str
    token_created_at: int

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
