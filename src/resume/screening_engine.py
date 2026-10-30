from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.database.models import (
    CandidateProfile,
    Job,
    ParsedResumeData,
    ProcessingStatus,
    RecruiterDecision,
    ResumeDocument,
    ScreeningResult,
)
from src.resume.resume_extractor import ResumeExtractor
from src.resume.skill_matcher import SkillMatcher


class ScreeningEngine:
    """Executes end-to-end resume extraction, scoring, and DB persistence for a resume against a job."""

    def __init__(self):
        self.extractor = ResumeExtractor()
        self.matcher = SkillMatcher()

    def process_and_screen_resume(self, session: Session, resume_id: str) -> ScreeningResult | None:
        resume = session.query(ResumeDocument).filter(ResumeDocument.id == resume_id).first()
        if not resume or not resume.raw_text:
            return None

        job = session.query(Job).filter(Job.id == resume.job_id).first()
        if not job:
            return None

        # 1. Parse Structured Resume Data
        structured = self.extractor.parse_resume(resume.raw_text)

        # 2. Create or Update CandidateProfile
        candidate = resume.candidate
        if not candidate:
            candidate = CandidateProfile(
                name=structured.name or "Candidate",
                email=structured.email,
                phone=structured.phone,
                linkedin=structured.linkedin,
                github=structured.github,
                portfolio=structured.portfolio,
                years_experience=structured.total_years_experience,
            )
            session.add(candidate)
            session.flush()
            resume.candidate_id = candidate.id
        else:
            if structured.name and candidate.name == "Candidate":
                candidate.name = structured.name
            if structured.email and not candidate.email:
                candidate.email = structured.email
            if structured.phone and not candidate.phone:
                candidate.phone = structured.phone

        # 3. Store Parsed Resume Data
        parsed_record = resume.parsed_data
        if not parsed_record:
            parsed_record = ParsedResumeData(
                resume_id=resume.id,
                extracted_name=structured.name,
                extracted_email=structured.email,
                extracted_phone=structured.phone,
                technical_skills=structured.technical_skills,
                soft_skills=structured.soft_skills,
                education=[e.model_dump() for e in structured.education],
                work_experience=[w.model_dump() for w in structured.work_experience],
                projects=[p.model_dump() for p in structured.projects],
                certifications=structured.certifications,
                achievements=structured.achievements,
                total_years_experience=structured.total_years_experience,
                skill_evidence=structured.skill_evidence,
            )
            session.add(parsed_record)
        else:
            parsed_record.extracted_name = structured.name
            parsed_record.extracted_email = structured.email
            parsed_record.technical_skills = structured.technical_skills
            parsed_record.education = [e.model_dump() for e in structured.education]
            parsed_record.work_experience = [w.model_dump() for w in structured.work_experience]
            parsed_record.projects = [p.model_dump() for p in structured.projects]
            parsed_record.total_years_experience = structured.total_years_experience
            parsed_record.skill_evidence = structured.skill_evidence

        # 4. Perform Job-Specific Screening
        evaluation = self.matcher.evaluate_candidate_for_job(
            job_title=job.title,
            job_description=job.description,
            required_skills=job.required_skills or [],
            preferred_skills=job.preferred_skills or [],
            mandatory_qualifications=job.mandatory_qualifications or [],
            min_years_experience=job.min_years_experience or 2.0,
            structured_resume=structured,
            raw_resume_text=resume.raw_text,
            weight_keywords=job.weight_keywords or 0.25,
            weight_similarity=job.weight_similarity or 0.25,
            weight_experience=job.weight_experience or 0.25,
            weight_semantic=job.weight_semantic or 0.25,
            shortlist_threshold=job.shortlist_threshold or 70.0,
        )

        # 5. Persist Screening Result
        screening = resume.screening_result
        if not screening:
            screening = ScreeningResult(
                resume_id=resume.id,
                overall_score=evaluation.overall_score,
                keyword_coverage_score=evaluation.keyword_coverage_score,
                text_similarity_score=evaluation.text_similarity_score,
                experience_score=evaluation.experience_score,
                semantic_score=evaluation.semantic_score,
                mandatory_criteria_passed=evaluation.mandatory_criteria_passed,
                mandatory_details=[m.model_dump() for m in evaluation.mandatory_evaluations],
                matched_skills=evaluation.matched_skills,
                missing_skills=evaluation.missing_skills,
                unclear_evidence=evaluation.unclear_evidence,
                evidence_excerpts=evaluation.evidence_excerpts,
                recommendation=evaluation.recommendation,
                recommendation_notes=evaluation.recommendation_notes,
                recruiter_decision=RecruiterDecision.PENDING.value,
            )
            session.add(screening)
        else:
            screening.overall_score = evaluation.overall_score
            screening.keyword_coverage_score = evaluation.keyword_coverage_score
            screening.text_similarity_score = evaluation.text_similarity_score
            screening.experience_score = evaluation.experience_score
            screening.semantic_score = evaluation.semantic_score
            screening.mandatory_criteria_passed = evaluation.mandatory_criteria_passed
            screening.mandatory_details = [m.model_dump() for m in evaluation.mandatory_evaluations]
            screening.matched_skills = evaluation.matched_skills
            screening.missing_skills = evaluation.missing_skills
            screening.unclear_evidence = evaluation.unclear_evidence
            screening.evidence_excerpts = evaluation.evidence_excerpts
            screening.recommendation = evaluation.recommendation
            screening.recommendation_notes = evaluation.recommendation_notes

        # Update Resume Processing Status
        resume.processing_status = ProcessingStatus.PROCESSED.value
        resume.processed_at = datetime.now(timezone.utc)
        session.flush()

        return screening
