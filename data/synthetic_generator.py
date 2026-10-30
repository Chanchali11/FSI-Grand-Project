import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import random
from typing import List

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from config import SYNTHETIC_DIR

RESUMES_DIR = SYNTHETIC_DIR / "resumes"
JOBS_DIR = SYNTHETIC_DIR / "job_descriptions"

for d in [RESUMES_DIR, JOBS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


SYNTHETIC_JOBS = [
    {
        "id": "job-python-backend",
        "title": "Senior Python Backend Engineer",
        "department": "Core Platform",
        "location": "Remote",
        "experience_level": "Senior",
        "min_years_experience": 4.0,
        "description": (
            "Seeking an experienced Senior Python Backend Engineer to architect, build, and maintain "
            "distributed microservices using FastAPI, SQLAlchemy, and PostgreSQL. You will design "
            "asynchronous messaging pipelines with Kafka and Redis, implement robust CI/CD, and "
            "mentor engineering team members."
        ),
        "required_skills": ["Python", "FastAPI", "SQLAlchemy", "PostgreSQL", "Docker", "REST APIs"],
        "preferred_skills": ["Kafka", "Redis", "Kubernetes", "AWS", "Pytest", "Microservices"],
        "mandatory_qualifications": ["4+ years backend development", "Proficiency in Python"],
        "technical_subjects": ["Python Concurrency", "Database Architecture", "System Design", "Distributed Systems"],
    },
    {
        "id": "job-ai-engineer",
        "title": "Full-Stack AI & Machine Learning Engineer",
        "department": "Applied AI",
        "location": "San Francisco, CA / Hybrid",
        "experience_level": "Mid-Senior",
        "min_years_experience": 3.0,
        "description": (
            "We are hiring a Full-Stack AI Engineer to develop generative AI applications, integrate "
            "LLMs via Anthropic and OpenAI APIs, and build scalable React/TypeScript frontends. "
            "Experience with LangChain, Vector Databases (Pinecone/Chroma), and PyTorch is required."
        ),
        "required_skills": ["Python", "Machine Learning", "PyTorch", "TypeScript", "React", "REST APIs"],
        "preferred_skills": ["LangChain", "Vector Databases", "Docker", "GCP", "FastAPI", "NLP"],
        "mandatory_qualifications": ["3+ years AI/ML software engineering", "Experience deploying LLMs in production"],
        "technical_subjects": ["Transformers & LLM Architectures", "Prompt Engineering", "Frontend State Management", "Model Serving"],
    },
    {
        "id": "job-devops-architect",
        "title": "Cloud DevOps & Platform Architect",
        "department": "Infrastructure & Reliability",
        "location": "Remote",
        "experience_level": "Lead",
        "min_years_experience": 5.0,
        "description": (
            "Looking for a Cloud DevOps Architect to manage multi-region Kubernetes clusters on AWS, "
            "maintain Terraform IaC scripts, and build zero-downtime CI/CD deployment pipelines. "
            "You will establish SOC2 security compliance, monitoring with Prometheus/Grafana, and incident response."
        ),
        "required_skills": ["Kubernetes", "AWS", "Terraform", "Docker", "CI/CD", "Linux"],
        "preferred_skills": ["Prometheus", "Grafana", "Python", "Golang", "Helm", "Security Compliance"],
        "mandatory_qualifications": ["5+ years cloud infrastructure experience", "Hands-on Kubernetes cluster management"],
        "technical_subjects": ["Infrastructure as Code", "Kubernetes Networking", "Cloud Security", "Disaster Recovery"],
    },
]

FIRST_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Jamie", "Peyton", "Cameron",
    "Sam", "Dakota", "Reese", "Quinn", "Skyler", "Kendall", "Hayden", "Logan", "Jesse", "Finley",
    "Rowan", "Harper", "Emerson", "River", "Amari", "Kai", "Sage", "Eden", "Rory", "Milan"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez",
    "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore",
    "Jackson", "Martin", "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez"
]

SKILL_POOLS = {
    "backend": ["Python", "FastAPI", "Django", "Flask", "SQLAlchemy", "PostgreSQL", "MySQL", "Redis", "Kafka", "Docker", "REST APIs", "Microservices", "Pytest", "Git"],
    "ai": ["Python", "PyTorch", "TensorFlow", "Scikit-Learn", "Machine Learning", "NLP", "Pandas", "NumPy", "LangChain", "Vector Databases", "React", "TypeScript", "Docker"],
    "devops": ["Kubernetes", "AWS", "Terraform", "Docker", "CI/CD", "Linux", "Prometheus", "Grafana", "Bash", "Python", "Helm", "Ansible", "CloudWatch", "GitOps"],
    "general": ["Java", "C++", "HTML/CSS", "JavaScript", "PHP", "Ruby on Rails", "Agile", "Jira", "Excel", "Customer Support"]
}


def generate_single_pdf_resume(filepath: str, name: str, email: str, role_type: str, experience_level: str):
    """Generate a clean, text-extractable 1-page PDF resume using ReportLab."""
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter

    # Margins and layout
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, name)

    c.setFont("Helvetica", 10)
    c.drawString(50, height - 68, f"Email: {email}  |  Phone: +1 (555) 01{random.randint(10, 99)}-{random.randint(1000, 9999)}  |  Location: San Francisco, CA")

    # Line separator
    c.setLineWidth(1)
    c.setStrokeColorRGB(0.3, 0.3, 0.8)
    c.line(50, height - 76, width - 50, height - 76)

    # Experience calculation
    years_exp = {
        "senior": random.uniform(5.0, 9.0),
        "mid": random.uniform(2.5, 4.5),
        "junior": random.uniform(0.5, 2.0),
    }.get(experience_level, 3.0)

    # Skills selection
    base_skills = SKILL_POOLS.get(role_type, SKILL_POOLS["backend"])
    if experience_level == "senior":
        selected_skills = random.sample(base_skills, min(len(base_skills), random.randint(9, 12)))
    elif experience_level == "mid":
        selected_skills = random.sample(base_skills, min(len(base_skills), random.randint(6, 8)))
    else:
        # Junior or misaligned
        selected_skills = random.sample(SKILL_POOLS["general"], 4) + random.sample(base_skills, 2)

    y = height - 100
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "PROFESSIONAL SUMMARY")
    y -= 16
    c.setFont("Helvetica", 10)
    summary_text = (
        f"Results-driven software engineering professional with {years_exp:.1f} years of hands-on experience "
        f"architecting, deploying, and maintaining resilient scalable systems in fast-paced collaborative teams."
    )
    c.drawString(50, y, summary_text)

    y -= 25
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "TECHNICAL SKILLS")
    y -= 16
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Core Technologies: {', '.join(selected_skills)}")

    y -= 25
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "PROFESSIONAL EXPERIENCE")
    y -= 18

    # Work experience entries
    companies = ["Acme Cloud Systems", "Nexus Technologies", "Vertex Labs", "Apex Digital"]
    num_jobs = 2 if years_exp > 3 else 1
    for i in range(num_jobs):
        comp = companies[i % len(companies)]
        title = "Senior Software Engineer" if (years_exp > 4 and i == 0) else "Software Engineer"
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, f"{title} — {comp}")
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(400, y, f"20{20-i*2} - Present" if i == 0 else f"20{18-i*2} - 20{20-i*2}")
        y -= 14
        c.setFont("Helvetica", 9)
        c.drawString(60, y, f"• Designed and maintained distributed backend microservices using {selected_skills[0]} and {selected_skills[1] if len(selected_skills) > 1 else 'SQL'}.")
        y -= 12
        c.drawString(60, y, "• Automated CI/CD deployment pipelines, cutting release downtime by 35%.")
        y -= 12
        c.drawString(60, y, "• Implemented performance optimizations on relational databases and caching layers.")
        y -= 18

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "KEY PROJECTS")
    y -= 18
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Distributed Event Streaming & Analytics Engine")
    y -= 14
    c.setFont("Helvetica", 9)
    c.drawString(60, y, f"Architected high-throughput message ingestion pipeline processing 25k events/sec using {selected_skills[0]}.")
    y -= 22

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "EDUCATION & CERTIFICATIONS")
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(50, y, "Bachelor of Science in Computer Science — State University (2020)")
    y -= 14
    c.drawString(50, y, "AWS Certified Solutions Architect & Developer Associate")

    c.save()


def generate_synthetic_dataset(total_resumes: int = 100) -> List[str]:
    """Generates synthetic job descriptions and a suite of 100+ PDF resumes."""
    generated_files = []
    print(f"Generating {total_resumes} synthetic PDF resumes in {RESUMES_DIR}...")

    roles = ["backend", "ai", "devops", "general"]
    levels = ["senior", "mid", "junior"]

    for i in range(1, total_resumes + 1):
        fname = random.choice(FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        full_name = f"{fname} {lname}"
        email = f"{fname.lower()}.{lname.lower()}{random.randint(10, 99)}@example.com"
        role_type = random.choice(roles)
        level = random.choice(levels)

        filename = f"Resume_{i:03d}_{fname}_{lname}_{role_type}_{level}.pdf"
        filepath = str(RESUMES_DIR / filename)

        generate_single_pdf_resume(filepath, full_name, email, role_type, level)
        generated_files.append(filepath)

    # Create 5 intentional duplicates to verify SHA-256 duplicate detection
    for dup_idx in range(1, 6):
        source_file = generated_files[dup_idx - 1]
        dup_file = str(RESUMES_DIR / f"Duplicate_Copy_{dup_idx}_{os.path.basename(source_file)}")
        with open(source_file, "rb") as sf, open(dup_file, "wb") as df:
            df.write(sf.read())
        generated_files.append(dup_file)

    print(f"Successfully created {len(generated_files)} synthetic resumes (including 5 duplicate test cases).")
    return generated_files


if __name__ == "__main__":
    generate_synthetic_dataset(100)
