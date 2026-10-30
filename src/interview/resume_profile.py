from typing import Any
from pydantic import BaseModel, Field


class ResumeProject(BaseModel):
    name: str = "Project"
    technologies: list[str] = Field(default_factory=list)
    description: str | None = None
    role: str | None = None
    challenges: list[str] = Field(default_factory=list)


class ResumeWorkExperience(BaseModel):
    company: str = "Company"
    role: str = "Software Engineer"
    duration: str | None = None
    highlights: list[str] = Field(default_factory=list)


class ResumeEducation(BaseModel):
    degree: str = "Degree"
    institution: str | None = None
    year: str | None = None


class NormalizedResumeProfile(BaseModel):
    """Normalized structured profile strictly reflecting extracted candidate resume content."""
    name: str = "Candidate"
    email: str | None = None
    phone: str | None = None
    education: list[ResumeEducation] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    programming_languages: list[str] = Field(default_factory=list)
    frameworks_and_tools: list[str] = Field(default_factory=list)
    projects: list[ResumeProject] = Field(default_factory=list)
    internships: list[str] = Field(default_factory=list)
    work_experience: list[ResumeWorkExperience] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    years_experience: float = 0.0

    def get_available_topics(self) -> dict[str, list[Any]]:
        """Return available non-empty topic collections strictly based on actual resume data."""
        topics = {}
        all_skills = list(dict.fromkeys(self.skills + self.programming_languages + self.frameworks_and_tools))
        if all_skills:
            topics["skills"] = all_skills
        if self.projects:
            topics["projects"] = self.projects
        if self.work_experience:
            topics["experience"] = self.work_experience
        if self.certifications:
            topics["certifications"] = self.certifications
        if self.internships:
            topics["internships"] = self.internships
        if self.achievements:
            topics["achievements"] = self.achievements
        return topics
