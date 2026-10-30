from src.interview.dynamic_question_generator import DynamicQuestionGenerator
from src.interview.resume_profile import NormalizedResumeProfile, ResumeProject
from src.reports.interview_report_service import InterviewReportService


def test_topic_distribution_default():
    profile = NormalizedResumeProfile(
        name="Alice Smith",
        skills=["Python", "PostgreSQL", "Docker", "Machine Learning"],
        programming_languages=["Python", "SQL"],
        frameworks_and_tools=["FastAPI", "Docker"],
        projects=[
            ResumeProject(name="Ambulance Routing AI", technologies=["Python", "PostgreSQL"]),
            ResumeProject(name="E-Commerce API", technologies=["FastAPI", "Docker"]),
        ],
        certifications=["AWS Certified Solutions Architect"],
        years_experience=3.5,
    )
    generator = DynamicQuestionGenerator()
    categories = generator.calculate_topic_distribution(profile, num_questions=10)

    assert len(categories) == 10
    # Must contain mixture of categories
    assert "technical_skills" in categories
    assert "projects" in categories
    assert "hr_behavioral" in categories


def test_topic_distribution_without_certs_redistributes():
    profile = NormalizedResumeProfile(
        name="Bob Jones",
        skills=["Python", "Go"],
        projects=[ResumeProject(name="Task Worker", technologies=["Go"])],
        certifications=[],
        internships=[],
    )
    generator = DynamicQuestionGenerator()
    categories = generator.calculate_topic_distribution(profile, num_questions=5)

    assert len(categories) == 5
    assert "certifications_internships" not in categories


def test_dynamic_question_generation_rooted_in_resume():
    profile = NormalizedResumeProfile(
        name="Charlie",
        skills=["Python", "PostgreSQL"],
        programming_languages=["Python"],
        frameworks_and_tools=["PostgreSQL"],
        projects=[ResumeProject(name="Emergency Ambulance Routing", technologies=["Python", "PostgreSQL"])],
        years_experience=2.0,
    )
    generator = DynamicQuestionGenerator()

    # Generate question for projects
    q_proj = generator.generate_next_question(
        resume_profile=profile,
        job_title="Software Engineer",
        company_name="Acme Corp",
        previous_questions=[],
        previous_answers=[],
        difficulty="Intermediate",
        category="projects",
        order_index=1,
    )

    assert "Emergency Ambulance Routing" in q_proj["question_text"] or "project" in q_proj["question_text"].lower()
    assert "rubric_criteria" in q_proj
    assert q_proj["question_order"] == 1


def test_contextual_follow_up():
    generator = DynamicQuestionGenerator()
    orig_q = "Can you explain your ambulance routing project?"
    cand_ans = "I developed an AI application to identify suitable hospitals and optimize emergency routes by considering hospital distance and bed availability."

    follow_up = generator.generate_follow_up_question(
        original_question=orig_q,
        candidate_answer=cand_ans,
        category="Projects: Ambulance Routing",
        job_title="AI Engineer",
        difficulty="Intermediate",
    )

    assert follow_up is not None
    assert "question_text" in follow_up
    assert len(follow_up["question_text"]) > 10
