from pydantic import BaseModel, Field, ConfigDict
from models.candidate import GenderEnum

class AgentCandidateSchema(BaseModel):
    name: str | None = Field(None, description="候选人的姓名")
    gender: GenderEnum = Field(GenderEnum.UNKNOWN, description="候选人的性别")
    birthday: str | None = Field(None, description="候选人的生日")
    email: str | None = Field(None, description="候选人的邮箱")
    phone_number: str | None = Field(None, description="候选人的手机号")
    work_experience: str | None = Field(None, description="候选人的工作经历")
    project_experience: str | None = Field(None, description="候选人的项目经历")
    education_experience: str | None = Field(None, description="候选人的教育经历")
    self_evaluation: str | None = Field(None, description="候选人的自我评价")
    other_information: str | None = Field(None, description="候选人的其他信息")
    skills: str | None = Field(None, description="候选人的技能") 

    model_config = ConfigDict(from_attributes=True)

