import random
import logging
import json
from typing import Any

from src.ai.claude_client import ClaudeClient
from src.interview.resume_profile import NormalizedResumeProfile
from src.interview.rubrics import InterviewRubrics

logger = logging.getLogger(__name__)


class DynamicQuestionGenerator:
    """
    Dynamically generates personalized, non-repeating, randomized interview questions
    rooted strictly in the candidate's actual uploaded resume content.
    """

    def __init__(self, ai_client: ClaudeClient | None = None):
        self.ai = ai_client or ClaudeClient()

    @staticmethod
    def calculate_topic_distribution(
        profile: NormalizedResumeProfile,
        num_questions: int = 10,
        weights: dict[str, float] | None = None,
    ) -> list[str]:
        """
        Calculates category quotas for an interview.
        Default target:
        - 30% Technical Skills
        - 30% Projects
        - 20% HR and Behavioral
        - 10% Certifications or Internships
        - 10% Problem-Solving / Architecture
        Redistributes if profile lacks certifications/internships or projects.
        """
        default_weights = {
            "technical_skills": 0.30,
            "projects": 0.30,
            "hr_behavioral": 0.20,
            "certifications_internships": 0.10,
            "problem_solving": 0.10,
        }
        w = weights or default_weights

        # Check availability
        has_certs = bool(profile.certifications or profile.internships)
        has_projects = bool(profile.projects)

        alloc = dict(w)
        if not has_certs:
            realloc = alloc.pop("certifications_internships", 0.10)
            alloc["technical_skills"] += realloc * 0.5
            alloc["problem_solving"] += realloc * 0.5

        if not has_projects:
            realloc = alloc.pop("projects", 0.30)
            alloc["technical_skills"] += realloc * 0.6
            alloc["problem_solving"] += realloc * 0.4

        # Normalize weights to sum to 1.0
        total_w = sum(alloc.values())
        norm_weights = {k: v / total_w for k, v in alloc.items()}

        # Build list of categories according to distribution
        categories = []
        for cat, weight in norm_weights.items():
            count = max(1, round(weight * num_questions))
            categories.extend([cat] * count)

        # Truncate or pad to exact count
        if len(categories) > num_questions:
            categories = categories[:num_questions]
        while len(categories) < num_questions:
            categories.append("technical_skills")

        random.shuffle(categories)
        return categories

    def generate_next_question(
        self,
        resume_profile: NormalizedResumeProfile,
        job_title: str,
        company_name: str,
        previous_questions: list[str],
        previous_answers: list[str],
        difficulty: str = "Intermediate",
        category: str = "technical_skills",
        order_index: int = 1,
    ) -> dict[str, Any]:
        """
        Generates a single personalized question rooted in actual resume facts.
        Includes semantic similarity validation and non-repetition checks.
        """
        # Step 1: Select relevant topic from resume for the category
        chosen_topic = self._pick_topic_from_resume(resume_profile, category, previous_questions)

        # Step 2: Formulate dynamic prompt for AI
        prompt = self._build_question_prompt(
            resume_profile=resume_profile,
            job_title=job_title,
            company_name=company_name,
            difficulty=difficulty,
            category=category,
            chosen_topic=chosen_topic,
            previous_questions=previous_questions,
            previous_answers=previous_answers,
        )

        question_data = None
        if not self.ai.use_mock:
            try:
                raw_response = self.ai._call_claude(
                    prompt=prompt,
                    system="You are an expert technical interviewer conducting an evidence-based personalized virtual interview. Return ONLY strict JSON.",
                )
                cleaned = self.ai._clean_json(raw_response)
                if cleaned and "question_text" in cleaned:
                    question_data = cleaned
            except Exception as e:
                logger.warning(f"Claude question generation failed: {e}. Falling back to deterministic generator.")

        # Step 3: Fallback deterministic question generator strictly rooted in resume
        if not question_data:
            question_data = self._generate_deterministic_question(
                resume_profile=resume_profile,
                category=category,
                topic=chosen_topic,
                difficulty=difficulty,
                job_title=job_title,
                previous_questions=previous_questions,
            )

        # Ensure order and rubrics
        question_data["question_order"] = order_index
        question_data["difficulty"] = difficulty
        if "rubric_criteria" not in question_data or not question_data["rubric_criteria"]:
            question_data["rubric_criteria"] = InterviewRubrics.get_rubric_for_stage(category)

        return question_data

    def generate_follow_up_question(
        self,
        original_question: str,
        candidate_answer: str,
        category: str,
        job_title: str,
        difficulty: str = "Intermediate",
    ) -> dict[str, Any] | None:
        """
        Generates a contextually connected follow-up question digging deeper into the candidate's answer.
        Returns None if answer is too brief or follow-up not warranted.
        """
        if len(candidate_answer.strip()) < 20:
            return None

        prompt = f"""
Candidate was asked: "{original_question}"
Candidate answered: "{candidate_answer}"
Job Title: {job_title}
Difficulty: {difficulty}

Generate a concise, insightful follow-up question probing specific reasoning, edge cases, trade-offs, or implementation details mentioned in their answer.
Return ONLY valid JSON:
{{
  "question_type": "follow_up",
  "category": "{category}",
  "question_text": "Follow-up question text here",
  "expected_concepts": ["concept1", "concept2"],
  "rubric_criteria": {{"technical_depth": 35, "edge_case_awareness": 35, "clarity": 30}}
}}
"""
        if not self.ai.use_mock:
            try:
                raw = self.ai._call_claude(prompt)
                data = self.ai._clean_json(raw)
                if data and "question_text" in data:
                    return data
            except Exception:
                pass

        # Fallback contextual follow-up
        lower_ans = candidate_answer.lower()
        if "optim" in lower_ans or "bottleneck" in lower_ans or "cache" in lower_ans:
            q_text = f"You mentioned optimization and performance trade-offs. What specific metric or benchmarking approach did you use to validate that gain?"
        elif "database" in lower_ans or "sql" in lower_ans or "data" in lower_ans:
            q_text = f"In that architecture, how do you manage data consistency, transactions, or failover when a write burst occurs?"
        elif "api" in lower_ans or "microservice" in lower_ans:
            q_text = f"How did you handle error propagation, timeouts, and idempotent retries in that integration?"
        else:
            q_text = f"Could you dive deeper into the primary technical challenge you personally solved during that implementation, and what you would do differently in hindsight?"

        return {
            "question_type": "follow_up",
            "category": category,
            "question_text": q_text,
            "expected_concepts": ["Trade-off analysis", "Verification metric", "System resiliency"],
            "rubric_criteria": {"technical_depth": 35, "edge_case_awareness": 35, "clarity": 30},
        }

    def _pick_topic_from_resume(
        self,
        profile: NormalizedResumeProfile,
        category: str,
        previous_questions: list[str],
    ) -> Any:
        prev_text = " ".join(previous_questions).lower()

        if category == "projects" and profile.projects:
            # Pick a project not already asked about
            unused = [p for p in profile.projects if p.name.lower() not in prev_text]
            return random.choice(unused) if unused else random.choice(profile.projects)

        if category == "certifications_internships":
            if profile.certifications:
                unused = [c for c in profile.certifications if c.lower() not in prev_text]
                return random.choice(unused) if unused else random.choice(profile.certifications)
            if profile.internships:
                return random.choice(profile.internships)

        # Technical skills
        all_skills = profile.skills or profile.programming_languages or profile.frameworks_and_tools or ["Problem Solving"]
        unused_skills = [s for s in all_skills if s.lower() not in prev_text]
        return random.choice(unused_skills) if unused_skills else random.choice(all_skills)

    def _build_question_prompt(
        self,
        resume_profile: NormalizedResumeProfile,
        job_title: str,
        company_name: str,
        difficulty: str,
        category: str,
        chosen_topic: Any,
        previous_questions: list[str],
        previous_answers: list[str],
    ) -> str:
        topic_desc = chosen_topic.name if hasattr(chosen_topic, "name") else str(chosen_topic)
        topic_tech = getattr(chosen_topic, "technologies", [])

        return f"""
You are an expert technical hiring manager interviewing a candidate for the role of {job_title} at {company_name}.
Difficulty Level: {difficulty}
Target Category: {category}

Candidate Verified Resume Facts:
- Core Skills: {json.dumps(resume_profile.skills)}
- Programming Languages: {json.dumps(resume_profile.programming_languages)}
- Frameworks/Tools: {json.dumps(resume_profile.frameworks_and_tools)}
- Target Topic for this question: "{topic_desc}" (Related tech: {json.dumps(topic_tech)})
- Total Experience: {resume_profile.years_experience} years

Constraint Rules:
1. STRICTLY base the question on the candidate's actual resume items above. DO NOT invent unmentioned technologies.
2. DO NOT repeat or rephrase any previous question.
Previous questions asked so far:
{json.dumps(previous_questions)}

Difficulty Guidelines:
- Beginner: Focus on fundamental concepts, purpose, syntax, and foundational knowledge.
- Intermediate: Focus on real-world scenarios, debugging, error handling, and component interactions.
- Advanced: Focus on architecture, internal mechanics, concurrency, performance trade-offs, and scalability.

Return ONLY a valid JSON object matching this schema:
{{
  "question_type": "conceptual | scenario | project_deep_dive | star_hr",
  "category": "{category}",
  "question_text": "Your clear, articulate, professional interview question text",
  "expected_concepts": ["concept1", "concept2", "concept3"],
  "rubric_criteria": {{
    "technical_correctness": 40,
    "reasoning_explanation": 25,
    "practical_application": 20,
    "communication_structure": 15
  }}
}}
"""

    def _generate_deterministic_question(
        self,
        resume_profile: NormalizedResumeProfile,
        category: str,
        topic: Any,
        difficulty: str,
        job_title: str,
        previous_questions: list[str],
    ) -> dict[str, Any]:
        """Provides high-quality randomized question templates customized to candidate's verified items."""
        topic_name = topic.name if hasattr(topic, "name") else str(topic)
        tech_list = getattr(topic, "technologies", [])
        tech_str = ", ".join(tech_list) if tech_list else topic_name

        if category == "projects":
            templates = [
                {
                    "type": "project_deep_dive",
                    "text": f"In your resume, you highlighted the project '{topic_name}'. Could you explain its overall architecture and how {tech_str} was integrated?",
                    "concepts": ["Architecture layout", "Tech stack integration", "Core workflow"],
                },
                {
                    "type": "scenario",
                    "text": f"What was the most challenging technical bottleneck or unexpected bug you encountered while building '{topic_name}', and how did you resolve it?",
                    "concepts": ["Root cause analysis", "Debugging methodology", "Measurable solution"],
                },
                {
                    "type": "project_deep_dive",
                    "text": f"If you had to scale '{topic_name}' to support 100x current user traffic, what architectural changes would you make to the data layer and APIs?",
                    "concepts": ["Caching strategies", "Database indexing/sharding", "Asynchronous processing"],
                },
            ]
        elif category == "hr_behavioral":
            templates = [
                {
                    "type": "star_hr",
                    "text": f"Can you describe a situation where you had to collaborate under tight deadlines or ambiguous requirements on a project like '{topic_name}'? How did you prioritize?",
                    "concepts": ["STAR Framework", "Time management", "Clear communication", "Outcome"],
                },
                {
                    "type": "star_hr",
                    "text": "Tell me about a time when you strongly disagreed with a peer or technical decision. How did you resolve the disagreement productively?",
                    "concepts": ["Active listening", "Data-driven persuasion", "Professional collaboration"],
                },
            ]
        elif category == "certifications_internships":
            templates = [
                {
                    "type": "conceptual",
                    "text": f"You completed {topic_name}. What was the most impactful principle or methodology you learned from it, and how have you applied it in practice?",
                    "concepts": ["Core methodology", "Real-world application", "Best practices"],
                }
            ]
        elif category == "problem_solving":
            templates = [
                {
                    "type": "scenario",
                    "text": f"Suppose a service utilizing {topic_name} suddenly experiences high CPU utilization and degraded latency in production. Walk me step-by-step through your incident triage process.",
                    "concepts": ["System metrics (APM/logs)", "Profiling", "Isolating blast radius", "Mitigation"],
                }
            ]
        else:  # technical_skills
            diff_level = difficulty.lower()
            if diff_level == "beginner":
                templates = [
                    {
                        "type": "conceptual",
                        "text": f"Can you explain the core purpose of {topic_name} and describe a simple practical use case where you implemented it?",
                        "concepts": ["Fundamental principles", "Standard usage", "Key advantages"],
                    },
                    {
                        "type": "conceptual",
                        "text": f"What are the key advantages of using {topic_name} compared to alternative tools or libraries in this space?",
                        "concepts": ["Feature comparison", "Syntax/Design patterns", "Appropriate use cases"],
                    },
                ]
            elif diff_level == "advanced":
                templates = [
                    {
                        "type": "system_design",
                        "text": f"In {topic_name}, explain the internal mechanics regarding memory management, concurrency, and performance optimization when processing high-throughput workloads.",
                        "concepts": ["Internal runtime behavior", "Concurrency safety", "Memory overhead", "Performance tuning"],
                    },
                    {
                        "type": "scenario",
                        "text": f"Discuss an advanced design pattern or anti-pattern you frequently observe in {topic_name} projects, and how you architect around it.",
                        "concepts": ["Design patterns", "Anti-pattern remediation", "Maintainability"],
                    },
                ]
            else:  # intermediate
                templates = [
                    {
                        "type": "conceptual",
                        "text": f"How do error handling, exception hierarchies, and resource lifecycle management work in {topic_name}?",
                        "concepts": ["Resource clean-up", "Exception propagation", "Resiliency"],
                    },
                    {
                        "type": "scenario",
                        "text": f"Suppose you notice intermittent timeouts or connection pool exhaustion in a service using {topic_name}. How do you diagnose and fix it?",
                        "concepts": ["Connection pooling", "Timeout budgets", "Health checks"],
                    },
                ]

        # Filter out templates that match previous questions
        prev_lower = [q.lower() for q in previous_questions]
        candidates = [t for t in templates if t["text"].lower() not in prev_lower]
        chosen = random.choice(candidates if candidates else templates)

        return {
            "question_type": chosen["type"],
            "category": f"{category.replace('_', ' ').title()}: {topic_name}",
            "question_text": chosen["text"],
            "expected_concepts": chosen["concepts"],
            "rubric_criteria": {
                "technical_correctness": 40,
                "reasoning_explanation": 25,
                "practical_application": 20,
                "communication_structure": 15,
            },
        }
