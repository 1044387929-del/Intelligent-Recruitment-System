from fastapi_mail import FastMail, ConnectionConfig
from pydantic import SecretStr, EmailStr
from settings import settings

def create_mail_instance() -> FastMail:
    """创建 FastMail 实例（每次调用返回新实例，线程/协程安全）"""
    mail_config = ConnectionConfig(
        # 邮箱用户名
        MAIL_USERNAME=settings.MAIL_USERNAME,
        # 邮箱密码
        MAIL_PASSWORD=SecretStr(settings.MAIL_PASSWORD),
        # 邮箱发件人
        MAIL_FROM=settings.MAIL_FROM,
        # 邮箱端口
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_SERVER=settings.MAIL_SERVER,
        # 邮箱发件人名称
        MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
        # 邮箱是否启用TLS
        MAIL_STARTTLS=settings.MAIL_STARTTLS,
        # 邮箱是否启用SSL
        MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
        # 是否使用凭证
        USE_CREDENTIALS=True,
        # 是否验证证书
        VALIDATE_CERTS=True,
    )
    return FastMail(mail_config)