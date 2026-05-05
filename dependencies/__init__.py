from models import AsyncSessionFactory, AsyncSession
from core.auth import AuthHandler
from fastapi import Depends, HTTPException, status
from repository.user_repo import UserRepo
from models.user import UserModel, UserStatus
from core.cache import HRCache

auth_handler = AuthHandler()

async def get_session_instance():
    """
    获取数据库会话实例
    Returns:
        AsyncSession: 数据库会话实例
    """
    session = AsyncSessionFactory()
    try:
        yield session
    finally:
        await session.close()

async def get_auth_handler() -> AuthHandler:
    """
    获取认证处理器实例
    Returns:
        AuthHandler: 认证处理器实例
    """
    return auth_handler

async def get_user_id(
    iss: str = Depends(auth_handler.auth_access_dependency),
):
    """
    获取当前用户ID
    Args:
        iss: 认证信息
    Returns:
        str: 当前用户ID
    """
    return iss

async def get_current_user(
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session_instance),
) -> UserModel:
    """
    获取当前用户
    Args:
        user_id: 用户ID
        session: 数据库会话
    Returns:
        UserModel: 当前用户
    """
    async with session.begin():
        user_repo = UserRepo(session)
        user: UserModel = await user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该用户不存在！")
        if user.status != UserStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该用户状态异常！")
        return user

async def get_super_user(
    current_user: UserModel = Depends(get_current_user)
) -> UserModel:
    """
    获取超级用户
    Args:
        current_user: 当前用户
    Returns:
        UserModel: 超级用户
    """
    if current_user.is_superuser:
        return current_user
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足，无法访问！")

def get_cache_instance():
    """
    获取缓存实例
    Returns:
        HRCache: 缓存实例
    """
    return HRCache()

def get_super_user(
    current_user: UserModel = Depends(get_current_user)
) -> UserModel:
    """
    获取超级用户
    Args:
        current_user: 当前用户
    Returns:
        UserModel: 超级用户
    """
    if current_user.is_superuser:
        return current_user
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足，无法访问！")