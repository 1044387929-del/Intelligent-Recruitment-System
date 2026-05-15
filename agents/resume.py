from langchain.agents import create_agent
from .llms import qwen_llm, deepseek_llm
from langchain.agents.middleware import ModelFallbackMiddleware
from .prompts import EXTRACT_CANDIDATE_SYSTEM_PROMPT
from schemas.agent_schema import AgentCandidateSchema

agent = create_agent(
    model=qwen_llm,
    # 如果qwen_llm解析失败，则使用deepseek_llm解析
    middleware=[ModelFallbackMiddleware(deepseek_llm)],
    system_prompt=EXTRACT_CANDIDATE_SYSTEM_PROMPT,
    response_format=AgentCandidateSchema,
)

async def extract_candidate_info(content: str) -> AgentCandidateSchema:
    """
    解析简历内容，返回候选人信息
    """
    response = await agent.ainvoke({
        "messages": [
            {
                "role": "user",
                "content": f"原始文本内容为: {content}，请从原始文本中提取候选人信息。"
            }
        ],
    })

    return response.get("structured_response")