from fastapi import APIRouter, Depends, HTTPException, status
from dependencies import get_current_user, get_session_instance
from models import AsyncSession
from fastapi import UploadFile, File
from models.user import UserModel
from settings import settings
import os
from uuid import uuid4
import aiofiles
from core.email_bot.pdf import WordToPdfConverter
from loguru import logger

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
    try:
        async with aiofiles.open(file_path, mode="wb") as fp:
            # 文件太大的话，内存可能会不够
            content = await file.read(1024)
            while content:
                await fp.write(content)
                content = await file.read(1024)
    finally:
        await fp.close()
    
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
    
    # 如果是图片，那么就保存图片
    async with session.begin():
        pass