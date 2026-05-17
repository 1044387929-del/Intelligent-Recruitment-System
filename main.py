from fastapi import FastAPI
# from . import models
from routers.user_router import router as user_router
from routers.position_router import router as position_router
from routers.candidate_router import router as candidate_router
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager
from redis import asyncio as aioredis
from settings import settings
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache import FastAPICache
from scheduler import start_email_polling

@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    初始化redis和缓存
    1. 初始化redis客户端
    2. 初始化缓存
    3. 返回一个异步上下文管理器
    """
    redis_client = aioredis.from_url(
        f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
        encoding='utf-8',
        decode_responses=True,
    )
    # 初始化缓存
    cache_backend = RedisBackend(redis_client)
    FastAPICache.init(cache_backend, prefix='fastapi-cache')
    bot, scheduler = await start_email_polling()
    yield
    # 程序即将退出之前执行逻辑
    await redis_client.close()
    if bot.is_connected:
        await bot.close()

    if scheduler.running:
        scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

app.include_router(user_router)
app.include_router(position_router)
app.include_router(candidate_router)
@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)