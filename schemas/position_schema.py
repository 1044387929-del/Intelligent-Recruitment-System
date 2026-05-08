from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from models.position import EducationEnum

class PositionCreateSchema(BaseModel):
    title: str = Field(..., description='职位名称')
    description: Optional[str] = Field(..., description='职位描述')
    requirements: str = Field(..., description='职位要求')
    min_salary: str = Field(..., description='最低薪资')
    max_salary: str = Field(..., description='最高薪资')
    deadline: Optional[datetime] = Field(..., description='截止日期')
    recruitment_count: int = Field(1, description='招聘人数')
    education: EducationEnum = Field(..., description='最低学历要求')
    work_year: int = Field(0, description='最低工作年限要求')
    # is_open: str = Field(True, description='是否开放')
    # department_id: str = Field(..., description='部门ID')