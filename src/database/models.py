import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedColumn, mapped_column, relationship


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    RECRUITER = "recruiter"
    HIRING_MANAGER = "hiring_manager"
    CANDIDATE = "candidate"
    STUDENT = "student"


class ProcessingStatus(str, enum.Enum):
    UPLOADED = "Uploaded"
    QUEUED = "Queued"
    PROCESSING = "Processing"
    PROCESSED = "Processed"
    NEEDS_MANUAL_REVIEW = "Needs Manual Review"
    MEETS_CRITERIA = "Meets Configured Criteria"
    DOES_NOT_MEET = "Does Not Meet Configured Criteria"
    FAILED = "Failed"
    DUPLICATE = "Duplicate"


class RecruiterDecision(str, enum.Enum):
    PENDING = "Pending"
    SHORTLISTED = "Shortlisted"
    REJECTED = "Rejected"
    INVITED = "Invited"
    INTERVIEWED = "Interviewed"
    HOLD_FOR_REVIEW = "Hold for Review"
    SELECTED_FOR_NEXT_ROUND = "Selected for Next Round"
    OFFER_EXTENDED = "Offer Extended"
    HIRED = "Hired"


class InterviewStage(str, enum.Enum):
    TECHNICAL = "Technical"
    HR = "HR"
    COMPREHENSIVE = "Comprehensive"


class InterviewStatus(str, enum.Enum):
    NOT_SCHEDULED = "Not Scheduled"
    NOT_STARTED = "Not Started"
    INVITED = "Invited"
    INVITATION_SENT = "Invitation Sent"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    EXPIRED = "Expired"
    CANCELLED = "Cancelled"


class EmailDeliveryStatus(str, enum.Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    SENT = "SENT"
    FAILED = "FAILED"
    DELIVERED = "DELIVERED"


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    recruiters: Mapped[list["Recruiter"]] = relationship("Recruiter", back_populates="company", cascade="all, delete-orphan")
    campaigns: Mapped[list["RecruitmentCampaign"]] = relationship("RecruitmentCampaign", back_populates="company", cascade="all, delete-orphan")


class Recruiter(Base):
    __tablename__ = "recruiters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.RECRUITER.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="recruiters")


class RecruitmentCampaign(Base):
    __tablename__ = "recruitment_campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Active")  # Active, Paused, Closed
    target_hires: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="campaigns", lazy="joined")
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="campaign", cascade="all, delete-orphan")
    resumes: Mapped[list["ResumeDocument"]] = relationship("ResumeDocument", back_populates="campaign", cascade="all, delete-orphan")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("recruitment_campaigns.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location: Mapped[str] = mapped_column(String(100), default="Remote")
    job_type: Mapped[str] = mapped_column(String(50), default="Full-time")
    experience_level: Mapped[str] = mapped_column(String(50), default="Mid-Senior")  # Entry, Mid, Senior, Lead
    min_years_experience: Mapped[float] = mapped_column(Float, default=2.0)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Structured Requirements (JSON stored)
    required_skills: Mapped[list[Any]] = mapped_column(JSON, default=list)  # List[str]
    preferred_skills: Mapped[list[Any]] = mapped_column(JSON, default=list)  # List[str]
    mandatory_qualifications: Mapped[list[Any]] = mapped_column(JSON, default=list)  # List[str]
    education_requirements: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    technical_subjects: Mapped[list[Any]] = mapped_column(JSON, default=list)  # List[str]
    interview_duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    interview_stages: Mapped[list[Any]] = mapped_column(JSON, default=lambda: ["Technical", "HR"])

    # Screening Weights
    weight_keywords: Mapped[float] = mapped_column(Float, default=0.25)
    weight_similarity: Mapped[float] = mapped_column(Float, default=0.25)
    weight_experience: Mapped[float] = mapped_column(Float, default=0.25)
    weight_semantic: Mapped[float] = mapped_column(Float, default=0.25)
    shortlist_threshold: Mapped[float] = mapped_column(Float, default=70.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    campaign: Mapped["RecruitmentCampaign"] = relationship("RecruitmentCampaign", back_populates="jobs", lazy="joined")
    resumes: Mapped[list["ResumeDocument"]] = relationship("ResumeDocument", back_populates="job", cascade="all, delete-orphan")
    invitations: Mapped[list["InterviewInvitation"]] = relationship("InterviewInvitation", back_populates="job", cascade="all, delete-orphan")


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    linkedin: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    github: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    portfolio: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    years_experience: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    resumes: Mapped[list["ResumeDocument"]] = relationship("ResumeDocument", back_populates="candidate")
    invitations: Mapped[list["InterviewInvitation"]] = relationship("InterviewInvitation", back_populates="candidate")
    interview_sessions: Mapped[list["InterviewSession"]] = relationship("InterviewSession", back_populates="candidate")


class ResumeDocument(Base):
    __tablename__ = "resume_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("recruitment_campaigns.id"), nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), nullable=False)
    candidate_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("candidate_profiles.id"), nullable=True)

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    page_count: Mapped[int] = mapped_column(Integer, default=1)

    # Document Flags
    is_scanned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_encrypted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_corrupt: Mapped[bool] = mapped_column(Boolean, default=False)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_of_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    processing_status: Mapped[str] = mapped_column(String(50), default=ProcessingStatus.UPLOADED.value)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    campaign: Mapped["RecruitmentCampaign"] = relationship("RecruitmentCampaign", back_populates="resumes")
    job: Mapped["Job"] = relationship("Job", back_populates="resumes")
    candidate: Mapped[Optional["CandidateProfile"]] = relationship("CandidateProfile", back_populates="resumes")
    parsed_data: Mapped[Optional["ParsedResumeData"]] = relationship("ParsedResumeData", back_populates="resume", uselist=False, cascade="all, delete-orphan")
    screening_result: Mapped[Optional["ScreeningResult"]] = relationship("ScreeningResult", back_populates="resume", uselist=False, cascade="all, delete-orphan")


class ParsedResumeData(Base):
    __tablename__ = "parsed_resume_data"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    resume_id: Mapped[str] = mapped_column(String(36), ForeignKey("resume_documents.id"), nullable=False, unique=True)

    extracted_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    extracted_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    extracted_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    technical_skills: Mapped[list[Any]] = mapped_column(JSON, default=list)  # List[str]
    soft_skills: Mapped[list[Any]] = mapped_column(JSON, default=list)  # List[str]
    education: Mapped[list[Any]] = mapped_column(JSON, default=list)  # List[Dict]
    work_experience: Mapped[list[Any]] = mapped_column(JSON, default=list)  # List[Dict]
    projects: Mapped[list[Any]] = mapped_column(JSON, default=list)  # List[Dict]
    certifications: Mapped[list[Any]] = mapped_column(JSON, default=list)  # List[str]
    achievements: Mapped[list[Any]] = mapped_column(JSON, default=list)  # List[str]

    total_years_experience: Mapped[float] = mapped_column(Float, default=0.0)
    skill_evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # Dict[skill, excerpt]
    parsed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    resume: Mapped["ResumeDocument"] = relationship("ResumeDocument", back_populates="parsed_data")


class ScreeningResult(Base):
    __tablename__ = "screening_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    resume_id: Mapped[str] = mapped_column(String(36), ForeignKey("resume_documents.id"), nullable=False, unique=True)

    overall_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0 to 100
    keyword_coverage_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0 to 100
    text_similarity_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0 to 100
    experience_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0 to 100
    semantic_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0 to 100

    mandatory_criteria_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    mandatory_details: Mapped[list[Any]] = mapped_column(JSON, default=list)  # List[Dict[str, Any]]

    matched_skills: Mapped[list[Any]] = mapped_column(JSON, default=list)  # List[str]
    missing_skills: Mapped[list[Any]] = mapped_column(JSON, default=list)  # List[str]
    unclear_evidence: Mapped[list[Any]] = mapped_column(JSON, default=list)  # List[str]
    evidence_excerpts: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # Dict[str, str]

    recommendation: Mapped[str] = mapped_column(String(100), default="Needs Manual Review")
    recommendation_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Recruiter Override / Decisions
    recruiter_decision: Mapped[str] = mapped_column(String(50), default=RecruiterDecision.PENDING.value)
    recruiter_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recruiter_override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    resume: Mapped["ResumeDocument"] = relationship("ResumeDocument", back_populates="screening_result")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Set once student sets password
    role: Mapped[str] = mapped_column(String(50), default=UserRole.STUDENT.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    candidate_profile_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("candidate_profiles.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    candidate_profile: Mapped[Optional["CandidateProfile"]] = relationship("CandidateProfile", foreign_keys=[candidate_profile_id])
    password_setup_tokens: Mapped[list["PasswordSetupToken"]] = relationship("PasswordSetupToken", back_populates="user", cascade="all, delete-orphan")
    invitations: Mapped[list["InterviewInvitation"]] = relationship("InterviewInvitation", back_populates="student_user")


class PasswordSetupToken(Base):
    __tablename__ = "password_setup_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="password_setup_tokens")


class EmailNotification(Base):
    __tablename__ = "email_notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=EmailDeliveryStatus.PENDING.value)
    delivery_attempts: Mapped[int] = mapped_column(Integer, default=0)
    provider_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    invitation_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("interview_invitations.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class InterviewInvitation(Base):
    __tablename__ = "interview_invitations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_profiles.id"), nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), nullable=False)
    student_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    application_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("resume_documents.id"), nullable=True)

    username: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    token: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    stage: Mapped[str] = mapped_column(String(50), default=InterviewStage.COMPREHENSIVE.value)
    invitation_status: Mapped[str] = mapped_column(String(50), default=InterviewStatus.INVITED.value)

    invited_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    deadline_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="invitations")
    job: Mapped["Job"] = relationship("Job", back_populates="invitations")
    student_user: Mapped[Optional["User"]] = relationship("User", back_populates="invitations")
    application: Mapped[Optional["ResumeDocument"]] = relationship("ResumeDocument")
    sessions: Mapped[list["InterviewSession"]] = relationship("InterviewSession", back_populates="invitation")
    email_notifications: Mapped[list["EmailNotification"]] = relationship("EmailNotification", foreign_keys=[EmailNotification.invitation_id], cascade="all, delete-orphan")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    invitation_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("interview_invitations.id"), nullable=True)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_profiles.id"), nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), nullable=False)

    stage: Mapped[str] = mapped_column(String(50), default=InterviewStage.TECHNICAL.value)
    status: Mapped[str] = mapped_column(String(50), default=InterviewStatus.IN_PROGRESS.value)
    current_question_index: Mapped[int] = mapped_column(Integer, default=0)
    total_questions: Mapped[int] = mapped_column(Integer, default=5)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)

    overall_interview_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0 to 100
    candidate_consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    invitation: Mapped[Optional["InterviewInvitation"]] = relationship("InterviewInvitation", back_populates="sessions")
    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="interview_sessions")
    questions: Mapped[list["InterviewQuestion"]] = relationship("InterviewQuestion", back_populates="session", cascade="all, delete-orphan")
    security_events: Mapped[list["InterviewSecurityEvent"]] = relationship("InterviewSecurityEvent", back_populates="session", cascade="all, delete-orphan")


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("interview_sessions.id"), nullable=False)
    question_order: Mapped[int] = mapped_column(Integer, nullable=False)

    question_type: Mapped[str] = mapped_column(String(50), default="conceptual")  # conceptual, coding, scenario, project, star_hr
    category: Mapped[str] = mapped_column(String(100), default="General")  # Python, System Design, Teamwork, etc.
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    expected_concepts: Mapped[list[Any]] = mapped_column(JSON, default=list)  # List[str]
    rubric_criteria: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # Weightings & criteria

    # Answer & Evaluation
    candidate_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    answer_mode: Mapped[str] = mapped_column(String(50), default="text")  # text, voice_transcribed
    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0 to 100
    evaluation_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    correct_concepts: Mapped[list[Any]] = mapped_column(JSON, default=list)
    missing_concepts: Mapped[list[Any]] = mapped_column(JSON, default=list)
    improvement_suggestions: Mapped[list[Any]] = mapped_column(JSON, default=list)
    rubric_scores: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # Breakdown e.g. {"correctness": 35/40, ...}

    # Follow up question if applicable
    follow_up_question: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    follow_up_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    session: Mapped["InterviewSession"] = relationship("InterviewSession", back_populates="questions")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    company_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # Candidate, Job, Resume, Interview
    entity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # Safe metadata without full resume text
    ip_address: Mapped[str] = mapped_column(String(50), default="127.0.0.1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class InterviewSecurityEvent(Base):
    __tablename__ = "interview_security_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("interview_sessions.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # tab_switch, fullscreen_exit, copy_attempt, paste_attempt, camera_interrupted, mic_interrupted
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    event_details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Relationships
    session: Mapped["InterviewSession"] = relationship("InterviewSession", back_populates="security_events")


class RecruitmentDecisionRecord(Base):
    __tablename__ = "recruitment_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_profiles.id"), nullable=False, index=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), nullable=False, index=True)
    interview_session_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("interview_sessions.id"), nullable=True)
    recruiter_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    decision: Mapped[str] = mapped_column(String(50), nullable=False)  # Selected for Next Round, Rejected, Hold for Review, etc.
    recruiter_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_round_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    next_round_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_round_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decision_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile")
    job: Mapped["Job"] = relationship("Job")
    session: Mapped[Optional["InterviewSession"]] = relationship("InterviewSession")


class DataRetentionRecord(Base):
    __tablename__ = "data_retention_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    scheduled_purge_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_purged: Mapped[bool] = mapped_column(Boolean, default=False)
    purged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reason: Mapped[str] = mapped_column(String(255), default="GDPR/Privacy Retention Expired")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
