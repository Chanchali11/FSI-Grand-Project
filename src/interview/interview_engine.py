from datetime import datetime, timezone
import logging
from typing import Any

from sqlalchemy.orm import Session

from src.database.models import (
    CandidateProfile,
    InterviewInvitation,
    InterviewQuestion,
    InterviewSession,
    InterviewStage,
    InterviewStatus,
    Job,
    RecruiterDecision,
    ResumeDocument,
)
from src.interview.answer_evaluator import AnswerEvaluator
from src.interview.dynamic_question_generator import DynamicQuestionGenerator
from src.interview.question_generator import QuestionGenerator
from src.interview.resume_profile import NormalizedResumeProfile, ResumeEducation, ResumeProject, ResumeWorkExperience

logger = logging.getLogger(__name__)


class InterviewEngine:
    """
    Coordinates dynamic resume-driven interview session workflows,
    randomized topic selection, live answer evaluations, and contextual follow-ups.
    """

    def __init__(self):
        self.question_generator = QuestionGenerator()
        self.dynamic_generator = DynamicQuestionGenerator()
        self.answer_evaluator = AnswerEvaluator()

    def build_normalized_profile_from_db(
        self, session: Session, candidate_id: str, job_id: str | None = None
    ) -> NormalizedResumeProfile:
        """Extracts structured candidate resume information from database parsed records."""
        candidate = session.query(CandidateProfile).filter(CandidateProfile.id == candidate_id).first()
        profile = NormalizedResumeProfile(
            name=candidate.name if candidate else "Candidate",
            email=candidate.email if candidate else None,
            phone=candidate.phone if candidate else None,
            years_experience=candidate.years_experience if candidate else 0.0,
        )

        # Pull parsed data from associated resume
        query = session.query(ResumeDocument).filter(ResumeDocument.candidate_id == candidate_id)
        if job_id:
            query = query.filter(ResumeDocument.job_id == job_id)
        doc = query.order_by(ResumeDocument.uploaded_at.desc()).first()

        if doc and doc.parsed_data:
            pd = doc.parsed_data
            profile.skills = pd.technical_skills or []
            profile.programming_languages = [s for s in (pd.technical_skills or []) if s.lower() in ("python", "java", "c++", "golang", "javascript", "typescript", "ruby", "rust", "php", "sql")]
            profile.frameworks_and_tools = [s for s in (pd.technical_skills or []) if s not in profile.programming_languages]
            profile.certifications = pd.certifications or []
            profile.achievements = pd.achievements or []
            profile.years_experience = pd.total_years_experience or profile.years_experience

            # Projects
            for p in (pd.projects or []):
                if isinstance(p, dict):
                    profile.projects.append(
                        ResumeProject(
                            name=p.get("title") or p.get("name") or "Project",
                            technologies=p.get("technologies") or [],
                            description=p.get("description"),
                        )
                    )

            # Work Experience
            for w in (pd.work_experience or []):
                if isinstance(w, dict):
                    profile.work_experience.append(
                        ResumeWorkExperience(
                            company=w.get("company", "Company"),
                            role=w.get("role", "Software Engineer"),
                            duration=w.get("duration"),
                            highlights=w.get("highlights", []),
                        )
                    )

            # Education
            for e in (pd.education or []):
                if isinstance(e, dict):
                    profile.education.append(
                        ResumeEducation(
                            degree=e.get("degree", "Degree"),
                            institution=e.get("institution"),
                            year=str(e.get("year")) if e.get("year") else None,
                        )
                    )

        # Fallback if profile is completely bare
        if not profile.skills:
            profile.skills = ["Python", "Problem Solving", "System Architecture"]
        if not profile.projects:
            profile.projects = [ResumeProject(name="Technical Portfolio Application", technologies=["Python", "SQL"])]

        return profile

    def start_session(
        self,
        session: Session,
        invitation_id: str | None,
        candidate_id: str,
        job_id: str,
        stage: str = InterviewStage.TECHNICAL.value,
        candidate_consent: bool = True,
        num_questions: int = 5,
        difficulty: str = "Intermediate",
    ) -> InterviewSession:
        job = session.query(Job).filter(Job.id == job_id).first()
        company_name = job.campaign.company.name if job and job.campaign and job.campaign.company else "Company"

        # Check existing active session
        existing = (
            session.query(InterviewSession)
            .filter(
                InterviewSession.candidate_id == candidate_id,
                InterviewSession.job_id == job_id,
                InterviewSession.stage == stage,
                InterviewSession.status == InterviewStatus.IN_PROGRESS.value,
            )
            .first()
        )
        if existing:
            return existing

        # Extract normalized resume profile strictly based on candidate's uploaded resume
        profile = self.build_normalized_profile_from_db(session, candidate_id, job_id)

        # Calculate category quotas using the 30/30/20/10/10 weighted distribution
        category_distribution = self.dynamic_generator.calculate_topic_distribution(
            profile=profile, num_questions=num_questions
        )

        interview_session = InterviewSession(
            invitation_id=invitation_id,
            candidate_id=candidate_id,
            job_id=job_id,
            stage=stage,
            status=InterviewStatus.IN_PROGRESS.value,
            current_question_index=0,
            total_questions=len(category_distribution),
            candidate_consent_given=candidate_consent,
            consent_timestamp=datetime.now(timezone.utc) if candidate_consent else None,
            started_at=datetime.now(timezone.utc),
        )
        session.add(interview_session)
        session.flush()

        # Dynamically generate questions personalized to actual resume
        previous_q_texts = []
        for idx, cat in enumerate(category_distribution):
            q_data = self.dynamic_generator.generate_next_question(
                resume_profile=profile,
                job_title=job.title if job else "Software Engineer",
                company_name=company_name,
                previous_questions=previous_q_texts,
                previous_answers=[],
                difficulty=difficulty,
                category=cat,
                order_index=idx + 1,
            )
            previous_q_texts.append(q_data["question_text"])

            q = InterviewQuestion(
                session_id=interview_session.id,
                question_order=idx + 1,
                question_type=q_data.get("question_type", "conceptual"),
                category=q_data.get("category", "General"),
                question_text=q_data.get("question_text", ""),
                expected_concepts=q_data.get("expected_concepts", []),
                rubric_criteria=q_data.get("rubric_criteria", {}),
            )
            session.add(q)

        session.commit()
        return interview_session

    def get_current_question(self, session: Session, session_id: str) -> InterviewQuestion | None:
        interview_session = session.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        if not interview_session:
            return None

        current_idx = interview_session.current_question_index
        return (
            session.query(InterviewQuestion)
            .filter(
                InterviewQuestion.session_id == session_id,
                InterviewQuestion.question_order == current_idx + 1,
            )
            .first()
        )

    def submit_answer(
        self,
        session: Session,
        session_id: str,
        question_id: str,
        candidate_answer: str,
        answer_mode: str = "text",
        difficulty: str = "Intermediate",
    ) -> dict[str, Any]:
        interview_session = session.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        question = session.query(InterviewQuestion).filter(InterviewQuestion.id == question_id).first()

        if not interview_session or not question:
            return {"error": "Invalid session or question ID."}

        job = session.query(Job).filter(Job.id == interview_session.job_id).first()
        job_title = job.title if job else "Software Engineer"

        # Evaluate Answer
        eval_result = self.answer_evaluator.evaluate_answer(
            job_title=job_title,
            interview_stage=interview_session.stage,
            question_text=question.question_text,
            expected_concepts=question.expected_concepts or [],
            rubric_criteria=question.rubric_criteria or {},
            candidate_answer=candidate_answer,
        )

        question.candidate_answer = candidate_answer
        question.answer_mode = answer_mode
        question.answered_at = datetime.now(timezone.utc)
        question.score = eval_result.get("score", 0.0)
        question.evaluation_feedback = eval_result.get("feedback", "")
        question.correct_concepts = eval_result.get("correct_concepts", [])
        question.missing_concepts = eval_result.get("missing_concepts", [])
        question.improvement_suggestions = eval_result.get("improvement_suggestions", [])
        question.rubric_scores = eval_result.get("rubric_scores", {})

        # Generate intelligent contextual follow-up question
        follow_up_data = self.dynamic_generator.generate_follow_up_question(
            original_question=question.question_text,
            candidate_answer=candidate_answer,
            category=question.category,
            job_title=job_title,
            difficulty=difficulty,
        )
        if follow_up_data:
            question.follow_up_question = follow_up_data.get("question_text", "")
            eval_result["follow_up_question"] = question.follow_up_question

        # Advance question index
        interview_session.current_question_index += 1

        is_complete = interview_session.current_question_index >= interview_session.total_questions
        if is_complete:
            self._finalize_session(session, interview_session)

        session.commit()

        return {
            "evaluation": eval_result,
            "is_complete": is_complete,
            "next_question_index": interview_session.current_question_index,
        }

    def _finalize_session(self, session: Session, interview_session: InterviewSession):
        """Calculate overall interview score and mark invitation as used."""
        interview_session.status = InterviewStatus.COMPLETED.value
        interview_session.completed_at = datetime.now(timezone.utc)

        all_questions = session.query(InterviewQuestion).filter(InterviewQuestion.session_id == interview_session.id).all()
        scores = [q.score for q in all_questions if q.score is not None]
        if scores:
            interview_session.overall_interview_score = round(sum(scores) / len(scores), 1)

        # Mark invitation as used & completed
        if interview_session.invitation_id:
            invitation = session.query(InterviewInvitation).filter(InterviewInvitation.id == interview_session.invitation_id).first()
            if invitation:
                invitation.is_used = True
                invitation.used_at = datetime.now(timezone.utc)
                invitation.invitation_status = InterviewStatus.COMPLETED.value
                invitation.completed_at = datetime.now(timezone.utc)

        # Update candidate screening status
        doc = (
            session.query(ResumeDocument)
            .filter(
                ResumeDocument.candidate_id == interview_session.candidate_id,
                ResumeDocument.job_id == interview_session.job_id,
            )
            .first()
        )
        if doc and doc.screening_result:
            doc.screening_result.recruiter_decision = RecruiterDecision.INTERVIEWED.value
