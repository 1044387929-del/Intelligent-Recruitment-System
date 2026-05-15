"""
任务模块，用于处理各种任务，比如发送邮件、解析简历等
发送邮件任务：send_email_task
注册邀请邮件任务：send_invite_email_task
解析简历任务：ocr_parse_resume_task
"""
from fastapi_mail import FastMail, MessageSchema
from aiosmtplib import SMTPResponseException
from loguru import logger
from core.mail import create_mail_instance
from models import AsyncSessionFactory
from repository.candidate_repo import ReusmeRepo
from models.candidate import ResumeModel
import os
from settings import settings
from core.ocr import PaddleOcr
from core.cache import HRCache, TaskInfoSchema

async def send_email_task(message: MessageSchema):
    """
    发送邮件任务
    Args:
        message: 邮件消息
    Returns:
        None
    """
    mail: FastMail = create_mail_instance()
    try:
        await mail.send_message(message)
    except SMTPResponseException as e:
        if e.code == -1 and b'\\x00\\x00\\x00' in str(e).encode():
            logger.info("⚠️ 忽略 QQ 邮箱 SMTP 关闭阶段的非标准响应（邮件已成功发送）", enqueue=True)
        else:
            logger.error(f"邮件发送失败！{e}")

async def send_invite_email_task(email: str, invite_code: str):
    message = MessageSchema(
        subject="注册邀请",
        recipients=[email],
        body=f"您好，您的邮箱是：{email}，验证码是：{invite_code}，一天内有效。",
        subtype="plain"
    )
    await send_email_task(message)

async def ocr_parse_resume_task(
    resume_id: str,
    task_id: str,
):
    """
    解析简历任务
    Args:
        resume_id: 简历ID
        task_id: 任务ID
    Returns:
        None
    """
    async with AsyncSessionFactory() as session:
        async with session.begin():
            resume_repo = ReusmeRepo(session=session)
            resume: ResumeModel | None = await resume_repo.get_resume_by_id(resume_id)

    if not resume:
        logger.warning("ocr_parse_resume_task: resume_id={} 不存在，跳过", resume_id)
        return

    # 上传时可能写入绝对路径；若路径失效则用 RESUME_DIR + 文件名兜底
    stored = resume.file_path
    if os.path.isfile(stored):
        file_path = stored
    else:
        file_path = os.path.join(settings.RESUME_DIR, os.path.basename(stored))

    cache: HRCache = HRCache()
    await cache.set_task_info(TaskInfoSchema(task_id=task_id, status="pending"))
    try:
        paddle_ocr = PaddleOcr()
        job_id = await paddle_ocr.create_job(file_path)
        jsonl_url = await paddle_ocr.poll_for_state(job_id)
        contents = await paddle_ocr.fetch_parsed_contents(jsonl_url)
        content = "\n\n".join(contents)
        # TODO：将content丢给大模型，让大模型识别其中的内容，比如姓名，性别，年龄、技能、教育经历、工作经历、项目经历、自我评价、其他信息等
        
        result = {"content": content}
        await cache.set_task_info(
            TaskInfoSchema(task_id=task_id, status="done", result=result)
        )
    except Exception as e:
        try:
            await cache.set_task_info(
                TaskInfoSchema(
                    task_id=task_id,
                    status="failed",
                    error_message=str(e),
                )
            )
        except Exception:
            logger.exception("写入任务失败状态到缓存时出错")
        