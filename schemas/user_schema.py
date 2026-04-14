from dataclasses import field
from pydantic import BaseModel, EmailStr, Field, field_validator
import re

class UserLoginSchema(BaseModel):
    email: EmailStr = Field(..., description='邮箱账号')
    password: str = Field(..., description="密码", min_length=6, max_length=20)
    
    @field_validator
    @classmethod
    def password_re(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("密码必须包含至少一个字母")
        if not re.search(r"\d", v):
            raise ValueError("密码必须包含至少一个数字")
        return v