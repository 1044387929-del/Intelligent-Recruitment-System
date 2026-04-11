import asyncio
from repository.user_repo import UserRepo, DepartmentRepo
from models import AsyncSessionFactory
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def init_department():
    async with 
