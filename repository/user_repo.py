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