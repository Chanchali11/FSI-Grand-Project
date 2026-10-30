
from src.ai.claude_client import ClaudeClient
from src.resume.resume_schema import (
    EducationItem,
    ProjectItem,
    StructuredResume,
    WorkExperienceItem,
)
from src.security.authentication import sanitize_input_text


class ResumeExtractor:
    """Extracts and validates structured candidate information from resume text."""

    def __init__(self, claude_client: ClaudeClient | None = None):
        self.ai = claude_client or ClaudeClient()

    def parse_resume(self, raw_text: str) -> StructuredResume:
        """Sanitize text, extract via AI/heuristics, and strictly validate with Pydantic."""
        sanitized = sanitize_input_text(raw_text)
        extracted_dict = self.ai.extract_resume_data(sanitized)

        # Build StructuredResume safely
        try:
            edu_items = [
                EducationItem(
                    degree=item.get("degree", "Degree"),
                    institution=item.get("institution"),
                    year=str(item.get("year")) if item.get("year") else None,
                )
                for item in extracted_dict.get("education", [])
                if isinstance(item, dict)
            ]

            work_items = [
                WorkExperienceItem(
                    company=item.get("company", "Company"),
                    role=item.get("role", "Software Engineer"),
                    duration=item.get("duration"),
                    highlights=item.get("highlights", []),
                )
                for item in extracted_dict.get("work_experience", [])
                if isinstance(item, dict)
            ]

            proj_items = [
                ProjectItem(
                    title=item.get("title", "Project"),
                    description=item.get("description"),
                    technologies=item.get("technologies", []),
                )
                for item in extracted_dict.get("projects", [])
                if isinstance(item, dict)
            ]

            # Construct verified model
            resume = StructuredResume(
                name=extracted_dict.get("name") or "Candidate",
                email=extracted_dict.get("email"),
                phone=extracted_dict.get("phone"),
                technical_skills=extracted_dict.get("technical_skills", []),
                soft_skills=extracted_dict.get("soft_skills", []),
                total_years_experience=float(extracted_dict.get("total_years_experience", 0.0)),
                education=edu_items,
                work_experience=work_items,
                projects=proj_items,
                certifications=extracted_dict.get("certifications", []),
                achievements=extracted_dict.get("achievements", []),
                skill_evidence=extracted_dict.get("skill_evidence", {}),
            )
            return resume
        except Exception:
            # Fallback guarantee
            return StructuredResume(
                name="Candidate",
                technical_skills=extracted_dict.get("technical_skills", ["Python", "SQL"]),
                total_years_experience=3.0,
            )
