from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from dependencies import get_current_user, get_session_instance
from models import AsyncSession
from fastapi import UploadFile, File
from models.user import UserModel
from settings import settings, BASE_DIR
import os
from uuid import uuid4
import aiofiles
from core.pdf import WordToPdfConverter
from loguru import logger
from repository.candidate_repo import ReusmeRepo
from schemas.candidate_schema import ResumeParseSchema, ResumeUploadRespSchema, ResumeParseRespSchema
from core.ocr import PaddleOcr, QwenOcr
from tasks import ocr_parse_resume_task
from core.cache import HRCache
from dependencies import get_cache_instance

router = APIRouter(prefix='/candidate', tags=['candidate'])

@router.post("/resume/upload", summary='上传简历')
async def resume_upload(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session_instance),
    current_user: UserModel = Depends(get_current_user),
):
    """
    上传简历
    Args:
        file: 简历文件
        session: 数据库会话
        current_user: 当前用户
    Returns:
        ResponseSchema: 响应数据
    """
    # 检查文件类型
    # 简历：图片、pdf、word
    allowed_mine_types = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/jpeg",
        "image/png",
        "image/jpg",
    ]
    if file.content_type not in allowed_mine_types:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的文件类型")

    # 保存文件
    resume_dir = settings.RESUME_DIR
    file_extension = os.path.splitext(file.filename)[-1]
    unique_filename = f"{uuid4()}{file_extension}"
    file_path = os.path.join(resume_dir, unique_filename)
    # try:
    async with aiofiles.open(file_path, mode="wb") as fp:
        # 文件太大的话，内存可能会不够
        content = await file.read(1024)
        while content:
            await fp.write(content)
            content = await file.read(1024)
    # finally:
        # await fp.close()
    
    # 如果是word文档，那么就转化成pdf
    if file_extension == ".doc" or file_extension == ".docx":
        pdf_path = file_path.replace(file_extension, ".pdf")
        converter = WordToPdfConverter(
            word_path=file_path,
            output_pdf_path=pdf_path,
        )
        try:
            await converter.convert()
        except Exception as e:
            logger.error(f"转换失败: {e}")
    
    # 将简历数据存储到数据库中
    async with session.begin():
        resume_repo = ReusmeRepo(session=session)
        resume = await resume_repo.create_resume(file_path=file_path, uploader_id=current_user.id)
    return {"resume": resume}

# 发起了一个简历识别的请求，创建一个后台任务，把任务id返回给前端
# 前端就可以通过task_id来获取这个任务的执行结果
@router.post("/resume/parse", summary='解析简历', response_model=ResumeParseRespSchema)
async def parse_resume(
    resume_data: ResumeParseSchema,
    background_tasks: BackgroundTasks,
    _: UserModel = Depends(get_current_user),

):
    """
    解析简历
    Args:
        resume_data: 简历数据
        background_tasks: 后台任务
        _: 当前用户
    Returns:
        dict: 任务ID
    """
    # 创建一个识别简历的后台任务
    task_id = str(uuid4())
    # 将任务id返回给前端
    background_tasks.add_task(ocr_parse_resume_task, resume_id=resume_data.resume_id, task_id=task_id)
    return {"task_id": task_id}

@router.get("/resume/parse/{task_id}", summary='获取简历解析状态')
async def get_task_status(
    task_id: str,
    cache: HRCache = Depends(get_cache_instance),
    _: UserModel = Depends(get_current_user),
):
    """
    获取简历解析状态
    Args:
        task_id: 任务ID
        cache: 缓存实例
    Returns:
        dict: 任务信息
    """
    task_info = await cache.get_task_info(task_id)
    return task_info.model_dump()

@router.get("/resume/ocr/test")
async def resume_ocr_test():
    """
    测试简历OCR识别
    Returns:
        str: 成功信息
    """
    file_path = os.path.join(BASE_DIR, "uploads", "753a9a92-4c0c-45cd-a9bd-1339ba976653.pdf")
    paddle_ocr = PaddleOcr()
    job_id = await paddle_ocr.create_job(file_path)
    jsonl_url = await paddle_ocr.poll_for_state(job_id)
    extracted_text = await paddle_ocr.fetch_parsed_contents(jsonl_url)
    logger.info(f"extracted_text: {extracted_text}")
    return "success"