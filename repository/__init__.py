# 基础仓库类
from sqlalchemy.ext.asyncio import AsyncSession

# 基础仓库类，所有仓库类都继承自这个类
class BaseRepo:
    def __init__(self, session: AsyncSession):
        self.session = session