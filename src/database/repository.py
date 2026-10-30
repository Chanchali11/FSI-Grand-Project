from collections.abc import Generator
from contextlib import contextmanager
import logging
import threading
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from config import settings
from src.database.models import (
    AuditEvent,
    Base,
    Company,
    Job,
    Recruiter,
    RecruitmentCampaign,
    UserRole,
)
from src.security.authentication import hash_password

logger = logging.getLogger(__name__)

# SQLite engine configuration (ensure directory exists and check_same_thread=False for Streamlit multi-threading)
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, echo=False)
SessionFactory = scoped_session(sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine))
_db_init_lock = threading.Lock()


def _migrate_existing_tables():
    """Ensure newly added columns exist in existing SQLite databases without requiring manual reset."""
    with engine.connect() as conn:
        # Check columns on interview_invitations
        try:
            res = conn.exec_driver_sql("PRAGMA table_info(interview_invitations)").fetchall()
            existing_cols = {r[1] for r in res}
            new_columns = [
                ("student_user_id", "VARCHAR(36) REFERENCES users(id)"),
                ("application_id", "VARCHAR(36) REFERENCES resume_documents(id)"),
                ("username", "VARCHAR(100)"),
                ("invitation_status", "VARCHAR(50) DEFAULT 'Invited'"),
                ("invited_at", "DATETIME"),
                ("deadline_at", "DATETIME"),
                ("completed_at", "DATETIME"),
            ]
            for col_name, col_def in new_columns:
                if col_name not in existing_cols:
                    conn.exec_driver_sql(f"ALTER TABLE interview_invitations ADD COLUMN {col_name} {col_def}")
            conn.commit()
        except Exception:
            pass


def init_db():
    """Create all tables, migrate schema additions, and seed default company and recruiter if empty."""
    with _db_init_lock:
        try:
            Base.metadata.create_all(bind=engine, checkfirst=True)
        except Exception as e:
            if "already exists" not in str(e).lower():
                logger.warning(f"Metadata create_all notice: {e}")
        try:
            _migrate_existing_tables()
        except Exception as e:
            logger.warning(f"Table migration notice: {e}")

        try:
            with get_db_session() as session:
                # Check if company exists
                demo_company = session.query(Company).first()
                if not demo_company:
                    demo_company = Company(
                        name="Acme Global Technologies",
                        domain="acmetech.io",
                        industry="Software & Cloud Infrastructure",
                        description="Enterprise cloud, AI, and scalable backend solutions.",
                    )
                    session.add(demo_company)
                    session.flush()

                    # Seed default recruiter account with cryptographically hashed password
                    demo_recruiter = Recruiter(
                        company_id=demo_company.id,
                        name="Alex Vance (Lead Talent Partner)",
                        email="recruiter@hiresphere.ai",
                        password_hash=hash_password("RecruiterPass2026!"),
                        role=UserRole.RECRUITER.value,
                    )
                    session.add(demo_recruiter)

                    # Seed default administrator account
                    demo_admin = Recruiter(
                        company_id=demo_company.id,
                        name="System Administrator",
                        email="admin@hiresphere.ai",
                        password_hash=hash_password("AdminPass2026!"),
                        role=UserRole.ADMIN.value,
                    )
                    session.add(demo_admin)

                    # Seed an initial campaign
                    campaign = RecruitmentCampaign(
                        company_id=demo_company.id,
                        title="Q4 Software Engineering Scale-up",
                        status="Active",
                        target_hires=5,
                    )
                    session.add(campaign)
                    session.flush()

                    # Seed a default sample job
                    sample_job = Job(
                        campaign_id=campaign.id,
                        title="Senior Python Backend Engineer",
                        department="Platform Engineering",
                        location="Remote (US/EU/APAC)",
                        job_type="Full-time",
                        experience_level="Senior",
                        min_years_experience=4.0,
                        description=(
                            "We are looking for an experienced Senior Python Backend Engineer to build high-throughput "
                            "distributed microservices, design low-latency PostgreSQL and Redis data architectures, "
                            "and implement asynchronous messaging pipelines using Kafka. "
                            "You will lead architectural reviews, mentor engineers, and ensure 99.99% system reliability."
                        ),
                        required_skills=["Python", "FastAPI", "SQLAlchemy", "PostgreSQL", "Docker", "REST APIs", "Microservices"],
                        preferred_skills=["Kafka", "Redis", "Kubernetes", "AWS", "CI/CD", "Pytest"],
                        mandatory_qualifications=["Minimum 4 years of backend development", "Proficiency in Python"],
                        technical_subjects=["Python Concurrency", "Database Indexing & Transactions", "System Architecture", "REST & Async Design"],
                        interview_duration_minutes=35,
                        interview_stages=["Technical", "HR"],
                        weight_keywords=0.25,
                        weight_similarity=0.25,
                        weight_experience=0.25,
                        weight_semantic=0.25,
                        shortlist_threshold=70.0,
                    )
                    session.add(sample_job)
                    session.commit()
                else:
                    # Upgrade legacy placeholder password hashes for existing databases
                    for r in session.query(Recruiter).all():
                        if "default_hash_value" in r.password_hash or "$" not in r.password_hash:
                            r.password_hash = hash_password("RecruiterPass2026!" if r.role == UserRole.RECRUITER.value else "AdminPass2026!")
                    
                    # Ensure admin account exists
                    admin_user = session.query(Recruiter).filter(Recruiter.role == UserRole.ADMIN.value).first()
                    if not admin_user:
                        admin_user = Recruiter(
                            company_id=demo_company.id,
                            name="System Administrator",
                            email="admin@hiresphere.ai",
                            password_hash=hash_password("AdminPass2026!"),
                            role=UserRole.ADMIN.value,
                        )
                        session.add(admin_user)
                    session.commit()
        except Exception as e:
            logger.warning(f"Database seed notice (may already be initialized): {e}")


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class DatabaseRepository:
    """Helper repository for common database queries."""

    @staticmethod
    def get_or_create_company(session: Session, name: str, domain: str = "") -> Company:
        company = session.query(Company).filter(Company.name == name).first()
        if not company:
            company = Company(name=name, domain=domain)
            session.add(company)
            session.flush()
        return company

    @staticmethod
    def get_campaigns(session: Session, company_id: str | None = None) -> list[RecruitmentCampaign]:
        query = session.query(RecruitmentCampaign)
        if company_id:
            query = query.filter(RecruitmentCampaign.company_id == company_id)
        return query.order_by(RecruitmentCampaign.created_at.desc()).all()

    @staticmethod
    def get_jobs(session: Session, campaign_id: str | None = None) -> list[Job]:
        query = session.query(Job)
        if campaign_id:
            query = query.filter(Job.campaign_id == campaign_id)
        return query.order_by(Job.created_at.desc()).all()

    @staticmethod
    def get_job_by_id(session: Session, job_id: str) -> Job | None:
        return session.query(Job).filter(Job.id == job_id).first()

    @staticmethod
    def log_audit_event(
        session: Session,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        company_id: str | None = None,
        user_id: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        event = AuditEvent(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            company_id=company_id,
            user_id=user_id,
            details=details or {},
        )
        session.add(event)
