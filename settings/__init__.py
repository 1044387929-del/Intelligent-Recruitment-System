from datetime import timedelta
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

    JWT_SECRET_KEY: str = "sfsdfsadfsdfjgafsd"
    JWT_ACCESS_TOKEN_EXPIRES: timedelta = timedelta(days=365)
    JWT_REFRESH_TOKEN_EXPIRES: timedelta = timedelta(days=365)
    
    # redis配置
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379

    # 邀请码过期时间
    INVITE_CODE_EXPIRE = 60 * 60 * 24 * 2

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+psycopg://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()