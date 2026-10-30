import os
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from src.database.models import (
    CandidateProfile,
    InterviewInvitation,
    InterviewSession,
    ResumeDocument,
)
from src.database.repository import DatabaseRepository


class PrivacyManager:
    """Manages candidate data privacy, GDPR compliance, consent records, and safe deletion."""

    @staticmethod
    def get_privacy_notice() -> dict[str, Any]:
        return {
            "title": "Hirexp Ai Candidate Privacy Notice & Fair Processing Declaration",
            "effective_date": "2026-01-01",
            "data_controller": "Hirexp Recruitment System",
            "purposes": [
                "Automated extraction and matching of technical skills and qualifications against job requirements.",
                "Conducting virtual interactive technical and HR interview evaluations.",
                "Generating objective, rubric-based evaluation summaries for human recruiter review.",
            ],
            "protected_characteristics_policy": (
                "Hirexp Ai strictly prohibits and excludes protected attributes (such as race, religion, gender, "
                "age, caste, marital status, and physical disability) from scoring and shortlisting algorithms. "
                "Evaluations are strictly derived from verified skills, project evidence, and candidate answers."
            ),
            "retention_policy": "Candidate resumes and interview records are retained for a default of 90 days, after which they are eligible for automated purging or immediate on-demand deletion.",
            "rights": ["Right to access", "Right to rectification", "Right to erasure ('Right to be Forgotten')", "Right to human recruiter override"],
        }

    @staticmethod
    def delete_candidate_data(session: Session, candidate_id: str, company_id: str | None = None) -> bool:
        """Completely delete candidate profile, attached resumes, physical files, and interview sessions."""
        candidate = session.query(CandidateProfile).filter(CandidateProfile.id == candidate_id).first()
        if not candidate:
            return False

        # Find resumes and remove physical files
        resumes = session.query(ResumeDocument).filter(ResumeDocument.candidate_id == candidate_id).all()
        for res in resumes:
            if res.storage_path and os.path.exists(res.storage_path):
                try:
                    os.remove(res.storage_path)
                except OSError:
                    pass
            session.delete(res)

        # Delete interview sessions and questions
        sessions = session.query(InterviewSession).filter(InterviewSession.candidate_id == candidate_id).all()
        for s in sessions:
            session.delete(s)

        # Delete invitations
        invitations = session.query(InterviewInvitation).filter(InterviewInvitation.candidate_id == candidate_id).all()
        for inv in invitations:
            session.delete(inv)

        # Delete candidate profile
        session.delete(candidate)

        # Log audit event
        DatabaseRepository.log_audit_event(
            session=session,
            action="CANDIDATE_DATA_PURGED",
            entity_type="CandidateProfile",
            entity_id=candidate_id,
            company_id=company_id,
            details={"reason": "User or Recruiter requested complete erasure under GDPR"},
        )
        return True

    @staticmethod
    def purge_expired_records(session: Session, retention_days: int = 90) -> int:
        """Purge records older than retention threshold."""
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        expired_resumes = session.query(ResumeDocument).filter(ResumeDocument.uploaded_at < cutoff).all()
        purged_count = 0
        for res in expired_resumes:
            if res.storage_path and os.path.exists(res.storage_path):
                try:
                    os.remove(res.storage_path)
                except OSError:
                    pass
            session.delete(res)
            purged_count += 1
        return purged_count
