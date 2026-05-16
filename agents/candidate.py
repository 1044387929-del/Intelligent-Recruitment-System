from schemas.candidate_schema import CandidateSchema
from schemas.position_schema import PositionSchema
from schemas.user_schema import UserSchema
from langgraph.graph.message import BaseMessage
from langchain.agents import create_agent
from .llms import qwen_llm, deepseek_llm
from typing import List, Annotated, TypeVar, Optional
from schemas.agent_schema import AgentCandidateSchema
from langchain.agents.middleware import ModelFallbackMiddleware, SummarizationMiddleware
from .prompts import CANDIDATE_PROCESS_SYSTEM_PROMPT, SCORE_FOR_CANDIDATE_SYSTEM_PROMPT, SCORE_FOR_CANDIDATE_USER_PROMPT
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from settings import settings
from pydantic import BaseModel
from langgraph.graph.message import add_messages
from langchain.tools import tool, ToolRuntime
from schemas.agent_schema import AgentCandidateScoreSchema
from langchain_core.prompts import PromptTemplate
from models import AsyncSessionFactory
from repository.candidate_repo import CandidateAIScoreRepo, CandidateRepo
from models.candidate import CandidateStatusEnum

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

@tool
async def score_for_candidate(
    runtime: ToolRuntime[CandidateAgentState],
):
    """
    根据候选人信息和职位需求，对候选人进行评分
    """
    candidate: CandidateSchema = runtime.state['candidate']
    position: PositionSchema = runtime.state['position']

    score_agent = create_agent(
        model=qwen_llm,
        system_prompt=SCORE_FOR_CANDIDATE_SYSTEM_PROMPT,
        middleware=[
            ModelFallbackMiddleware(first_model=deepseek_llm),
        ],
        response_format=AgentCandidateScoreSchema
    )
    user_prompt_template = PromptTemplate.from_template(SCORE_FOR_CANDIDATE_USER_PROMPT)
    user_prompt = user_prompt_template.invoke(
        {
            "candidate": candidate.model_dump_json(),
            "position": position.model_dump_json(),
        }
    )

    response = await score_agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ]
        }
    )

    candidate_score: AgentCandidateScoreSchema = response['structured_response']
    # 将得分情况保存到数据库
    async with AsyncSessionFactory() as session:
        async with session.begin():
            try:
                score_repo = CandidateAIScoreRepo(session)
                candidate_repo = CandidateRepo(session)
                # 1. 将得分情况保存到数据库
                await score_repo.create_candidate_score(
                    candidate_id=candidate.id, 
                    candidate_score_dict=candidate_score.model_dump()
                )

                # 2. 判断得分情况，如果超过8分，则更新候选人状态为待面试
                status = CandidateStatusEnum.AI_FILTER_FAILED
                if candidate_score.overall_score > 8:
                    status = CandidateStatusEnum.AI_FILTER_PASSED
                await candidate_repo.update_candidate_status(
                    candidate_id=candidate.id,
                    status=status
                )
            except Exception as e:
                return f"得分工具执行失败，错误信息为：{e}"
            
    return f"得分工具执行成功！该候选人的AI筛选结果为：{candidate_score.model_dump_json()}"

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
            tools = [score_for_candidate],
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