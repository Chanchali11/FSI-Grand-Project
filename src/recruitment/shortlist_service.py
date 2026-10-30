from typing import Any

from sqlalchemy.orm import Session

from src.database.models import (
    CandidateProfile,
    RecruiterDecision,
    ResumeDocument,
    ScreeningResult,
)
from src.database.repository import DatabaseRepository


class ShortlistService:
    """Manages proposed shortlists, recruiter overrides, and decision workflows."""

    @staticmethod
    def get_candidate_screening_list(
        session: Session,
        job_id: str,
        recommendation_filter: str | None = None,
        min_score: float | None = None,
        decision_filter: str | None = None,
        search_query: str | None = None,
    ) -> list[dict[str, Any]]:
        query = (
            session.query(ScreeningResult, ResumeDocument, CandidateProfile)
            .join(ResumeDocument, ScreeningResult.resume_id == ResumeDocument.id)
            .outerjoin(CandidateProfile, ResumeDocument.candidate_id == CandidateProfile.id)
            .filter(ResumeDocument.job_id == job_id)
        )

        if recommendation_filter and recommendation_filter != "All":
            query = query.filter(ScreeningResult.recommendation == recommendation_filter)

        if min_score is not None:
            query = query.filter(ScreeningResult.overall_score >= min_score)

        if decision_filter and decision_filter != "All":
            query = query.filter(ScreeningResult.recruiter_decision == decision_filter)

        results = query.order_by(ScreeningResult.overall_score.desc()).all()

        candidate_list = []
        for s_res, doc, cand in results:
            cand_name = cand.name if cand else "Candidate"
            cand_email = cand.email if cand else "N/A"

            if search_query:
                sq = search_query.lower()
                matched_search = (
                    sq in (cand_name or "").lower()
                    or sq in (cand_email or "").lower()
                    or any(sq in str(sk).lower() for sk in (s_res.matched_skills or []))
                )
                if not matched_search:
                    continue

            # Extract education summary
            edu_str = "Not Specified"
            if doc and doc.parsed_data and doc.parsed_data.education:
                edu_list = doc.parsed_data.education
                if isinstance(edu_list, list) and len(edu_list) > 0:
                    first_edu = edu_list[0]
                    if isinstance(first_edu, dict):
                        edu_str = f"{first_edu.get('degree', 'Degree')} ({first_edu.get('institution', 'University')})"

            candidate_list.append({
                "screening_id": s_res.id,
                "resume_id": doc.id,
                "candidate_id": cand.id if cand else None,
                "candidate_name": cand_name,
                "candidate_email": cand_email,
                "candidate_phone": cand.phone if cand else "N/A",
                "filename": doc.original_filename,
                "overall_score": s_res.overall_score,
                "keyword_coverage": s_res.keyword_coverage_score,
                "text_similarity": s_res.text_similarity_score,
                "experience_score": s_res.experience_score,
                "semantic_score": s_res.semantic_score,
                "mandatory_passed": s_res.mandatory_criteria_passed,
                "matched_skills": s_res.matched_skills or [],
                "missing_skills": s_res.missing_skills or [],
                "unclear_evidence": s_res.unclear_evidence or [],
                "education_match": edu_str,
                "recommendation": s_res.recommendation,
                "recruiter_decision": s_res.recruiter_decision,
                "recruiter_notes": s_res.recruiter_notes or "",
                "override_reason": s_res.recruiter_override_reason or "",
                "evidence_excerpts": s_res.evidence_excerpts or {},
            })

        return candidate_list

    @staticmethod
    def update_recruiter_decision(
        session: Session,
        screening_id: str,
        decision: str,
        recruiter_id: str | None = None,
        recruiter_notes: str = "",
        override_reason: str = "",
    ) -> bool:
        screening = session.query(ScreeningResult).filter(ScreeningResult.id == screening_id).first()
        if not screening:
            return False

        old_decision = screening.recruiter_decision
        screening.recruiter_decision = decision
        screening.recruiter_notes = recruiter_notes
        if override_reason:
            screening.recruiter_override_reason = override_reason

        # Log audit trail
        DatabaseRepository.log_audit_event(
            session=session,
            action="RECRUITER_DECISION_UPDATED",
            entity_type="ScreeningResult",
            entity_id=screening.id,
            user_id=recruiter_id,
            details={
                "old_decision": old_decision,
                "new_decision": decision,
                "override_reason": override_reason,
            },
        )
        return True

    @staticmethod
    def bulk_approve_shortlist(
        session: Session,
        job_id: str,
        threshold_score: float = 70.0,
        recruiter_id: str | None = None,
    ) -> int:
        """Approve all candidates meeting score and mandatory criteria who are still pending."""
        screenings = (
            session.query(ScreeningResult)
            .join(ResumeDocument, ScreeningResult.resume_id == ResumeDocument.id)
            .filter(
                ResumeDocument.job_id == job_id,
                ScreeningResult.overall_score >= threshold_score,
                ScreeningResult.mandatory_criteria_passed.is_(True),
                ScreeningResult.recruiter_decision == RecruiterDecision.PENDING.value,

            )
            .all()
        )

        approved_count = 0
        for s in screenings:
            s.recruiter_decision = RecruiterDecision.SHORTLISTED.value
            approved_count += 1

        DatabaseRepository.log_audit_event(
            session=session,
            action="BULK_SHORTLIST_APPROVED",
            entity_type="Job",
            entity_id=job_id,
            user_id=recruiter_id,
            details={"approved_count": approved_count, "threshold": threshold_score},
        )
        return approved_count

    @staticmethod
    def bulk_update_decisions(
        session: Session,
        screening_ids: list[str],
        decision: str,
        recruiter_id: str | None = None,
        recruiter_notes: str = "",
    ) -> int:
        """Update recruiter decision for a list of specific screening IDs."""
        updated = 0
        for s_id in screening_ids:
            res = session.query(ScreeningResult).filter(ScreeningResult.id == s_id).first()
            if res:
                res.recruiter_decision = decision
                if recruiter_notes:
                    res.recruiter_notes = recruiter_notes
                updated += 1
        DatabaseRepository.log_audit_event(
            session=session,
            action="BULK_DECISION_UPDATED",
            entity_type="ScreeningResult",
            user_id=recruiter_id,
            details={"updated_count": updated, "new_decision": decision},
        )
        return updated
