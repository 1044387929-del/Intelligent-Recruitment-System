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
from models.interview import InterviewResultEnum
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
from repository.review_repo import InterviewRepo

# ========== 项目内部 - Core ==========
from core.dingtalk import DingTalkHttp
from core.cache import HRCache
from core.email_bot import EmailBot, EmailBotSettings

# ========== 项目内部 - Utils ==========
from utils.available_time import find_available_slot
from utils.iso8601 import iso8601_to_datetime_beijing, datetime_to_iso8601_beijing

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
    :param runtime: 运行时状态
    :return: 评分结果
    """
    candidate: CandidateSchema = runtime.state['candidate']
    position: PositionSchema = runtime.state['position']
    # 1. 创建评分agent
    score_agent = create_agent(
        model=qwen_llm,
        system_prompt=SCORE_FOR_CANDIDATE_SYSTEM_PROMPT,
        middleware=[
            ModelFallbackMiddleware(first_model=deepseek_llm),
        ],
        response_format=AgentCandidateScoreSchema
    )
    # 2. 创建用户提示模板
    user_prompt_template = PromptTemplate.from_template(SCORE_FOR_CANDIDATE_USER_PROMPT)
    user_prompt = user_prompt_template.invoke(
        {
            "candidate": candidate.model_dump_json(),
            "position": position.model_dump_json(),
        }
    )
    # 3. 调用评分agent
    response = await score_agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": user_prompt.text,
                }
            ]
        }
    )

    # 4. 获取评分结果
    candidate_score: AgentCandidateScoreSchema = response['structured_response']
    # 5. 将评分结果保存到数据库
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
                raise ValueError(f"得分工具执行失败，错误信息为：{e}")
                # return f"得分工具执行失败，错误信息为：{e}"
            
    return f"得分工具执行成功！该候选人的AI筛选结果为：{candidate_score.model_dump_json()}"

@tool
async def get_interviewer_available_slot(
    runtime: ToolRuntime[CandidateAgentState],
):
    """
    获取面试官可用的面试时间
    :param runtime: 运行时状态
    :return: 面试官可用的面试时间
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
        available_times = [
            (datetime_to_iso8601_beijing(start), datetime_to_iso8601_beijing(end))
            for start, end in available_slots
        ]
        return f"获取候选人可用面试时间成功，可用时间为：{json.dumps(available_times)}"

    except Exception as e:
        logger.error(e)
        return f"获取候选人可用面试时间失败，错误信息为：{e}"

@tool
async def send_interview_email(
    interview_datetime_str: str,
    runtime: ToolRuntime[CandidateAgentState],
):
    """
    发送面试邀请邮件
    :param interview_datetime_str: 面试时间
    :param runtime: 运行时状态
    :return: 发送面试邀请邮件成功
    """
    candidate: CandidateSchema = runtime.state['candidate']
    position: PositionSchema = runtime.state['position']

    email_bot_settings = EmailBotSettings(
        imap_host=settings.EMAIL_BOT_IMAP_HOST,
        smtp_host=settings.EMAIL_BOT_SMTP_HOST,
        email=settings.EMAIL_BOT_EMAIL,
        password=settings.EMAIL_BOT_PASSWORD,
    )
    async with EmailBot(email_bot_settings) as bot:
        subject = "【HR招聘】候选人面试邀请"
        # interview_datetime = iso8601_to_datetime_beijing(interview_iso8601_datetime)
        # interview_datetime_str = interview_datetime.strftime(r"%Y年%m月%d日 %H:%M")
        body = f"""
尊敬的{candidate.name}，
您好，
感谢您投递我司的{position.title}职位。
我们初步确定了面试时间，请您确认是否方便。
面试时间: {interview_datetime_str}
请您确认是否方便，如果方便，请您回复“确认”。
如果不方便，请回复您方便的时间，我们将会重新安排面试时间。
谢谢！
        """
        try:
            await bot.send_email(
                to=candidate.email,
                subject=subject,
                text=body,
            )
        except Exception as e:
            logger.error(e)
            return f"发送面试邀请邮件失败，错误信息为：{e}"
        
        return f"给候选人发送面试邀请邮件成功！面试时间确定为：{interview_datetime_str}"

@tool
async def confirm_interview_time(
    interview_datetime_str: str,
    runtime: ToolRuntime[CandidateAgentState],
):
    """
    确认最终的面试时间，这个工具会做以下几件事情：
    * 通过邮件，发送最终的面试时间给候选人
    * 给面试官的钉钉船舰一个面试的日程安排
    * 在系统中创建一个面试预约记录
    * 在系统中修改候选人的状态为待面试
    :param interview_datetime_str: 面试时间，ISO8601字符串
    :param runtime: 运行时状态
    :return: 确认面试时间成功
    """
    position: PositionSchema = runtime.state['position']
    candidate: CandidateSchema = runtime.state['candidate']
    interviewer: UserSchema = runtime.state['interviewer']
    try:
        interview_datetime: datetime = iso8601_to_datetime_beijing(interview_datetime_str)
        # 由于后面存储数据库，不能带日期中带时区，所以需要将日期转换为北京时区
        if interview_datetime.tzinfo is not None:
            interview_datetime_without_tz=interview_datetime.astimezone(None).replace(tzinfo=None)
    except Exception as e:
        return f"面试时间格式错误，错误信息为：{e}"

    # 1. 发送最终确认面试的时间给候选人
    email_bot_settings = EmailBotSettings(
        imap_host=settings.EMAIL_BOT_IMAP_HOST,
        smtp_host=settings.EMAIL_BOT_SMTP_HOST,
        email=settings.EMAIL_BOT_EMAIL,
        password=settings.EMAIL_BOT_PASSWORD,
    )
    async with EmailBot(email_bot_settings) as bot:
        subject = "【HR招聘】候选人面试时间确定"
        body = f"""
尊敬的{candidate.name}，
面试时间已确定：
{interview_datetime_str}
请您准时参加面试。该邮件无需再回复。谢谢！
"""
        try:
            await bot.send_email(
                to=candidate.email,
                subject=subject,
                text=body,
            )
        except Exception as e:
            logger.error(e)
            return f"发送面试邀请邮件失败，错误信息为：{e}"
    
    # 2. 给面试官的钉钉船舰一个面试的日程安排
    union_id: str | None = None
    try:
        async with AsyncSessionFactory() as session:
            async with session.begin():
                user_repo = UserRepo(session)
                dingding_user = await user_repo.get_dingding_user(user_id=interviewer.id)
                if not dingding_user:
                    return "面试官没有绑定钉钉账号！无法给面试官的钉钉船舰一个面试的日程安排"
                union_id = dingding_user.union_id
    except Exception as e:
        return f"面试官的用户信息获取失败，错误信息为：{e}"

    try:
        access_token: str = await get_dingtalk_access_token(interviewer.id)
    except Exception as e:
        return f"获取面试官的钉钉access_token失败，错误信息为：{e}"
    
    try:
        dingtalk_http = DingTalkHttp()
        # start_datetime: datetime = iso8601_to_datetime_beijing(interview_datetime_str)
        end_datetime: datetime = interview_datetime + timedelta(hours=1)
        await dingtalk_http.create_calendar(
            union_id=union_id,
            access_token=access_token,
            summary=f"面试安排：{candidate.name} - {position.title}",
            start_datetime=interview_datetime,
            end_datetime=end_datetime,
        )
    except Exception as e:
        return f"给面试官的钉钉船舰一个面试的日程安排失败，错误信息为：{e}"
    
    try:
        async with AsyncSessionFactory() as session:
            async with session.begin():
                # 3. 在数据库当中创建一个面试预约记录
                interview_repo = InterviewRepo(session)
                await interview_repo.create_interview(
                    interview_dict={
                        "scheduled_time": interview_datetime_without_tz,
                        "result": InterviewResultEnum.PENDING,
                        "candidate_id": candidate.id,
                        "interviewer_id": interviewer.id,
                    }
                )
                # 4. 在数据库中修改候选人的状态为待面试
                candidate_repo = CandidateRepo(session)
                await candidate_repo.update_candidate_status(
                    candidate_id=candidate.id,
                    status=CandidateStatusEnum.WAITING_FOR_INTERVIEW,
                )
    except Exception as e:
        return f"在数据库当中创建一个面试预约记录失败，错误信息为：{e}"
        
    return f"""
    * 给候选人发送面试时间执行成功！
    * 给面试官创建钉钉日程安排成功！
    * 在系统中创建面试预约成功！
    * 在系统中修改面试候选人状态为待面试成功
    """

@tool
async def reject_interview(
    runtime: ToolRuntime[CandidateAgentState],
):
    """
    拒绝面试，这个工具会做以下几件事情：
    * 通过邮件，发送拒绝面试的邮件给候选人
    * 在系统中修改候选人的状态为已拒绝
    :param runtime: 运行时状态
    :return: 拒绝面试成功
    """
    candidate: CandidateSchema = runtime.state['candidate']
    # position: PositionSchema = runtime.state['position']
    try:
        async with AsyncSessionFactory() as session:
            async with session.begin():
                candidate_repo = CandidateRepo(session)
                await candidate_repo.update_candidate_status(
                    candidate_id=candidate.id,
                    status=CandidateStatusEnum.REFUSED_INTERVIEW,
                )
        return f"已经将候选人的状态修改为已拒绝！"
    except Exception as e:
        return f"在系统中修改候选人的状态为已拒绝失败，错误信息为：{e}"

@tool
async def get_current_time(
    runtime: ToolRuntime[CandidateAgentState],
):
    """
    获取当前时间，返回格式为：2026年5月16日 10:00:00 星期一（本月第16天）
    :param runtime: 运行时状态
    :return: 当前时间
    """
    now_bj = datetime.now()

    weekday_map = {
        0: "星期一",
        1: "星期二",
        2: "星期三",
        3: "星期四",
        4: "星期五",
        5: "星期六",
        6: "星期日",
    }

    weekday_cn = weekday_map.get(now_bj.weekday(), "星期日")

    day_of_month = now_bj.day
    return (
        f"{now_bj.year}年{now_bj.month}月{now_bj.day}日"
        f"{now_bj.hour:02d}:{now_bj.minute:02d}:{now_bj.second:02d}"
        f"{weekday_cn}（本月第{day_of_month}天）"
    )

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
            state_schema=CandidateAgentState,
            system_prompt=CANDIDATE_PROCESS_SYSTEM_PROMPT,
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
            tools = [
                score_for_candidate, 
                get_interviewer_available_slot, 
                send_interview_email,
                confirm_interview_time,
                reject_interview,
                get_current_time,
                ],
            # 使用postgres作为检查点
            checkpointer=self.checkpointer
        )
        response = await agent.ainvoke(
            {
                "messages": messages,
                "candidate": self.candidate,
                "position": self.position,
                "interviewer": self.interviewer,
            },
            {"configurable": {"thread_id": thread_id}},
        )
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