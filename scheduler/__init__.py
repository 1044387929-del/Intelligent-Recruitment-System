from apscheduler.schedulers.asyncio import AsyncIOScheduler
from agents.candidate import CandidateProcessAgent
from core.cache import HRCache
from core.email_bot import EmailBot, EmailBotSettings
from settings import settings
from loguru import logger
from agents.candidate import CandidateAgentState
from langchain_core.messages import HumanMessage

scheduler = AsyncIOScheduler()

async def poll_and_process_emails(bot: EmailBot, state: dict):
    try:
        last_uid = state.get("last_uid")
        if last_uid is None:
            last_uid = await bot.get_max_uid() or 0
        state["last_uid"] = last_uid
        logger.info(f"Initialized last_uid: {last_uid}")
        new_emails = await bot.fetch_since_uid(last_uid)
        if not new_emails:
            return
        new_emails.sort(key=lambda e: int(e.uid))

        async with CandidateProcessAgent() as agent:
            for mail in new_emails:
                # 如果邮件发件人是邮箱账号，则跳过
                if mail.from_.address.lower() == bot.settings.email.lower():
                    continue
            thread_id = mail.from_.address
            response = await agent.ainvoke(
                messages=[
                    HumanMessage(content=f"收到邮件内容：{mail.text or mail.html}")
                ],
                thread_id=thread_id
            )
            logger.info(f"Processed email from {thread_id}: response: {response}")
            # 更新 last_uid，确保下次轮询不会重复处理已处理过的邮件
            state["last_uid"] = max(state["last_uid"], int(mail.uid))
            cache = HRCache()
            await cache.set_email_last_uid(state["last_uid"])
        logger.info(f"Processed {len(new_emails)} new emails, last_uid now {state['last_uid']}")
    
    except Exception as e:
        logger.error(f"Error processing emails: {e}")
        raise e

async def start_email_polling():
    """
    启动邮件轮询
    """
    email_settings = EmailBotSettings(
        imap_host=settings.EMAIL_BOT_IMAP_HOST,
        smtp_host=settings.EMAIL_BOT_SMTP_HOST,
        email=settings.EMAIL_BOT_EMAIL,
        password=settings.EMAIL_BOT_PASSWORD
    )
    cache = HRCache()
    last_uid = await cache.get_email_last_uid()
    state: dict = {"last_uid": last_uid}
    bot = EmailBot(email_settings)
    await bot.connect()

    # 添加定时任务，每15秒轮询一次
    scheduler.add_job(
        poll_and_process_emails,
        "interval",
        seconds=15,
        args=[bot, state],
        max_instances=1,
    )

    scheduler.start()
    logger.info("Scheduler started, polling inbox...")
    return bot, scheduler