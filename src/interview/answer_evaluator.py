from typing import Any

from src.ai.claude_client import ClaudeClient
from src.security.authentication import sanitize_input_text


class AnswerEvaluator:
    """Evaluates candidate interview answers against transparent rubric criteria."""

    def __init__(self, claude_client: ClaudeClient | None = None):
        self.ai = claude_client or ClaudeClient()

    def evaluate_answer(
        self,
        job_title: str,
        interview_stage: str,
        question_text: str,
        expected_concepts: list[str],
        rubric_criteria: dict[str, Any],
        candidate_answer: str,
    ) -> dict[str, Any]:
        sanitized_answer = sanitize_input_text(candidate_answer)
        if not sanitized_answer.strip():
            return {
                "score": 0.0,
                "rubric_scores": {k: 0.0 for k in rubric_criteria},
                "correct_concepts": [],
                "missing_concepts": expected_concepts,
                "feedback": "No answer was submitted.",
                "improvement_suggestions": ["Please provide a response addressing the question."],
                "follow_up_question": "Would you like another opportunity to answer this question?",
            }

        return self.ai.evaluate_interview_answer(
            job_title=job_title,
            interview_stage=interview_stage,
            question_text=question_text,
            expected_concepts=expected_concepts,
            rubric_criteria=rubric_criteria,
            candidate_answer=sanitized_answer,
        )
