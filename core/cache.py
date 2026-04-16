from core.single import SingletonMeta
from fastapi_cache import FastAPICache

class HRCache(metaclass=SingletonMeta):
    def __init__(self):
        self.cache_backend = FastAPICache.get_cache_backend()
    
    invite_prefix = 'invite:'

    async def set(self, key, value, ex):
        await self.cache_backend.set(self.invite_prefix + key, value, ex)