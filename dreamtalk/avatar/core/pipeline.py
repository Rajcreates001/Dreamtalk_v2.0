# Dreamtalk - Avatar Module
# Migrated from Dreamtalk-Avatar-Module

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    ASSETS_AVATARS_DIR: str = "assets/avatars"
    ASSETS_OUTPUTS_DIR: str = "assets/outputs"
    WEIGHTS_DIR: str = "weights"

    DID_API_KEY: str = ""
    DID_API_URL: str = "https://api.d-id.com"
    PUBLIC_BASE_URL: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
