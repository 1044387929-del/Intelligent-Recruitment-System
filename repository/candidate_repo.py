from . import BaseRepo
from models.candidate import ResumeModel
from sqlalchemy import select, update
from models.candidate import CandidateModel
from models.candidate import CandidateAIScoreModel
from sqlalchemy.orm import selectinload
from models.candidate import CandidateStatusEnum

class ReusmeRepo(BaseRepo):
    async def create_resume(self, file_path: str, uploader_id: str) -> ResumeModel:
        """
        创建简历
        """
        resume = ResumeModel(file_path=file_path, uploader_id=uploader_id)
        self.session.add(resume)
        return resume

    
    async def get_resume_by_id(self, resume_id: str) -> ResumeModel | None:
        """
        获取简历
        """
        stmt = select(ResumeModel).where(ResumeModel.id == resume_id)
        resume = await self.session.scalar(stmt)
        return resume
    
class CandidateRepo(BaseRepo):
    async def create_candidate(self, candidate_data: dict) -> CandidateModel:
        """
        创建候选人
        """
        candidate = CandidateModel(**candidate_data)
        self.session.add(candidate)
        return candidate
    
    async def get_by_id(self, candidate_id: str) -> CandidateModel | None:
        """
        获取候选人
        """
        stmt = select(CandidateModel).where(
            CandidateModel.id == candidate_id
            ).options(
            selectinload(CandidateModel.position),
            selectinload(CandidateModel.resume),
            selectinload(CandidateModel.creator),
        )
        return await self.session.scalar(stmt)
    
    async def update_candidate_status(self, candidate_id: str, status: CandidateStatusEnum):
        """
        更新候选人状态
        """
        stmt = update(CandidateModel).where(
        ).values(status=status)
        return await self.session.execute(stmt)

class CandidateAIScoreRepo(BaseRepo):
    async def create_candidate_score(self, candidate_id: str, candidate_score_dict: dict) -> CandidateAIScoreModel:
        """
        创建候选人AI评分
        """
        candidate_score = CandidateAIScoreModel(**candidate_score_dict, candidate_id=candidate_id)
        self.session.add(candidate_score)
        return candidate_score
    
    async def get_by_candidate_id(self, candidate_id: str) -> CandidateAIScoreModel | None:
        # 获取候选人AI评分
        stmt = select(CandidateAIScoreModel).where(
            CandidateAIScoreModel.candidate_id == candidate_id
            ).options(
                selectinload(CandidateAIScoreModel.candidate))
        return await self.session.scalar(stmt)

    async def update_candidate_status(self, candidate_id: str, status: CandidateStatusEnum):
        """
        更新候选人状态
        """
        candidate_score = self.get_by_candidate_id(candidate_id)
        candidate_score.status = status