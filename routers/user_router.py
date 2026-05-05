import random
from aiosmtplib import SMTPResponseException
import string
from fastapi import APIRouter, Depends, status, BackgroundTasks
from pydantic import EmailStr
from core.mail import create_mail_instance
from schemas.user_schema import UserListRespSchema, UserLoginSchema, UserStatusUpdateSchema
from schemas import ResponseSchema
from dependencies import (
    get_session_instance, 
    get_auth_handler, 
    get_super_user
)
from models import AsyncSession
from models.user import UserModel, UserStatus
from repository.user_repo import UserRepo
from fastapi.exceptions import HTTPException
from core.auth import AuthHandler
from schemas.user_schema import UserLoginRespSchema, UserInviteSchema, UserRegisterSchema
from core.cache import HRCache, InviteInfoSchema
from repository.user_repo import DepartmentRepo
from dependencies import (
    get_cache_instance, 
    get_current_user
)
from fastapi_mail import FastMail, MessageSchema
from loguru import logger


# 通过docs访问的时候，对API进行分组
router = APIRouter(prefix='/user', tags=['user'])

async def send_email_task(message: MessageSchema):
    mail_config: FastMail = create_mail_instance()
    try:
        await mail_config.send_message(message)
    except SMTPResponseException as e:
        if e.code == -1 and b'\\x00\\x00\\x00' in str(e).encode():
            logger.info("⚠️ 忽略 QQ 邮箱 SMTP 关闭阶段的非标准响应（邮件已成功发送）", enqueue=True)
        else:
            logger.error(f"邮件发送失败！{e}")
        

async def send_invite_email_task(
    email: str,
    invite_code: str
):
    # 发送邮件
    message = MessageSchema(
        subject="【知了课堂】注册邀请",
        recipients=[email],
        body=f"您好，您的邮箱是：{email}，验证码是：{invite_code}，一天内有效。",
        subtype="plain"
    )
    await send_email_task(message)
    

@router.post(path='/login', summary='登录', response_model=UserLoginRespSchema)
async def login(
    login_data: UserLoginSchema,
    session: AsyncSession = Depends(get_session_instance),
    auth_handler: AuthHandler = Depends(get_auth_handler)
):
    """
    用户登录
    Args:
        login_data: 登录数据
        session: 数据库会话
        auth_handler: 认证处理器
    Returns:
        UserLoginRespSchema: 登录响应数据
    Raises:
        HTTPException: 用户不存在或密码错误
    """
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
        # 判断员工状态
        if user.status == UserStatus.BLOCKED:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="该用户已被禁用")
        # 生成jwt token
        tokens = auth_handler.encode_login_token(user.id)
        return {
            "access_token": tokens['access_token'],
            "refresh_token": tokens['refresh_token'],
            "user": user
        }

@router.post(
    '/invite', 
    summary='邀请用户', 
    response_model=ResponseSchema
    )
async def invite_user(
    invite_data: UserInviteSchema,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session_instance),
    # 缓存实例
    # 这里使用了依赖注入，是因为我们可以在路由函数中使用缓存实例，而不需要在路由函数中创建缓存实例
    cache: HRCache = Depends(get_cache_instance),
    # python中，下划线开头的是一个特殊的变量，表示这个变量是一个私有的变量，不会被外部访问，
    # 这里之所以用下划线开头，是因为我们不需要使用这个变量，只是为了满足依赖注入的类型提示
    _: UserModel = Depends(get_current_user),
):
    """
    邀请用户
    Args:
        invite_data: 邀请数据
        session: 数据库会话
        auth_handler: 认证处理器
    Returns:
        ResponseSchema: 响应数据
    Raises:
        HTTPException: 邀请失败
    """
    email = invite_data.email
    department_id = invite_data.department_id
    # 这个上下文管理器是用来保证事务的完整性，如果事务中发生错误，会自动回滚
    async with session.begin():
        # 先校验用户是否存在
        user_repo = UserRepo(session)
        user = await user_repo.get_by_email(str(invite_data.email))
        if user:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="该用户已存在")
        # 2. 再校验部门是否存在
        department_repo = DepartmentRepo(session)
        department = await department_repo.get_by_id(invite_data.department_id)
        if not department:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='该部门不存在')
    
    # 生成邀请码，随机六位整数
    invite_code: str = "".join(random.sample(string.digits, 6))

    # 将邀请信息保存在缓存中
    await cache.set_invite_info(InviteInfoSchema(email=email, department_id=department_id, invite_code=invite_code))

    # 给指定用户发送邮件
    background_tasks.add_task(
        send_invite_email_task,
        email=str(email),
        invite_code=invite_code
    )

    return ResponseSchema()

@router.post("/register", summary="注册")
async def register(
    register_data: UserRegisterSchema,
    session: AsyncSession = Depends(get_session_instance),
    cache: HRCache = Depends(get_cache_instance),
):
    """
    注册用户
    Args:
        register_data: 注册数据
        session: 数据库会话
        cache: 缓存实例
    Returns:
        ResponseSchema: 响应数据
    Raises:
        HTTPException: 注册失败
    """
    email = register_data.email
    # 1. 校验邮箱和邀请码是否正确
    invite_info: InviteInfoSchema = await cache.get_invite_info(str(email))
    if not invite_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邀请已失效或该邮箱尚未被邀请，请先完成邀请流程。",
        )
    if invite_info.invite_code != register_data.invite_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邀请码错误！")
    
    async with session.begin():
        # 3. 校验邮箱是否已经注册
        user_repo = UserRepo(session)
        user: UserModel = await user_repo.get_by_email(str(email))
        if user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="改邮箱已经被注册！")
        # 4. 创建用户
        await user_repo.create_user({
            "email": email,
            "username": register_data.username,
            "realname": register_data.realname,
            "password": register_data.password,
            "department_id": invite_info.department_id,
        })
    return ResponseSchema()

@router.get("/list", summary="获取用户列表", response_model=UserListRespSchema)
async def user_list(
    page: int = 1,
    size: int = 3,
    department_id: str | None= None,
    _: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_instance),
):
    """
    获取用户列表
    Args:
        page: 页码
        size: 每页条数
        department_id: 部门ID
        _: 当前用户
        session: 数据库会话
    Returns:
        UserListRespSchema: 用户列表响应数据
    """
    async with session.begin():
        user_repo = UserRepo(session)
        users = await user_repo.get_user_list(page=page, size=size, department_id=department_id)
    return {
        "users": users
    }

@router.patch("/status/update", summary="修改用户状态",
response_model=ResponseSchema)
async def update_user_status(
    status_data: UserStatusUpdateSchema,
    session: AsyncSession = Depends(get_session_instance),
    super_user: UserModel = Depends(get_super_user),
):
    """
    修改用户状态
    Args:
        user_id: 用户ID
        status: 用户状态
        session: 数据库会话
    """
    async with session.begin():
        user_repo = UserRepo(session)
        user: UserModel = await user_repo.get_by_id(status_data.user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户不存在")
        if user.is_superuser:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="超级用户不能被修改状态")
        user.status = status_data.status
    return ResponseSchema()
