from dataclasses import field
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
import re

from sqlalchemy import desc
from sqlalchemy.orm import descriptor_props
from models.user import UserStatus
from typing import Optional, List
from datetime import datetime
# from models.user import UserStatus


class UserLoginSchema(BaseModel):
    """
    用户登录信息
    """
    email: EmailStr = Field(..., description='邮箱账号')
    password: str = Field(..., description="密码", min_length=6, max_length=20)
    
    # @field_validator('password')
    # @classmethod
    # def password_re(cls, v: str) -> str:
    #     if not re.search(r"[A-Za-z]", v):
    #         raise ValueError("密码必须包含至少一个字母")
    #     if not re.search(r"\d", v):
    #         raise ValueError("密码必须包含至少一个数字")
    #     return v

class DepartmentSchema(BaseModel):
    """
    部门信息
    """
    id: str = Field(..., description="部门ID")
    name: str = Field(..., description="部门名称")
    description: Optional[str] = Field(..., description="部门描述")
    # 后续根据orm模型自动读取数据
    model_config = ConfigDict(from_attributes=True)

class UserSchema(BaseModel):
    """
    用户信息
    """
    id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    phone_number: Optional[str] = Field(..., description="手机号")
    realname: str = Field(..., description="真实姓名")
    avatar: Optional[str] = Field(..., description="头像")
    department: DepartmentSchema = Field(..., description="所属部门")
    status: UserStatus = Field(..., description="用户状态")
    is_superuser: bool = Field(..., description="是否是超级用户")
    is_hr: bool = Field(..., description="是否是HR")
    created_at: datetime = Field(..., description="创建时间")
    model_config = ConfigDict(from_attributes=True)

class UserLoginRespSchema(BaseModel):
    """
    登录响应信息
    """
    access_token: str = Field(..., description="access_token")
    refresh_token: str = Field(..., description="refresh_token")
    user: UserSchema = Field(..., description="user")

class UserInviteSchema(BaseModel):
    """
    邀请用户信息
    """
    email: EmailStr = Field(..., description="邮箱账号")
    department_id: str = Field(..., description="部门ID")

class UserRegisterSchema(BaseModel):
    """
    用户注册信息
    """
    email: EmailStr = Field(..., description="邮箱")
    invite_code: str = Field(..., min_length=6, max_length=6, description='邀请码')
    username: str = Field(..., description="用户名")
    realname: str = Field(..., description="真实姓名")
    password: str = Field(..., min_length=6, max_length=20, description="密码")

class UserListRespSchema(BaseModel):
    """
    用户列表响应信息
    """
    users: List[UserSchema]

class UserStatusUpdateSchema(BaseModel):
    """
    用户状态更新信息
    """
    user_id: str = Field(..., description="用户ID")
    status: UserStatus = Field(..., description="用户状态")

class UserStatusUpdateRespSchema(BaseModel):
    """
    用户状态更新响应信息
    """
    user_id: str = Field(..., description="用户ID")
    status: UserStatus = Field(..., description="用户状态")

class DepartmentListRespSchema(BaseModel):
    """
    部门列表响应信息
    """
    departments: List[DepartmentSchema]

class DingdingUserSchema(BaseModel):
    """
    钉钉用户信息
    """
    id: str = Field(..., description="钉钉用户ID")
    nick: str = Field(..., description="钉钉昵称")
    union_id: str = Field(..., description="钉钉unionID")
    open_id: str = Field(..., description="钉钉openID")
    mobile: str = Field(..., description="钉钉手机号")
    user_id: str = Field(..., description="用户ID")
    model_config = ConfigDict(from_attributes=True)

class DingdingUserRespSchema(BaseModel):
    """
    钉钉用户响应信息
    """
    dingding_user: DingdingUserSchema = Field(..., description="钉钉用户信息")

class AssignDepartmentSchema(BaseModel):
    """
    分配部门信息
    """
    hr_id: str = Field(..., description="HR用户ID")
    department_ids: List[str] = Field(..., description="部门ID列表")