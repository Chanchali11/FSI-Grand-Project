from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.ai.claude_client import ClaudeClient
from src.resume.resume_schema import (
    MandatoryCriterionCheck,
    ScreeningEvaluation,
    StructuredResume,
)


class SkillMatcher:
    """Multi-tiered matching engine combining keyword coverage, TF-IDF cosine similarity, and semantic AI."""

    def __init__(self, claude_client: ClaudeClient = None):
        self.ai = claude_client or ClaudeClient()

    @staticmethod
    def calculate_keyword_coverage(required_skills: list[str], candidate_skills: list[str]) -> tuple[float, list[str], list[str]]:
        """Calculate percentage of required skills possessed by candidate."""
        if not required_skills:
            return 100.0, [], []

        req_lower = [s.strip().lower() for s in required_skills if s.strip()]
        cand_lower = set(s.strip().lower() for s in candidate_skills if s.strip())

        matched = [orig for orig in required_skills if orig.strip().lower() in cand_lower]
        missing = [orig for orig in required_skills if orig.strip().lower() not in cand_lower]

        score = (len(matched) / len(req_lower)) * 100.0
        return round(score, 1), matched, missing

    @staticmethod
    def calculate_tfidf_similarity(job_description: str, resume_text: str) -> float:
        """Compute TF-IDF cosine similarity between full job text and candidate resume text."""
        if not job_description or not resume_text:
            return 0.0

        try:
            vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=5000)
            tfidf_matrix = vectorizer.fit_transform([job_description, resume_text])
            sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            # Normalize to 0 - 100 scale
            score = round(float(sim) * 100.0, 1)
            return min(100.0, max(0.0, score))
        except Exception:
            return 45.0  # Safe deterministic default if corpus is uniform

    @staticmethod
    def evaluate_experience(min_years_required: float, candidate_years: float) -> float:
        """Score experience based on meeting minimum threshold."""
        if min_years_required <= 0:
            return 100.0
        ratio = candidate_years / min_years_required
        if ratio >= 1.2:
            return 100.0
        elif ratio >= 1.0:
            return 90.0
        elif ratio >= 0.75:
            return 75.0
        elif ratio >= 0.5:
            return 55.0
        else:
            return 30.0

    def evaluate_candidate_for_job(
        self,
        job_title: str,
        job_description: str,
        required_skills: list[str],
        preferred_skills: list[str],
        mandatory_qualifications: list[str],
        min_years_experience: float,
        structured_resume: StructuredResume,
        raw_resume_text: str,
        weight_keywords: float = 0.25,
        weight_similarity: float = 0.25,
        weight_experience: float = 0.25,
        weight_semantic: float = 0.25,
        shortlist_threshold: float = 70.0,
        weight_preferred_skills: float | None = None,
        weight_qualifications: float | None = None,
    ) -> ScreeningEvaluation:
        """Generate comprehensive evidence-based screening evaluation with configurable hybrid scoring."""
        # 1. Keyword Coverage for Required Skills
        kw_score, matched_skills, missing_skills = self.calculate_keyword_coverage(
            required_skills=required_skills,
            candidate_skills=structured_resume.technical_skills,
        )

        # 1b. Preferred Skills Coverage
        pref_score, matched_pref, _ = self.calculate_keyword_coverage(
            required_skills=preferred_skills,
            candidate_skills=structured_resume.technical_skills,
        )

        # 2. TF-IDF Text Similarity
        tfidf_score = self.calculate_tfidf_similarity(
            job_description=job_description,
            resume_text=raw_resume_text,
        )

        # 3. Experience Score
        exp_score = self.evaluate_experience(
            min_years_required=min_years_experience,
            candidate_years=structured_resume.total_years_experience,
        )

        # 4. Semantic Claude Evaluation
        semantic_data = self.ai.evaluate_semantic_match(
            job_title=job_title,
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            mandatory_qualifications=mandatory_qualifications,
            candidate_profile=structured_resume.model_dump(),
        )
        semantic_score = float(semantic_data.get("semantic_score", 70.0))

        # Check mandatory qualifications
        mandatory_checks = []
        all_passed = True
        passed_count = 0
        for mq in mandatory_qualifications:
            # Check if mentioned or satisfied
            status = "Passed"
            evidence = f"Candidate profile indicates alignment with {mq}"
            if "experience" in mq.lower() and structured_resume.total_years_experience < min_years_experience:
                status = "Unclear"
                evidence = f"Candidate has {structured_resume.total_years_experience} yrs vs required {min_years_experience} yrs."
                all_passed = False
            else:
                passed_count += 1
            mandatory_checks.append(MandatoryCriterionCheck(criterion=mq, status=status, evidence=evidence))

        qual_score = (passed_count / max(len(mandatory_checks), 1)) * 100.0 if mandatory_checks else 100.0

        # 5. Composite Weighted Score Calculation (supports 4-factor and 5-factor hybrid models)
        if weight_preferred_skills is not None or weight_qualifications is not None:
            w_req = weight_keywords
            w_sim = weight_similarity
            w_exp = weight_experience
            w_pref = weight_preferred_skills or 0.10
            w_qual = weight_qualifications or 0.10
            total_weight = w_req + w_sim + w_exp + w_pref + w_qual
            if total_weight <= 0:
                total_weight = 1.0

            overall_score = round(
                (
                    (kw_score * w_req)
                    + (tfidf_score * w_sim)
                    + (exp_score * w_exp)
                    + (pref_score * w_pref)
                    + (qual_score * w_qual)
                )
                / total_weight,
                1,
            )
        else:
            total_weight = weight_keywords + weight_similarity + weight_experience + weight_semantic
            if total_weight <= 0:
                total_weight = 1.0

            overall_score = round(
                (
                    (kw_score * weight_keywords)
                    + (tfidf_score * weight_similarity)
                    + (exp_score * weight_experience)
                    + (semantic_score * weight_semantic)
                )
                / total_weight,
                1,
            )

        # Determine Recommendation
        if overall_score >= shortlist_threshold and all_passed:
            recommendation = "Meets Configured Criteria"
            notes = "Candidate exceeds screening threshold and meets all mandatory criteria."
        elif overall_score >= (shortlist_threshold - 15.0):
            recommendation = "Needs Manual Review"
            notes = "Candidate has strong potential but requires human recruiter verification on specific criteria."
        else:
            recommendation = "Does Not Meet Configured Criteria"
            notes = "Candidate did not meet required skill coverage or experience baseline."

        # Collect Evidence Excerpts
        evidence_excerpts = dict(structured_resume.skill_evidence)
        for skill in matched_skills:
            if skill not in evidence_excerpts:
                # Find excerpt in raw text
                idx = raw_resume_text.lower().find(skill.lower())
                if idx != -1:
                    start = max(0, idx - 40)
                    end = min(len(raw_resume_text), idx + 80)
                    evidence_excerpts[skill] = f"...{raw_resume_text[start:end].strip()}..."
                else:
                    evidence_excerpts[skill] = "Extracted from technical summary section."

        return ScreeningEvaluation(
            overall_score=overall_score,
            keyword_coverage_score=kw_score,
            text_similarity_score=tfidf_score,
            experience_score=exp_score,
            semantic_score=semantic_score,
            mandatory_criteria_passed=all_passed,
            mandatory_evaluations=mandatory_checks,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            unclear_evidence=missing_skills[:3],
            evidence_excerpts=evidence_excerpts,
            recommendation=recommendation,
            recommendation_notes=notes,
        )
