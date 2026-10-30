from pydantic import BaseModel, Field


class EducationItem(BaseModel):
    degree: str = "Degree"
    institution: str | None = None
    year: str | None = None


class WorkExperienceItem(BaseModel):
    company: str = "Company"
    role: str = "Software Engineer"
    duration: str | None = None
    highlights: list[str] = Field(default_factory=list)


class ProjectItem(BaseModel):
    title: str = "Project"
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)


class StructuredResume(BaseModel):
    name: str | None = "Candidate"
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None

    technical_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    total_years_experience: float = 0.0

    education: list[EducationItem] = Field(default_factory=list)
    work_experience: list[WorkExperienceItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)

    # Traceable evidence snippets
    skill_evidence: dict[str, str] = Field(default_factory=dict)


class MandatoryCriterionCheck(BaseModel):
    criterion: str
    status: str  # "Passed", "Failed", "Unclear"
    evidence: str


class ScreeningEvaluation(BaseModel):
    overall_score: float = Field(ge=0.0, le=100.0)
    keyword_coverage_score: float = Field(ge=0.0, le=100.0)
    text_similarity_score: float = Field(ge=0.0, le=100.0)
    experience_score: float = Field(ge=0.0, le=100.0)
    semantic_score: float = Field(ge=0.0, le=100.0)

    mandatory_criteria_passed: bool = True
    mandatory_evaluations: list[MandatoryCriterionCheck] = Field(default_factory=list)

    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    unclear_evidence: list[str] = Field(default_factory=list)
    evidence_excerpts: dict[str, str] = Field(default_factory=dict)

    recommendation: str  # "Meets Configured Criteria", "Needs Manual Review", "Does Not Meet Configured Criteria"
    recommendation_notes: str = ""
