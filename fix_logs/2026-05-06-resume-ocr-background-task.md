# Fix: 简历解析后台任务 Redis / 缓存 API / 文件路径

**日期**: 2026-05-06  
**范围**: `POST /candidate/resume/parse` 触发的 `ocr_parse_resume_task` 后台任务

## 现象

- Postman 对解析接口返回 **HTTP 200**（符合设计：主请求立即返回 `task_id`，OCR 在 `BackgroundTasks` 中执行）。
- 服务端日志出现 **`ERROR: Exception in ASGI application`**，后台任务失败。
- 典型错误包括：
  - `redis.exceptions.ConnectionError: ... 10061`（本机未启动 Redis）。
  - `ValueError: ... pdf不存在！`（磁盘路径与库中 `file_path` 组合错误）。
  - `TypeError: HRCache.set_task_info() got an unexpected keyword argument 'task_id'`（调用方式与 `TaskInfoSchema` 不一致）。

## 根因

1. **`set_task_info` 调用错误**  
   `HRCache.set_task_info` 仅接受单个参数 `task_info: TaskInfoSchema`。成功/失败分支误用 `task_id=`、`status=`、`error=` 关键字参数；且模型字段为 **`error_message`**，不存在 `error`。

2. **简历文件路径**  
   上传时入库的 `file_path` 常为 **绝对路径**。任务中再使用 `os.path.join(settings.RESUME_DIR, resume.file_path)`，在部分历史数据或路径形态下会得到错误路径。应优先使用 **仍存在的绝对路径**，否则使用 **`RESUME_DIR` + `basename(stored)`** 兜底。

3. **缺少简历记录保护**  
   `resume_id` 无效时 `resume` 可能为 `None`，直接访问 `resume.file_path` 会抛异常。

## 改动

| 文件 | 说明 |
|------|------|
| `tasks/__init__.py` | 空简历提前返回；解析磁盘路径；`set_task_info` 统一传入 `TaskInfoSchema`；失败写缓存再包一层 try/except 打日志；移除未使用 import。 |

## 验证建议

1. 启动 **Redis**（与 `settings` 中 host/port 一致）。
2. 先 **`POST /candidate/resume/upload`** 上传真实文件，再 **`POST /candidate/resume/parse`** 使用返回的 `resume.id`。
3. **`GET /candidate/resume/parse/{task_id}`** 应能读到 `pending` → `done` 或 `failed`（含 `error_message`）。

## 后续待办（未在本次修改）

- `core/cache.py` 中任务键当前经 `set()` 仍会带上 `invite:` 前缀，语义上可拆分为独立前缀（可选重构）。
- 上传入库可统一只存 **相对文件名**，进一步避免路径歧义（需数据迁移或兼容读写）。
