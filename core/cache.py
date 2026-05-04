"""
缓存模块，用于缓存数据，提高性能
缓存分为两种：
1. 邀请码缓存
2. 其他缓存
"""
from core.single import SingletonMeta
from fastapi_cache import FastAPICache
from pydantic import BaseModel, EmailStr
from settings import settings
from fastapi_cache.backends.redis import RedisBackend
from typing import Optional

class InviteInfoSchema(BaseModel):
    email: EmailStr
    department_id: str
    invite_code: str

class HRCache(metaclass=SingletonMeta):
    def __init__(self):
        # 获取缓存后端
        self.cache_backend: RedisBackend = FastAPICache.get_backend()
    
    invite_prefix = 'invite:'

    async def set(self, key, value, ex) -> None:
        """
        设置缓存
        """
        await self.cache_backend.set(self.invite_prefix + key, value, expire=ex)
    
    async def get(self, key) -> Optional[str]:
        """
        获取缓存
        """
        value = await self.cache_backend.get(self.invite_prefix + key)
        return value

    async def delete(self, key) -> None:
        """
        删除缓存
        """
        await self.cache_backend.clear(key)
    
    async def set_invite_info(self, invite_info: InviteInfoSchema):
        """
        设置邀请码缓存
        """
        key = f"{self.invite_prefix}{invite_info.email}"
        await self.cache_backend.set(key, invite_info.model_dump_json(), expire=settings.INVITE_CODE_EXPIRE)

    async def get_invite_info(self, email: str) -> Optional[InviteInfoSchema]:
        """
        获取邀请码缓存
        """
        key = f"{self.invite_prefix}{email}"
        invite_info = await self.get(key)
        if invite_info is not None:
            # model_validate_json 会自动将json转换为Pydantic模型
            invite_info = InviteInfoSchema.model_validate_json(invite_info)
            return invite_info
        return None

    