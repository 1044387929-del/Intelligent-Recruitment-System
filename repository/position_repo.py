from . import BaseRepo
from models import AsyncSession
from models.position import PositionModel
from sqlalchemy import select, delete
from typing import List
from models.user import UserModel
from fastapi import HTTPException, status

class PositionRepo(BaseRepo):
    async def create_position(self, position_data: dict) -> PositionModel:
        position = PositionModel(**position_data)
        self.session.add(position)
        return position
    
    async def get_position_list(self, 
        user: UserModel,
        page: int = 1, 
        size: int = 10) -> List[PositionModel]:
        """
        获取职位列表
        Args:
            user: 当前用户
            page: 页码
            size: 每页条数
        Returns:
            List[PositionModel]: 职位列表
        """
        # 如果用户是HR，则获取其管理的部门下的职位
        stmt = select(PositionModel)
        if user.is_hr and (not user.is_superuser):
            department_ids = [d.id for d in user.managed_departments]
            stmt = stmt.where(PositionModel.department_id.in_(department_ids))
        
        # 如果用户是普通用户，则获取其所在部门下的职位
        elif (not user.is_hr) and (not user.is_superuser):
            stmt = stmt.where(PositionModel.department_id == user.department_id)
        
        # 分页
        limit = size
        offset = (page - 1) * size
        # 等价于：stmt sql语句，
        # SELECT * FROM positions WHERE department_id IN (SELECT id FROM departments WHERE id IN (SELECT department_id FROM users WHERE id = ?)) ORDER BY created_at DESC LIMIT ? OFFSET ?
        stmt = stmt.limit(limit).offset(offset).order_by(PositionModel.created_at.desc())
        positions = (await self.session.scalars(stmt)).all()
        return positions

    async def get_position_by_id(self, position_id: str) -> PositionModel | None:
        stmt = select(PositionModel).where(PositionModel.id == position_id)
        position = await self.session.scalar(stmt)
        return position

    async def delete_position_by_id(
        self, 
        user: UserModel,
        position_id: str) -> None:
        """
        删除职位
        Args:
            user: 当前用户
            position_id: 职位ID
        """
        stmt = delete(PositionModel).where(PositionModel.id == position_id)
        await self.session.execute(stmt)

    