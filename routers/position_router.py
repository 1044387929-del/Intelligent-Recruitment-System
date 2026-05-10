from fastapi import Depends, APIRouter, HTTPException, status
from dependencies import get_current_user
from models.user import UserModel
from models import AsyncSession
from dependencies import get_session_instance
from repository.position_repo import PositionRepo
from schemas.position_schema import PositionCreateSchema, PositionRespSchema

router = APIRouter(prefix='/position', tags=['position'])

@router.post("/create", summary='创建职位')
async def create_position(
    position_data: PositionCreateSchema,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_instance),
):
    async with session.begin():
        # repo实例是用来操作数据库的，所以需要传入session实例
        position_repo = PositionRepo(session)
        position_dict = position_data.model_dump()
        position_dict['creator_id'] = current_user.id
        position_dict['department_id'] = current_user.department_id
        position = await position_repo.create_position(position_dict)
        return {"position": position}