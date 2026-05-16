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

class AgentCandidateScoreSchema(BaseModel):
    """
    AI评分结果
    """
    # 工作经历评分，1-10分
    work_experience_score: int = Field(..., description="工作经历评分",ge=1, le=10)
    technical_skills_score: int = Field(..., description="技术技能评分",ge=1, le=10)
    soft_skills_score: int = Field(..., description="软技能评分",ge=1, le=10)
    educational_background_score: int = Field(..., description="教育背景评分",ge=1, le=10)
    project_experience_score: int = Field(..., description="项目经验评分",ge=1, le=10)
    overall_score: int = Field(..., description="总评分",ge=1, le=10)
    summary: str = Field(..., description="总结")
    strengths: list[str] = Field(..., description="优势")
    weaknesses: list[str] = Field(..., description="劣势")