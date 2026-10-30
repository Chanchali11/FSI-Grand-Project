"""Prompt templates for Claude AI structured extraction, screening, and interview evaluation."""

PROMPT_JOB_REQUIREMENT_EXTRACTION = """
You are an expert technical recruiter and talent architect.
Analyze the following job description and extract structured recruitment criteria.
Return ONLY a valid JSON object matching the requested schema without any markdown formatting, preamble, or conversational commentary.

Job Title: {job_title}
Job Description:
{job_description}

Schema expected:
{{
  "required_skills": ["skill1", "skill2", ...],
  "preferred_skills": ["skill1", "skill2", ...],
  "mandatory_qualifications": ["qualification1", ...],
  "education_requirements": "Degree level or equivalent",
  "min_years_experience": 3.0,
  "technical_subjects": ["topic1", "topic2", ...]
}}
"""

PROMPT_RESUME_EXTRACTION = """
You are an unbiased AI document parser for technical recruitment.
Extract structured information from the following resume text.
Rules:
1. Extract candidate name, contact info, skills, education, work experience, projects, and certifications.
2. DO NOT extract or infer protected demographic attributes (age, gender, ethnicity, religion, marital status).
3. For each extracted key skill, provide a short quote or excerpt from the resume demonstrating evidence.
4. If a field is absent, leave it empty. NEVER invent or hallucinate information.
5. Return ONLY a valid JSON object matching this schema:

{{
  "name": "Candidate Full Name or None",
  "email": "candidate@example.com or None",
  "phone": "+1-555-0199 or None",
  "technical_skills": ["Python", "Docker", ...],
  "soft_skills": ["Leadership", "Communication", ...],
  "total_years_experience": 4.5,
  "education": [
    {{"degree": "B.S. Computer Science", "institution": "State University", "year": "2020"}}
  ],
  "work_experience": [
    {{"company": "Tech Corp", "role": "Software Engineer", "duration": "2 years", "highlights": ["Built microservices"]}}
  ],
  "projects": [
    {{"title": "Real-time Chat", "description": "Built WebSockets chat in Go and Redis", "technologies": ["Go", "Redis"]}}
  ],
  "certifications": ["AWS Solutions Architect"],
  "skill_evidence": {{
    "Python": "Built Python automation pipelines for data extraction",
    "Docker": "Containerized multi-service web backend"
  }}
}}

Resume text:
{resume_text}
"""

PROMPT_SEMANTIC_MATCHING = """
You are an objective recruitment screening engine.
Compare the candidate's structured profile against the specified job requirements.

Job Title: {job_title}
Job Required Skills: {required_skills}
Job Preferred Skills: {preferred_skills}
Mandatory Qualifications: {mandatory_qualifications}

Candidate Extracted Profile:
- Skills: {candidate_skills}
- Experience: {candidate_experience} years
- Work History: {candidate_work}
- Projects: {candidate_projects}

Evaluate:
1. Matched skills with supporting resume evidence quotes.
2. Missing or weakly evidenced skills.
3. Mandatory qualifications check (Pass / Fail / Unclear).
4. Qualitative semantic relevance score from 0 to 100.
5. Recommendation: "Meets Configured Criteria", "Needs Manual Review", or "Does Not Meet Configured Criteria".

Return ONLY a valid JSON object:
{{
  "semantic_score": 85.0,
  "mandatory_passed": true,
  "mandatory_evaluations": [
    {{"criterion": "4+ years backend", "status": "Passed", "evidence": "Has 5 years total experience"}}
  ],
  "matched_skills": ["Python", "SQLAlchemy"],
  "missing_skills": ["Kafka"],
  "unclear_evidence": ["Kubernetes"],
  "evidence_excerpts": {{
    "Python": "5 years building Python applications"
  }},
  "recommendation": "Meets Configured Criteria",
  "rationale": "Strong candidate with comprehensive backend experience."
}}
"""

PROMPT_GENERATE_INTERVIEW_QUESTIONS = """
You are a senior technical interviewer and hiring bar raiser for {company_name}.
Generate {num_questions} targeted, job-specific interview questions for the role: {job_title}.
Interview Type: {interview_type} (Technical or HR).

Job Requirements:
{job_requirements}

Candidate Background (for tailoring):
- Skills: {candidate_skills}
- Projects: {candidate_projects}

Question guidelines:
- For Technical: mix conceptual, real-world scenario/architecture, debugging/coding reasoning, and project deep-dive questions.
- For HR: apply the STAR framework (Situation, Task, Action, Result) covering teamwork, leadership, deadline pressure, and culture.
- Each question must specify the expected core concepts and rubric criteria.

Return ONLY a valid JSON array of questions:
[
  {{
    "question_order": 1,
    "question_type": "conceptual",
    "category": "Python Architecture",
    "question_text": "Explain the difference between threading, multiprocessing, and asyncio in Python, and describe when you would choose each in a high-scale service.",
    "expected_concepts": ["GIL", "CPU-bound vs I/O-bound", "Event loop", "Memory overhead"],
    "rubric_criteria": {{
      "technical_correctness": 40,
      "reasoning_explanation": 25,
      "practical_application": 20,
      "communication_structure": 15
    }}
  }}
]
"""

PROMPT_EVALUATE_INTERVIEW_ANSWER = """
You are an objective AI interview evaluator.
Evaluate the candidate's submitted answer against the question and expected concepts.

Role: {job_title}
Interview Category: {interview_stage}
Question: {question_text}
Expected Concepts: {expected_concepts}
Rubric Weightings: {rubric_criteria}

Candidate Answer:
\"\"\"{candidate_answer}\"\"\"

Instructions:
1. Assess correctness, reasoning, practical depth, and clarity without penalizing accent, minor phrasing variations, or brevity if precise.
2. Award a score between 0 and 100 based on the rubric criteria.
3. Identify which expected concepts were demonstrated and which were omitted.
4. Provide constructive feedback and formulate a targeted follow-up question.

Return ONLY a valid JSON object:
{{
  "score": 82.0,
  "rubric_scores": {{
    "technical_correctness": 34.0,
    "reasoning_explanation": 22.0,
    "practical_application": 16.0,
    "communication_structure": 10.0
  }},
  "correct_concepts": ["Identified GIL constraints", "Distinguished CPU vs I/O bound"],
  "missing_concepts": ["Did not mention uvloop or event loop mechanics"],
  "feedback": "Strong foundational grasp of Python concurrency. Good distinction between multiprocessing and threading.",
  "improvement_suggestions": ["Mention specific async event loops and task starvation scenarios."],
  "follow_up_question": "How would you handle a blocking database call inside an asyncio worker without freezing the event loop?"
}}
"""
