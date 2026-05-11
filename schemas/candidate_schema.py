from pydantic import BaseModel, Field
from datetime import datetime

class ResumeSchema(BaseModel):
    id: str = Field(..., description="简历ID")
    file_path: str = Field(..., description="简历文件路径")
    uploader: str = Field(..., description="上传者ID")


class ResumeUploadRespSchema(BaseModel):
    resume: ResumeSchema | None = Field(..., description="简历")
