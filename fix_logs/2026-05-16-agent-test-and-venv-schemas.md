# Fix: 误改 fastapi_mail、Agent 语法错误、CandidateSchema 校验失败

**日期**: 2026-05-16  
**范围**: 应用启动、`GET /candidate/agent/test`、候选人 Agent 后台任务

## 现象

1. **Uvicorn 无法启动**
  `fastapi_mail/schemas.py` 报 `NameError: name 'mapped_column' is not defined`，堆栈指向 `.venv/Lib/site-packages/fastapi_mail/schemas.py` 中的 `PositionModel`。
2. **导入 agents 失败**（已自行修复）
  `agents/candidate.py` 报 `SyntaxError: keyword argument repeated: state_schema`。
3. `**GET /candidate/agent/test` 返回 500**
  `CandidateSchema.model_validate(candidate_model)` 失败：  
   `resume` 期望 `ResumeSchema`，实际传入 SQLAlchemy `ResumeModel`。
4. **后续隐患**（本次一并修复）
  `run_candidate_agent` 调用 `CandidateProcessAgent.ainvoke` 时参数签名不匹配（缺 `thread_id`，且把 state dict 当作第一个位置参数）。

## 根因


| 问题                 | 根因                                                                                                         |
| ------------------ | ---------------------------------------------------------------------------------------------------------- |
| fastapi_mail 崩溃    | 将项目里的 SQLAlchemy `PositionModel` 误粘贴进**第三方包** `fastapi_mail/schemas.py`。该文件应只有 Pydantic 邮件模型，不应含 ORM 代码。   |
| state_schema 重复    | `create_agent(...)` 中 `state_schema` 关键字参数写了两次。                                                            |
| CandidateSchema 校验 | 父模型虽有 `from_attributes=True`，嵌套的 `ResumeSchema` 未开启；且 ORM 字段为 `uploader_id`，Schema 字段名为 `uploader`，无法自动映射。 |
| Agent 任务调用         | `ainvoke(self, messages, thread_id)` 与 `create_agent` 返回的 `invoke(state, config)` 封装不一致，任务层误用 dict 单参数调用。  |


## 改动


| 文件                                  | 说明                                                                                                              |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `.venv/.../fastapi_mail/schemas.py` | **勿再修改**；若仍含 `PositionModel`，应恢复包原文件或 `pip install --force-reinstall fastapi-mail`。业务模型放在 `models/position.py`。 |
| `schemas/candidate_schema.py`       | `ResumeSchema` 增加 `from_attributes`、`validation_alias="uploader_id"`，支持从 `ResumeModel` 校验。                      |
| `tasks/__init__.py`                 | `run_candidate_agent` 使用 `HumanMessage` + `thread_id` 调用 `ainvoke`；移除未使用的 `PositionModel` 导入。                   |
| `agents/candidate.py`               | 删除重复的 `state_schema`（用户已在本地修复）。                                                                                 |


## 验证建议

1. 确认 `fastapi_mail/schemas.py` 末尾无 `PositionModel`，重启：`uvicorn main:app --reload`。
2. `GET /candidate/agent/test` 应返回 `{"result":"success"}`（HTTP 200）。
3. 查看日志，后台 `run_candidate_agent` 应能进入 Agent 流程（需 PostgreSQL agent 库与 LLM 配置可用）。

## 后续待办

- 上传接口 `resume_upload` 返回的仍是 ORM `resume` 对象，若前端需要 JSON，可改为 `ResumeSchema.model_validate(resume)` 与 `response_model` 对齐。
- 避免在 `.venv` 内直接改源码；ORM 与 Schema 分别维护在 `models/` 与 `schemas/`。

---

## 补充修复（同日后台任务连接失败）

**现象**：`GET /candidate/agent/test` 返回 200，但后台 `run_candidate_agent` 报错  
`psycopg.ProgrammingError: missing "=" after "postgresql+psycopg://..."`。

**根因**：`DATABASE_AGENT_URL` 使用了 SQLAlchemy 驱动前缀 `postgresql+psycopg://`，`AsyncPostgresSaver` 底层 psycopg 无法解析。

**改动**：`settings/__init__.py` 中 `DATABASE_AGENT_URL` 改为 `postgresql://...`（`DATABASE_URL` 仍为 SQLAlchemy 格式不变）。

**现象（续）**：连接串修复后报  
`InvalidStateError: Synchronous calls to AsyncPostgresSaver are only allowed from a different thread`。

**根因**：`CandidateProcessAgent.ainvoke` 内对 graph 调用了同步 `agent.invoke()`，与 `AsyncPostgresSaver` 不兼容。

**改动**：`agents/candidate.py` 改为 `await agent.ainvoke(..., {"configurable": {"thread_id": thread_id}})`。

**现象（续）**：Agent 已跑起来，调用 `score_for_candidate` 时 `KeyError: 'position'`。

**根因**：`CandidateAgentState` 要求 `candidate` / `position` / `interviewer` 三项，但 `ainvoke` 初始 state 只传了 `candidate`；职位信息仅在用户消息文本里，未写入 graph state，工具从 `runtime.state['position']` 读取失败。

**改动**：`CandidateProcessAgent.ainvoke` 初始 state 同时传入 `position`、`interviewer`。

