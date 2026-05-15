from pydantic import BaseModel, Field
from datetime import datetime
from core.cache import TaskInfoSchema

class ResumeSchema(BaseModel):
    id: str = Field(..., description="简历ID")
    file_path: str = Field(..., description="简历文件路径")
    uploader: str = Field(..., description="上传者ID")


class ResumeUploadRespSchema(BaseModel):
    resume: ResumeSchema | None = Field(..., description="简历")

class ResumeParseSchema(BaseModel):
    resume_id: str = Field(..., description="简历ID")
    # task_id: str = Field(..., description="任务ID")

class ResumeParseRespSchema(BaseModel):
    task_id: str = Field(..., description="任务ID")

class ResumeParseTaskInfoRespSchema(TaskInfoSchema):
    pass