from models import AsyncSessionFactory

async def get_session_instance():
    session = AsyncSessionFactory()
    try:
        yield session
    finally:
        await session.close()