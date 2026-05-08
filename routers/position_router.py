from fastapi import Depends, APIRouter, HTTPException, status
from dependencies import get_current_user
from models.user import UserModel
from models import AsyncSession
from dependencies import get_session_instance
from schemas.position_schema import PositionCreateSchema

router = APIRouter(prefix='/position', tags=['position'])

@router.get("/create", summary='创建职位')
async def create_position(
    position_data: PositionCreateSchema,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_instance),
):
    async with session.begin():
        pass