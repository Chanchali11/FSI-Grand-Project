from typing import Any

from sqlalchemy.orm import Session

from src.database.models import (
    InterviewInvitation,
    InterviewSession,
    Job,
    ProcessingStatus,
    RecruiterDecision,
    RecruitmentCampaign,
    ResumeDocument,
    ScreeningResult,
)
from src.database.repository import DatabaseRepository


class CampaignService:
    """Manages companies, recruitment campaigns, and jobs."""

    @staticmethod
    def create_campaign(
        session: Session,
        company_name: str,
        campaign_title: str,
        target_hires: int = 1,
        company_domain: str = "",
        company_industry: str = "",
    ) -> RecruitmentCampaign:
        company = DatabaseRepository.get_or_create_company(session, name=company_name, domain=company_domain)
        if company_industry and not company.industry:
            company.industry = company_industry

        campaign = RecruitmentCampaign(
            company_id=company.id,
            title=campaign_title,
            target_hires=target_hires,
            status="Active",
        )
        session.add(campaign)
        session.flush()

        DatabaseRepository.log_audit_event(
            session=session,
            action="CAMPAIGN_CREATED",
            entity_type="RecruitmentCampaign",
            entity_id=campaign.id,
            company_id=company.id,
            details={"title": campaign_title, "target_hires": target_hires},
        )
        return campaign

    @staticmethod
    def create_job(
        session: Session,
        campaign_id: str,
        title: str,
        description: str,
        department: str = "Engineering",
        location: str = "Remote",
        experience_level: str = "Mid-Senior",
        min_years_experience: float = 2.0,
        required_skills: list[str] | None = None,
        preferred_skills: list[str] | None = None,
        mandatory_qualifications: list[str] | None = None,
        education_requirements: str = "Bachelor's degree or equivalent",
        technical_subjects: list[str] | None = None,
        interview_duration_minutes: int = 30,
        interview_stages: list[str] | None = None,
        weight_keywords: float = 0.25,
        weight_similarity: float = 0.25,
        weight_experience: float = 0.25,
        weight_semantic: float = 0.25,
        shortlist_threshold: float = 70.0,
    ) -> Job:
        job = Job(
            campaign_id=campaign_id,
            title=title,
            description=description,
            department=department,
            location=location,
            experience_level=experience_level,
            min_years_experience=min_years_experience,
            required_skills=required_skills or [],
            preferred_skills=preferred_skills or [],
            mandatory_qualifications=mandatory_qualifications or [],
            education_requirements=education_requirements,
            technical_subjects=technical_subjects or [],
            interview_duration_minutes=interview_duration_minutes,
            interview_stages=interview_stages or ["Technical", "HR"],
            weight_keywords=weight_keywords,
            weight_similarity=weight_similarity,
            weight_experience=weight_experience,
            weight_semantic=weight_semantic,
            shortlist_threshold=shortlist_threshold,
        )
        session.add(job)
        session.flush()

        # Retrieve company_id
        campaign = session.query(RecruitmentCampaign).filter(RecruitmentCampaign.id == campaign_id).first()
        company_id = campaign.company_id if campaign else None

        DatabaseRepository.log_audit_event(
            session=session,
            action="JOB_CREATED",
            entity_type="Job",
            entity_id=job.id,
            company_id=company_id,
            details={"title": title, "department": department},
        )
        return job

    @staticmethod
    def get_dashboard_metrics(session: Session, campaign_id: str | None = None) -> dict[str, Any]:
        """Compute real-time recruitment metrics across campaigns or for a selected campaign."""
        camp_query = session.query(RecruitmentCampaign)
        if campaign_id:
            camp_query = camp_query.filter(RecruitmentCampaign.id == campaign_id)
        campaigns = camp_query.all()
        campaign_ids = [c.id for c in campaigns]

        if not campaign_ids:
            return {
                "total_campaigns": 0,
                "total_resumes": 0,
                "processed_count": 0,
                "failed_count": 0,
                "duplicate_count": 0,
                "manual_review_count": 0,
                "meets_criteria_count": 0,
                "shortlisted_count": 0,
                "invitations_sent": 0,
                "interviews_pending": 0,
                "technical_completed": 0,
                "hr_completed": 0,
                "awaiting_final_review": 0,
            }

        resumes = session.query(ResumeDocument).filter(ResumeDocument.campaign_id.in_(campaign_ids)).all()
        resume_ids = [r.id for r in resumes]

        total_resumes = len(resumes)
        processed_count = sum(1 for r in resumes if r.processing_status == ProcessingStatus.PROCESSED.value)
        failed_count = sum(1 for r in resumes if r.processing_status == ProcessingStatus.FAILED.value)
        duplicate_count = sum(1 for r in resumes if r.is_duplicate)

        # Screening results
        screenings = session.query(ScreeningResult).filter(ScreeningResult.resume_id.in_(resume_ids)).all() if resume_ids else []
        manual_review_count = sum(1 for s in screenings if s.recommendation == "Needs Manual Review")
        meets_criteria_count = sum(1 for s in screenings if s.recommendation == "Meets Configured Criteria")
        shortlisted_count = sum(1 for s in screenings if s.recruiter_decision in (RecruiterDecision.SHORTLISTED.value, RecruiterDecision.INVITED.value, RecruiterDecision.SELECTED_FOR_NEXT_ROUND.value, RecruiterDecision.HIRED.value))
        selected_for_next_round_count = sum(1 for s in screenings if s.recruiter_decision == RecruiterDecision.SELECTED_FOR_NEXT_ROUND.value)
        awaiting_final_review = sum(1 for s in screenings if s.recruiter_decision == RecruiterDecision.PENDING.value and s.recommendation == "Meets Configured Criteria")

        # Interviews
        jobs = session.query(Job).filter(Job.campaign_id.in_(campaign_ids)).all()
        job_ids = [j.id for j in jobs]

        invitations = session.query(InterviewInvitation).filter(InterviewInvitation.job_id.in_(job_ids)).all() if job_ids else []
        invitations_sent = len(invitations)
        interviews_pending = sum(1 for inv in invitations if not inv.is_used)

        sessions = session.query(InterviewSession).filter(InterviewSession.job_id.in_(job_ids)).all() if job_ids else []
        technical_completed = sum(1 for s in sessions if s.stage in ("Technical", "Comprehensive") and s.status == "Completed")
        hr_completed = sum(1 for s in sessions if s.stage == "HR" and s.status == "Completed")
        interviews_completed = sum(1 for s in sessions if s.status == "Completed")

        return {
            "total_campaigns": len(campaigns),
            "total_resumes": total_resumes,
            "processed_count": processed_count,
            "failed_count": failed_count,
            "duplicate_count": duplicate_count,
            "manual_review_count": manual_review_count,
            "meets_criteria_count": meets_criteria_count,
            "shortlisted_count": shortlisted_count,
            "selected_for_next_round_count": selected_for_next_round_count,
            "invitations_sent": invitations_sent,
            "interviews_pending": interviews_pending,
            "interviews_completed": interviews_completed,
            "technical_completed": technical_completed,
            "hr_completed": hr_completed,
            "awaiting_final_review": awaiting_final_review,
        }
