from fastapi import APIRouter, Depends, status
from schemas.user_schema import UserLoginSchema
from dependencies import get_session_instance
from models import AsyncSession
from models.user import UserModel
from repository.user_repo import UserRepo
from fastapi.exceptions import HTTPException

# 通过docs访问的时候，对API进行分组
router = APIRouter(prefix='/user', tags=['user'])

@router.post(path='/login', summary='登录')
async def login(
    login_data: UserLoginSchema,
    session: AsyncSession = Depends(get_session_instance),
):
    # 开启事务
    async with session.begin():
        # 获取用户
        user_repo = UserRepo(session)
        user: UserModel =  await user_repo.get_by_email(str(login_data.email))
        if not user:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="该用户不存在")
        # 验证密码是否正确
        if not user.check_password(login_data.password):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="该用户不存在")
            