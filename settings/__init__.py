from datetime import timedelta
from pydantic_settings import BaseSettings
from pydantic import computed_field, Field
import os
import dotenv

dotenv.load_dotenv(r'settings/setting.env')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    # DB
    DB_USERNAME: str = Field(..., validation_alias="DB_USERNAME")
    DB_PASSWORD: str = Field(..., validation_alias="DB_PASSWORD")
    DB_HOST: str = Field(..., validation_alias="DB_HOST")
    DB_PORT: int = Field(..., validation_alias="DB_PORT")
    DB_NAME: str = Field(..., validation_alias="DB_NAME")

    JWT_SECRET_KEY: str = "sfsdfsadfsdfjgafsd"
    JWT_ACCESS_TOKEN_EXPIRES: timedelta = timedelta(days=365)
    JWT_REFRESH_TOKEN_EXPIRES: timedelta = timedelta(days=365)
    
    # redis配置
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379

    # 邀请码过期时间
    INVITE_CODE_EXPIRE: int = 60 * 60 * 24 * 2

    # 邮件配置
    ## 邮箱用户名
    MAIL_USERNAME: str = Field(..., validation_alias="MAIL_USERNAME")
    ## 邮箱密码
    MAIL_PASSWORD: str = Field(..., validation_alias="MAIL_PASSWORD")
    ## 邮箱发件人
    MAIL_FROM: str = Field(..., validation_alias="MAIL_FROM")
    ## 邮箱端口
    MAIL_PORT: int = 587
    ## 邮箱服务器
    MAIL_SERVER: str = "smtp.qq.com"
    ## 邮箱发件人名称
    MAIL_FROM_NAME: str = "小韩同学"
    ## 邮箱是否启用TLS
    MAIL_STARTTLS: bool = True
    ## 邮箱是否启用SSL
    MAIL_SSL_TLS: bool = False

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+psycopg://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()