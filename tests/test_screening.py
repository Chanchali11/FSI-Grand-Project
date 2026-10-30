from src.interview.rubrics import InterviewRubrics
from src.resume.resume_schema import StructuredResume
from src.resume.skill_matcher import SkillMatcher


def test_rubrics_sum_to_100():
    tech_rubric = InterviewRubrics.TECHNICAL_RUBRIC
    assert InterviewRubrics.validate_rubric(tech_rubric) is True
    assert sum(tech_rubric.values()) == 100

    hr_rubric = InterviewRubrics.HR_RUBRIC
    assert InterviewRubrics.validate_rubric(hr_rubric) is True
    assert sum(hr_rubric.values()) == 100


def test_skill_matcher_keyword_coverage():
    req = ["Python", "FastAPI", "SQLAlchemy", "PostgreSQL", "Docker"]
    cand = ["Python", "Docker", "Git", "React"]

    score, matched, missing = SkillMatcher.calculate_keyword_coverage(req, cand)
    assert matched == ["Python", "Docker"]
    assert "FastAPI" in missing
    assert score == 40.0


def test_skill_matcher_tfidf_similarity():
    job_desc = "Seeking experienced Senior Python Backend Engineer building FastAPI microservices and PostgreSQL databases."
    resume_matching = "Senior Python engineer with extensive FastAPI and PostgreSQL microservices production experience."
    resume_unrelated = "Accountant and financial auditor specializing in balance sheets, payroll, and tax compliance."

    sim_high = SkillMatcher.calculate_tfidf_similarity(job_desc, resume_matching)
    sim_low = SkillMatcher.calculate_tfidf_similarity(job_desc, resume_unrelated)

    assert sim_high > sim_low
    assert sim_high > 20.0


def test_full_candidate_screening_evaluation():
    matcher = SkillMatcher()
    candidate = StructuredResume(
        name="Alex Vance",
        email="alex.vance@example.com",
        technical_skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        total_years_experience=5.0,
        skill_evidence={"Python": "5 years building microservices", "Docker": "containerized backends"},
    )

    eval_result = matcher.evaluate_candidate_for_job(
        job_title="Senior Python Backend Engineer",
        job_description="Python, FastAPI, PostgreSQL, Docker, Microservices.",
        required_skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        preferred_skills=["Redis", "Kafka"],
        mandatory_qualifications=["4+ years backend", "Proficiency in Python"],
        min_years_experience=4.0,
        structured_resume=candidate,
        raw_resume_text="Senior Python Backend Engineer with 5 years experience in FastAPI, PostgreSQL, and Docker.",
        shortlist_threshold=70.0,
    )

    assert eval_result.overall_score >= 70.0
    assert eval_result.recommendation == "Meets Configured Criteria"
    assert "Python" in eval_result.matched_skills
    assert eval_result.mandatory_criteria_passed is True


def test_hybrid_five_factor_screening_weights():
    """Verify configurable hybrid screening weights (Required 35%, Experience 25%, Similarity 20%, Preferred 10%, Qualifications 10%)."""
    matcher = SkillMatcher()
    candidate = StructuredResume(
        name="Jordan Lee",
        email="jordan.lee@example.com",
        technical_skills=["Python", "PostgreSQL", "Docker", "Kafka"],  # Has 2 of 3 required, 1 of 2 preferred
        total_years_experience=6.0,
        skill_evidence={"Python": "6 years experience", "Docker": "CI/CD pipelines"},
    )

    eval_result = matcher.evaluate_candidate_for_job(
        job_title="Backend Architect",
        job_description="Seeking a Backend Architect with Python, FastAPI, and PostgreSQL experience building Kafka streaming.",
        required_skills=["Python", "FastAPI", "PostgreSQL"],  # 2/3 matched = 66.7%
        preferred_skills=["Kafka", "Redis"],                  # 1/2 matched = 50.0%
        mandatory_qualifications=["Minimum 4 years backend", "Proficiency in Python"],
        min_years_experience=4.0,
        structured_resume=candidate,
        raw_resume_text="Backend Architect with 6 years experience specializing in Python, PostgreSQL, and Kafka pipelines.",
        weight_keywords=0.35,          # 35% Required skills
        weight_experience=0.25,        # 25% Experience
        weight_similarity=0.20,        # 20% Job similarity
        weight_preferred_skills=0.10,  # 10% Preferred skills
        weight_qualifications=0.10,    # 10% Qualifications
        shortlist_threshold=70.0,
    )

    assert eval_result.overall_score > 60.0
    assert eval_result.mandatory_criteria_passed is True
    assert "Python" in eval_result.matched_skills
    assert "FastAPI" in eval_result.missing_skills

