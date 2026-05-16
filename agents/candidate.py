from schemas.candidate_schema import CandidateSchema
from schemas.position_schema import PositionSchema
from schemas.user_schema import UserSchema
from langgraph.graph.message import BaseMessage
from langchain.agents import create_agent
from .llms import qwen_llm, deepseek_llm
from typing import List, Annotated, TypeVar, Optional
from schemas.agent_schema import AgentCandidateSchema
from langchain.agents.middleware import ModelFallbackMiddleware, SummarizationMiddleware
from .prompts import CANDIDATE_PROCESS_SYSTEM_PROMPT
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from settings import settings
from pydantic import BaseModel
from langgraph.graph.message import add_messages

T = TypeVar("T")
def assign_state_property(left: T, right: Optional[T]) -> T:
    """
    如果right不为None，则返回right，否则返回left
    """
    return right if right is not None else left

class CandidateAgentState(BaseModel):
    messages: Annotated[List[BaseMessage], add_messages]
    candidate: Annotated[CandidateSchema, assign_state_property]
    position: Annotated[PositionSchema, assign_state_property]
    interviewer: Annotated[UserSchema, assign_state_property]

class CandidateProcessAgent:
    def __init__(self, 
        candidate: CandidateSchema | None = None,
        position: PositionSchema | None = None,
        interviewer: UserSchema | None = None,
    ):
        self.candidate = candidate
        self.position = position
        self.interviewer = interviewer
        self._checkpointer = None

    async def ainvoke(self,
        messages: List[BaseMessage],
        thread_id: str,
    ):
        assert self.checkpointer is not None, "检查点未初始化"
        agent = create_agent(
            model=qwen_llm,
            state_schema=AgentCandidateSchema,
            system_prompt=CANDIDATE_PROCESS_SYSTEM_PROMPT,
            state_schema=CandidateAgentState,
            middleware=[
                ModelFallbackMiddleware(
                    first_model=deepseek_llm,
                ),
                # 如果生成的内容超过50000个token，则进行摘要，保留10000个token
                SummarizationMiddleware(
                    model=deepseek_llm,
                    trigger=("tokens", 50000),
                    keep=("tokens", 10000)
                )
            ],
            tools = [],
            # 使用postgres作为检查点
            checkpointer=self.checkpointer
        )
        response = await agent.invoke({
            "messages": messages,
            "candidate": self.candidate,
        }, 
        {
            "thread_id": thread_id,
        })
        return response

    async def __aenter__(self):
        """
        进入上下文管理器
        """
        self._checkpointer_conn = AsyncPostgresSaver.from_conn_string(settings.DATABASE_AGENT_URL)
        self.checkpointer = await self._checkpointer_conn.__aenter__()
        await self.checkpointer.setup()
        return self
    
    async def __aexit__(self, exc_type, exc_value, exc_tb):
        """
        退出上下文管理器
        """
        await self._checkpointer_conn.__aexit__(exc_type, exc_value, exc_tb)

# async with CandidateProcessAgent(candidate, position, interviewer) as agent:
#     pass