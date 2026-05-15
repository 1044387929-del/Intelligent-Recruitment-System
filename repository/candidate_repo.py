from . import BaseRepo
from models.candidate import ResumeModel
from sqlalchemy import select

class ReusmeRepo(BaseRepo):
    async def create_resume(self, file_path: str, uploader_id: str) -> ResumeModel:
        resume = ResumeModel(file_path=file_path, uploader_id=uploader_id)
        self.session.add(resume)
        return resume

    
    async def get_resume_by_id(self, resume_id: str) -> ResumeModel | None:
        stmt = select(ResumeModel).where(ResumeModel.id == resume_id)
        resume = await self.session.scalar(stmt)
        return resume