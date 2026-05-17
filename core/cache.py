"""
缓存模块，用于缓存数据，提高性能
缓存分为两种：
1. 邀请码缓存
2. 其他缓存
"""
from core.single import SingletonMeta
from fastapi_cache import FastAPICache
from settings import settings
from fastapi_cache.backends.redis import RedisBackend
from typing import Optional
from schemas.cache_schema import InviteInfoSchema, DingTalkTokenInfoSchema, TaskInfoSchema

class HRCache(metaclass=SingletonMeta):
    """
    缓存类，用于缓存数据，提高性能
    """
    invite_prefix = 'invite:'
    dingtalk_prefix = 'dingtalk:'
    task_prefix = 'task:'

    def __init__(self):
        # 获取缓存后端
        self.cache_backend: RedisBackend = FastAPICache.get_backend()
    
    invite_prefix = 'invite:'

    async def set(self, key, value, ex) -> None:
        """
        设置缓存。

        key 为「逻辑键」（不含前缀），真实 Redis 键为 invite_prefix + key。
        邀请场景下 key 应传邮箱字符串，最终键名为 invite:{邮箱}。
        """
        await self.cache_backend.set(self.invite_prefix + key, value, expire=ex)
    
    async def get(self, key) -> Optional[str]:
        """
        获取缓存。

        与 set 对称：同样只传逻辑键，内部统一拼一次 invite_prefix。
        切勿在调用方先拼好 "invite:xxx" 再传入，否则会变成 invite:invite:xxx，读写对不上。
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
        设置邀请码缓存。

        与 get_invite_info 保持一致：都通过 set/get，且第一参数仅为邮箱字符串，
        保证 Redis 键始终为 invite:{邮箱}（前缀只加一次）。
        """
        await self.set(
            str(invite_info.email),
            invite_info.model_dump_json(),
            settings.INVITE_CODE_EXPIRE,
        )

    async def get_invite_info(self, email: str) -> Optional[InviteInfoSchema]:
        """
        获取邀请码缓存。

        必须与 set_invite_info 使用相同的逻辑键（邮箱），并同样走 self.get，
        才能命中 set_invite_info 写入的同一条记录。
        """
        invite_info = await self.get(str(email))
        if invite_info is not None:
            # model_validate_json 会自动将json转换为Pydantic模型
            invite_info = InviteInfoSchema.model_validate_json(invite_info)
            return invite_info
        return None

    async def set_dingtalk_info(self, dingtalk_info: DingTalkTokenInfoSchema):
        key = f"{self.dingtalk_prefix}{dingtalk_info.user_id}"
        await self.set(key, dingtalk_info.model_dump_json(), ex=60*60*24*29)
    
    async def get_dingtalk_info(self, user_id: str) -> DingTalkTokenInfoSchema | None:
        key = f"{self.dingtalk_prefix}{user_id}"
        token_json = await self.get(key)
        if token_json is not None:
            return DingTalkTokenInfoSchema.model_validate_json(token_json)
        return None
            
    async def set_task_info(self, task_info: TaskInfoSchema):
        """
        设置任务信息缓存
        """
        key = f"{self.task_prefix}{task_info.task_id}"
        # 60分钟过期
        await self.set(key, task_info.model_dump_json(), ex=60*60)

    async def get_task_info(self, task_id: str) -> TaskInfoSchema | None:
        key = f"{self.task_prefix}{task_id}"
        task_json = await self.get(key)
        if task_json is not None:
            task_info = TaskInfoSchema.model_validate_json(task_json)
            return task_info
        return None