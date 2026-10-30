from src.interview.answer_evaluator import AnswerEvaluator
from src.interview.question_generator import QuestionGenerator


def test_question_generator_technical_and_hr():
    gen = QuestionGenerator()
    tech_qs = gen.generate_questions(
        company_name="Acme Tech",
        job_title="Senior Python Engineer",
        interview_stage="Technical",
        job_description="Python, PostgreSQL, Distributed Systems",
        candidate_skills=["Python", "SQLAlchemy"],
        num_questions=3,
    )
    assert len(tech_qs) == 3
    assert all("question_text" in q for q in tech_qs)
    assert all(sum(q["rubric_criteria"].values()) == 100 for q in tech_qs)

    hr_qs = gen.generate_questions(
        company_name="Acme Tech",
        job_title="Senior Python Engineer",
        interview_stage="HR",
        job_description="Python, PostgreSQL, Distributed Systems",
        num_questions=3,
    )
    assert len(hr_qs) == 3
    assert all(sum(q["rubric_criteria"].values()) == 100 for q in hr_qs)


def test_answer_evaluator():
    evaluator = AnswerEvaluator()
    eval_result = evaluator.evaluate_answer(
        job_title="Senior Python Engineer",
        interview_stage="Technical",
        question_text="Explain GIL in Python and how it affects concurrency.",
        expected_concepts=["GIL", "CPU-bound vs I/O-bound", "Multiprocessing", "Threading"],
        rubric_criteria={"technical_correctness": 40, "reasoning_explanation": 25, "practical_application": 20, "communication_structure": 15},
        candidate_answer="The Global Interpreter Lock prevents multiple native threads from executing Python bytecode simultaneously. For CPU-bound tasks, we use multiprocessing.",
    )

    assert "score" in eval_result
    assert 0.0 <= eval_result["score"] <= 100.0
    assert len(eval_result["correct_concepts"]) > 0
    assert "feedback" in eval_result
