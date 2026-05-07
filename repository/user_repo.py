# 用户仓库（Repo）层：封装了对UserModel及相关模型（如DepartmentModel、
# DingdingUserModel）的数据库操作，包括用户的增、查、列表、
# 与钉钉用户等信息的管理，供上层服务或路由调用。

from multiprocessing import Value
from sqlalchemy import select, exists
from . import BaseRepo
from sqlalchemy.orm import selectinload
from models.user import UserModel, DepartmentModel, DingdingUserModel
from typing import List, Sequence

class UserRepo(BaseRepo):
    async def create_user(self, user_data: dict) -> UserModel:
        user = UserModel(**user_data)
        self.session.add(user)
        return user
    
    async def get_by_id(self, user_id: str) -> UserModel | None:
        user = await self.session.scalar(select(UserModel).where(UserModel.id==user_id))
        return user
    
    async def get_by_email(self, email: str) -> UserModel | None:
        user = await self.session.scalar(select(UserModel).where(UserModel.email==email))
        return user
    
    async def get_user_list(
        self,
        page: int = 1,
        size: int = 10,
        department_id: str|None = None
    ) -> Sequence[UserModel] | None:
        # 
        stmt = select(UserModel)
        if department_id:
            stmt = stmt.where(UserModel.department_id == department_id)
        offset = (page - 1) * size
        stmt = stmt.offset(offset).limit(size)
        users = await self.session.scalars(stmt)
        return users.all()
    
    async def set_dingding_user(
        self,
        user_id: str,
        dingding_user_data: dict
    ) -> DingdingUserModel:
        stmt = select(UserModel).where(UserModel.id == user_id).options(selectinload(UserModel.dingding_user))
        user: UserModel = await self.session.scalar(stmt)
        if not user:
            raise ValueError("设置钉钉的用户不存在")
        
        if user.dingding_user:
            for key, value in dingding_user_data.items():
                setattr(user.dingding_user, key, value)
            dingding_user = user.dingding_user
        else:
            dingding_user = DingdingUserModel(**dingding_user_data)
            dingding_user.user_id = user_id
            self.session.add(dingding_user)
        return dingding_user
    
    async def get_dingding_user(self, user_id: str) -> DingdingUserModel | None:
        stmt = select(DingdingUserModel).where(DingdingUserModel.user_id == user_id)
        dingding_user = await self.session.scalar(stmt)
        return dingding_user



class DepartmentRepo(BaseRepo):
    async def create_department(self, department_data: dict) -> DepartmentModel:
        department = DepartmentModel(**department_data)
        self.session.add(department)
        return department
    
    async def get_by_id(self, department_id: str) -> DepartmentModel | None:
        department = await self.session.scalar(
            select(DepartmentModel).where(DepartmentModel.id==department_id)
        )
        return department
    
    async def get_by_name(self, name: str) -> DepartmentModel | None:
        department = await self.session.scalar(
            select(DepartmentModel).where(DepartmentModel.name==name)
        )
        return department
    
    async def delete_department(self, department_id: str):
        return await self.session.delete(DepartmentModel(id=department_id))

    async def get_department_list(self) -> List[DepartmentModel]:
        stmt = select(DepartmentModel)
        departments = await self.session.scalars(stmt)
        return departments.all()