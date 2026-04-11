from pydantic_settings import BaseSettings
from pydantic import computed_field
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    # DB
    DB_USERNAME: str = "hr_user"
    DB_PASSWORD: str = "hfw"
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 5432
    DB_NAME: str = "hr_db"

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+psycopg://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()