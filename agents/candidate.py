# ========== 标准库 & 第三方 ==========
from datetime import datetime, timedelta
import json
from typing import List, Annotated, Tuple, TypeVar, Optional, Any

from pydantic import BaseModel
from loguru import logger

# ========== LangChain & LangGraph ==========
from langgraph.graph.message import BaseMessage, add_messages
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain.agents import create_agent
from langchain.agents.middleware import ModelFallbackMiddleware, SummarizationMiddleware
from langchain.tools import tool, ToolRuntime
from langchain_core.prompts import PromptTemplate

# ========== 项目内部 - Settings & Prompts ==========
from settings import settings
from .prompts import (
    CANDIDATE_PROCESS_SYSTEM_PROMPT, 
    SCORE_FOR_CANDIDATE_SYSTEM_PROMPT, 
    SCORE_FOR_CANDIDATE_USER_PROMPT,
)

# ========== 项目内部 - LLM ==========
from .llms import qwen_llm, deepseek_llm

# ========== 项目内部 - Schemas ==========
from schemas.candidate_schema import CandidateSchema
from schemas.position_schema import PositionSchema
from schemas.user_schema import UserSchema
from schemas.agent_schema import AgentCandidateSchema, AgentCandidateScoreSchema
from schemas.cache_schema import DingTalkTokenInfoSchema

# ========== 项目内部 - Models ==========
from models import AsyncSessionFactory
from models.user import DingdingUserModel
from models.candidate import CandidateStatusEnum

# ========== 项目内部 - Repositories ==========
from repository.user_repo import UserRepo
from repository.candidate_repo import CandidateAIScoreRepo, CandidateRepo

# ========== 项目内部 - Core ==========
from core.dingtalk import DingTalkHttp
from core.cache import HRCache

# ========== 项目内部 - Utils ==========
from utils.available_time import find_available_slot
from utils.iso8601 import iso8601_to_datetime_beijing

async def get_dingtalk_access_token(user_id: str) -> str:
    dingding_http = DingTalkHttp()

    # 2. 从缓存中获取该用户的refresh_token
    cache: HRCache = HRCache()
    token_info = await cache.get_dingtalk_info(user_id)
    if not token_info:
        error_message = f"{user_id}用户钉钉授权已过期！"
        logger.error(error_message)
        raise ValueError(error_message)

    try:
        # 3. 根据refresh_token刷新access_token
        refresh_token, access_token = await dingding_http.refresh_access_token(token_info.refresh_token)

        # 4. 将获取到的token信息重新设置到缓存中
        await cache.set_dingtalk_info(
            DingTalkTokenInfoSchema(
                user_id=user_id,
                access_token=access_token,
                refresh_token=refresh_token
            )
        )

        return access_token
    except Exception as e:
        logger.error(e)
        raise ValueError(e)


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
    Args:
        candidate: 候选人
        position: 职位
    Returns:
        str: 评分结果
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

@tool
async def get_interviewer_available_slot(
    runtime: ToolRuntime[CandidateAgentState],
):
    """
    获取面试官可用的面试时间
    Args:
        interviewer: 面试官
    Returns:
        str: 面试官可用的面试时间
    """
    interviewer: UserSchema = runtime.state['interviewer']
    # 1. 获取该用户的钉钉账号
    union_id: str | None = None
    async with AsyncSessionFactory() as session:
        async with session.begin():
            try:
                user_repo = UserRepo(session)
                dingding_user: DingdingUserModel | None = await user_repo.get_dingding_user(
                    user_id=interviewer.id
                )
                if not dingding_user:
                    return f"获取候选人可用面试时间失败，没有绑定钉钉账号"
                union_id = dingding_user.union_id
            except Exception as e:
                return f"获取候选人可用面试时间失败，错误信息为：{e}"
    # 2. 获取钉钉的access_token
    try:
        access_token = await get_dingtalk_access_token(interviewer.id)
    except Exception as e:
        logger.error(e)
        return f"获取候选人可用面试时间失败，错误信息为：{e}"

    # 3. 获取面试官的日程安排，从钉钉的日历中获取
    try:
        dingtalk_http = DingTalkHttp()
        now = datetime.now()
        tomorrow_nine = datetime(year=now.year, month=now.month, day=now.day + 1, hour=9, minute=0, second=0)
        events: list[dict[str, Any]] = await dingtalk_http.get_calendar_list(
            access_token=access_token, 
            union_id=union_id,
            time_min=tomorrow_nine,
            time_max=tomorrow_nine + timedelta(hours=7),
        )
        busy_slots = [
            (iso8601_to_datetime_beijing(event['start']['dateTime']), 
            iso8601_to_datetime_beijing(event['end']['dateTime']))
            for event in events
            ]
        available_slots: List[Tuple[datetime, datetime]] = find_available_slot(
            busy_slots,
            start_date=tomorrow_nine,
            )
        if len(available_slots) == 0:
            return f"获取候选人可用面试时间失败，没有可用的时间"
        available_times = [(iso8601_to_datetime_beijing(slot[0]), iso8601_to_datetime_beijing(slot[1])) 
        for slot in available_slots]
        return f"获取候选人可用面试时间成功，可用时间为：{json.dumps(available_times)}"

    except Exception as e:
        logger.error(e)
        return f"获取候选人可用面试时间失败，错误信息为：{e}"

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
            tools = [score_for_candidate, get_interviewer_available_slot],
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