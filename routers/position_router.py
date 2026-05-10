from fastapi import Depends, APIRouter, HTTPException, status
from dependencies import get_current_user
from models.user import UserModel
from models import AsyncSession
from dependencies import get_session_instance
from repository.position_repo import PositionRepo
from schemas import ResponseSchema
from schemas.position_schema import PositionCreateSchema, PositionRespSchema, PositionListRespSchema

router = APIRouter(prefix='/position', tags=['position'])

@router.post("/create", summary='创建职位')
async def create_position(
    position_data: PositionCreateSchema,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_instance),
):
    """
    创建职位
    Args:
        position_data: 职位数据
        current_user: 当前用户
        session: 数据库会话
    Returns:
        PositionRespSchema: 职位响应数据
    """
    async with session.begin():
        # repo实例是用来操作数据库的，所以需要传入session实例
        position_repo = PositionRepo(session)
        position_dict = position_data.model_dump()
        position_dict['creator_id'] = current_user.id
        position_dict['department_id'] = current_user.department_id
        position = await position_repo.create_position(position_dict)
        return {"position": position}

@router.get("/list", summary='获取职位列表', response_model=PositionListRespSchema)
async def position_list(
    page: int = 1,
    size: int = 3,
    session: AsyncSession = Depends(get_session_instance),
    current_user: UserModel = Depends(get_current_user),
):
    """
    获取职位列表
    Args:
        page: 页码
        size: 每页条数
        session: 数据库会话
    Returns:
        PositionListRespSchema: 职位列表响应数据
    """
    async with session.begin():
        position_repo = PositionRepo(session=session)
        positions = await position_repo.get_position_list(user=current_user, page=page, size=size)
        return {"positions": positions}

@router.delete("/{position_id}", summary='删除职位', response_model=ResponseSchema)
async def delete_position(
    position_id: str,
    session: AsyncSession = Depends(get_session_instance),
    current_user: UserModel = Depends(get_current_user),
):
    """
    删除职位
    Args:
        position_id: 职位ID
        session: 数据库会话
        current_user: 当前用户
    """
    async with session.begin():
        position_repo = PositionRepo(session=session)
        position = await position_repo.get_position_by_id(position_id=position_id)
        if not position:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="职位不存在")
        # 如果用户不是超级用户 并且 职位所在部门不是当前用户所在部门
        if (not current_user.is_superuser) and (position.department_id != current_user.department.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限删除职位")
        
        # 删除职位
        await position_repo.delete_position_by_id(user=current_user, position_id=position_id)
        return ResponseSchema()