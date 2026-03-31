from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    gemini_api_key: str
    api_secret_key: str
    admin_password: str
    screenshot_dir: Path = Path("/var/data/screenshots")

    class Config:
        env_file = ".env"
        extra = "ignore"
