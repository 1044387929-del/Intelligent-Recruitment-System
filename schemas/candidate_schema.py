from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from core.cache import TaskInfoSchema
from models.candidate import GenderEnum
from .position_schema import PositionSchema
from .user_schema import UserSchema

class ResumeSchema(BaseModel):
    id: str = Field(..., description="简历ID")
    file_path: str = Field(..., description="简历文件路径")
    uploader: str = Field(..., description="上传者ID", validation_alias="uploader_id")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ResumeUploadRespSchema(BaseModel):
    resume: ResumeSchema | None = Field(..., description="简历")

class ResumeParseSchema(BaseModel):
    resume_id: str = Field(..., description="简历ID")
    # task_id: str = Field(..., description="任务ID")

class ResumeParseRespSchema(BaseModel):
    task_id: str = Field(..., description="任务ID")

class ResumeParseTaskInfoRespSchema(TaskInfoSchema):
    pass

class CandidateCreateSchema(BaseModel):
    name: str | None = Field(..., description="姓名")
    email: str | None = Field(..., description="候选人邮箱")
    gender: GenderEnum | None = Field(GenderEnum.UNKNOWN, description="性别")
    birthday: str | None = Field(None, description="候选人出生日期，如果只有年份，则只填写年份")
    phone_number: str | None = Field(None, description="候选人手机号")
    work_experience: str | None = Field(None, description="候选人工作经历")
    project_experience: str | None = Field(None, description="候选人项目经历")
    education_experience: str | None = Field(None, description="候选人教育经历")
    self_evaluation: str | None = Field(None, description="候选人自我评价")
    other_information: str | None = Field(None, description="其他信息")
    skills: str | None = Field(None, description="候选人技能")
    position_id: str = Field(..., description="候选人投递的职位ID")
    resume_id: str = Field(..., description="候选人简历ID")

class CandidateSchema(BaseModel):
    id: str = Field(..., description="候选人ID")
    name: str = Field(..., description="候选人姓名")
    email: str = Field(..., description="候选人邮箱")
    gender: GenderEnum = Field(GenderEnum.UNKNOWN, description="候选人性别")
    birthday: str | None = Field(None, description="候选人出生日期")
    phone_number: str | None = Field(None, description="候选人手机号")
    work_experience: str | None = Field(None, description="候选人工作经历")
    project_experience: str | None = Field(None, description="候选人项目经历")
    education_experience: str | None = Field(None, description="候选人教育经历")
    self_evaluation: str | None = Field(None, description="候选人自我评价")
    other_information: str | None = Field(None, description="其他信息")
    skills: str | None = Field(None, description="候选人技能")
    position: PositionSchema = Field(..., description="候选人投递的职位")
    resume: ResumeSchema = Field(..., description="候选人简历")
    creator: UserSchema = Field(..., description="创建者")
    
    model_config = ConfigDict(from_attributes=True)