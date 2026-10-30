

class InterviewRubrics:
    """Pre-configured transparent rubrics totaling exactly 100 points."""

    TECHNICAL_RUBRIC: dict[str, int] = {
        "technical_correctness": 40,
        "reasoning_explanation": 25,
        "practical_application": 20,
        "communication_structure": 15,
    }

    HR_RUBRIC: dict[str, int] = {
        "relevance": 30,
        "structure_clarity": 25,
        "specific_examples": 25,
        "communication": 20,
    }

    @staticmethod
    def validate_rubric(rubric: dict[str, int]) -> bool:
        """Validate that all rubric criteria sum to exactly 100 points."""
        return sum(rubric.values()) == 100

    @classmethod
    def get_rubric_for_stage(cls, stage: str) -> dict[str, int]:
        if "hr" in stage.lower():
            return cls.HR_RUBRIC.copy()
        return cls.TECHNICAL_RUBRIC.copy()

    @staticmethod
    def get_rubric_descriptions(stage: str) -> dict[str, str]:
        if "hr" in stage.lower():
            return {
                "relevance": "Direct alignment of the response to the question and cultural competencies (30 pts)",
                "structure_clarity": "Structured communication adhering to the STAR framework (Situation, Task, Action, Result) (25 pts)",
                "specific_examples": "Authentic personal actions, measurable outcomes, and introspective reflection (25 pts)",
                "communication": "Clarity, active engagement, and concise role-related articulation (20 pts)",
            }
        return {
            "technical_correctness": "Accurate concepts, edge-case handling, and precision of technical facts (40 pts)",
            "reasoning_explanation": "Logical problem decomposition and trade-off justification (25 pts)",
            "practical_application": "Real-world scalability, design patterns, and operational depth (20 pts)",
            "communication_structure": "Coherent flow, clarity, and concise technical vocabulary (15 pts)",
        }
