from pydantic import BaseModel, Field
from typing import Literal, Optional

from sqlalchemy import desc

class ResponseSchema(BaseModel):
    result: Literal['success', 'fail'] = Field('success', description='响应消息')
    