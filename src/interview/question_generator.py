from typing import Any

from src.ai.claude_client import ClaudeClient
from src.interview.rubrics import InterviewRubrics


class QuestionGenerator:
    """Generates personalized, job-aligned questions using Claude AI with deterministic fallback."""

    def __init__(self, claude_client: ClaudeClient | None = None):
        self.ai = claude_client or ClaudeClient()

    def generate_questions(
        self,
        company_name: str,
        job_title: str,
        interview_stage: str,
        job_description: str,
        candidate_skills: list[str] | None = None,
        candidate_projects: list[dict[str, Any]] | None = None,
        num_questions: int = 5,
    ) -> list[dict[str, Any]]:
        questions = self.ai.generate_interview_questions(
            company_name=company_name,
            job_title=job_title,
            interview_type=interview_stage,
            job_requirements=job_description,
            candidate_skills=candidate_skills or [],
            candidate_projects=candidate_projects or [],
            num_questions=num_questions,
        )

        rubric = InterviewRubrics.get_rubric_for_stage(interview_stage)
        # Ensure rubrics are attached to every question
        for q in questions:
            if not q.get("rubric_criteria"):
                q["rubric_criteria"] = rubric
        return questions
