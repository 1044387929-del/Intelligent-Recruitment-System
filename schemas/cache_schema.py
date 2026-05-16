from pydantic import BaseModel, EmailStr, Field
from typing import Literal
from schemas.agent_schema import AgentCandidateSchema

class InviteInfoSchema(BaseModel):
    """
    邀请信息
    """
    email: EmailStr
    department_id: str
    invite_code: str

class DingTalkTokenInfoSchema(BaseModel):
    """
    钉钉token信息
    """
    access_token: str
    refresh_token: str
    user_id: str

class TaskInfoSchema(BaseModel):
    """
    任务信息
    """
    task_id: str
    status: Literal["pending", "done", "failed"]
    result: AgentCandidateSchema | None = None
    error_message: str | None = None
    task_prefix: str = 'task:'

