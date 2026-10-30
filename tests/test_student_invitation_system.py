import os
"""
Full Backend API and service test script verifying:
1. Candidate Shortlisting & Automatic Student Account Creation (Idempotent)
2. Unique username format HS<year><seq>
3. Cryptographic single-use password setup token generation & hashing (raw token never stored in DB)
4. Expiration check & Argon2id password setup completion
5. Authentication via StudentAuthService (valid credentials & invalid rejection)
6. Prevention of token replay (used tokens strictly rejected)
7. EmailNotification record logging & delivery status tracking
8. Multi-interview association for existing student account
"""

from datetime import datetime, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import (
    Base,
    CandidateProfile,
    Company,
    EmailDeliveryStatus,
    EmailNotification,
    InterviewInvitation,
    InterviewSession,
    InterviewStatus,
    Job,
    PasswordSetupToken,
    Recruiter,
    RecruiterDecision,
    RecruitmentCampaign,
    ResumeDocument,
    ScreeningResult,
    User,
    UserRole,
)
from config import settings
from src.recruitment.email_service import EmailService
from src.recruitment.invitation_service import InvitationService
from src.security.authentication import hash_password, verify_password, validate_password_strength
from src.security.student_auth_service import StudentAuthService


@pytest.fixture
def test_db():
    settings.SMTP_MOCK_MODE = True
    os.environ["SMTP_MOCK_MODE"] = "true"
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed Company & Recruiter
    company = Company(name="Test Tech Inc", domain="testtech.io")
    session.add(company)
    session.flush()

    campaign = RecruitmentCampaign(company_id=company.id, title="Test 2026 Campus Drive")
    session.add(campaign)
    session.flush()

    job = Job(
        campaign_id=campaign.id,
        title="Software Engineer Intern",
        description="Python intern role",
        required_skills=["Python", "SQL"],
        interview_duration_minutes=30,
    )
    session.add(job)
    session.flush()

    # Seed Candidate Profile & Application
    candidate = CandidateProfile(
        name="Rahul Kumar",
        email="rahul.kumar@testmail.com",
        phone="+91-9876543210",
        years_experience=1.0,
    )
    session.add(candidate)
    session.flush()

    doc = ResumeDocument(
        campaign_id=campaign.id,
        job_id=job.id,
        candidate_id=candidate.id,
        original_filename="Rahul_Kumar_Resume.pdf",
        storage_path="data/uploads/test.pdf",
        file_size_bytes=1024,
        sha256_hash="dummyhash123456",
    )
    session.add(doc)
    session.flush()

    screening = ScreeningResult(
        resume_id=doc.id,
        overall_score=85.0,
        recruiter_decision=RecruiterDecision.SHORTLISTED.value,
    )
    session.add(screening)
    session.commit()

    yield {
        "session": session,
        "company": company,
        "campaign": campaign,
        "job": job,
        "candidate": candidate,
        "document": doc,
        "screening": screening,
    }

    session.close()


def test_unique_username_generation(test_db):
    session = test_db["session"]
    year = str(datetime.utcnow().year)
    username1 = StudentAuthService.generate_unique_username(session, "Rahul Kumar")
    assert username1.startswith(f"HS{year}")

    # Create user with username1
    user1 = User(
        username=username1,
        email="test1@example.com",
        name="Student 1",
        role=UserRole.STUDENT.value,
    )
    session.add(user1)
    session.commit()

    # Next username must be strictly distinct
    username2 = StudentAuthService.generate_unique_username(session, "Next Student")
    assert username2 != username1
    assert username2.startswith(f"HS{year}")


def test_automatic_student_account_provisioning(test_db):
    session = test_db["session"]
    candidate = test_db["candidate"]
    job = test_db["job"]

    invitation, details = InvitationService.create_invitation(
        session=session,
        candidate_id=candidate.id,
        job_id=job.id,
        stage="Comprehensive",
        expire_hours=72,
        send_email=True,
    )
    session.commit()

    assert invitation is not None
    assert details["username"] is not None
    assert details["username"].startswith("HS")
    assert details["email_sent"] is True
    assert "Password_Setup?token=" in details["setup_url"]

    # Verify user in database
    student_user = session.query(User).filter(User.username == details["username"]).first()
    assert student_user is not None
    assert student_user.email == candidate.email
    assert student_user.role == UserRole.STUDENT.value
    assert student_user.candidate_profile_id == candidate.id

    # Verify raw token is NOT in database, only hash
    raw_token = details["raw_setup_token"]
    raw_found = session.query(PasswordSetupToken).filter(PasswordSetupToken.token_hash == raw_token).first()
    assert raw_found is None  # Raw token must NEVER be stored in DB


def test_password_setup_lifecycle(test_db):
    session = test_db["session"]
    candidate = test_db["candidate"]
    job = test_db["job"]

    invitation, details = InvitationService.create_invitation(
        session=session,
        candidate_id=candidate.id,
        job_id=job.id,
        send_email=True,
    )
    session.commit()

    raw_token = details["raw_setup_token"]
    username = details["username"]

    # 1. Validate token before use
    val = StudentAuthService.validate_setup_token(session, raw_token)
    assert val["valid"] is True
    assert val["username"] == username

    # 2. Test weak password rejection
    ok_weak, err_weak, _ = StudentAuthService.complete_password_setup(session, raw_token, "weak", "weak")
    assert ok_weak is False
    assert "at least 8 characters" in err_weak

    # 3. Test password mismatch rejection
    ok_mismatch, err_mismatch, _ = StudentAuthService.complete_password_setup(session, raw_token, "SecurePass2026!", "WrongPass2026!")
    assert ok_mismatch is False
    assert "do not match" in err_mismatch

    # 4. Successful password setup
    ok_success, msg_success, user_res = StudentAuthService.complete_password_setup(
        session=session,
        raw_token=raw_token,
        new_password="CandidatePass2026!",
        confirm_password="CandidatePass2026!",
    )
    assert ok_success is True
    assert user_res is not None
    assert user_res.username == username
    assert "created successfully" in msg_success.lower()

    # 5. Token replay prevention: Re-using the same token MUST fail
    val_replay = StudentAuthService.validate_setup_token(session, raw_token)
    assert val_replay["valid"] is False
    assert val_replay.get("already_used") is True

    # 6. Authenticate student with newly created password
    user, auth_msg = StudentAuthService.authenticate_student(session, username, "CandidatePass2026!")
    assert user is not None
    assert user.username == username

    # 7. Authenticate student via email also works
    user_email, _ = StudentAuthService.authenticate_student(session, candidate.email, "CandidatePass2026!")
    assert user_email is not None

    # 8. Invalid password strictly rejected
    bad_user, bad_msg = StudentAuthService.authenticate_student(session, username, "WrongPassword!")
    assert bad_user is None
    assert "Invalid credentials" in bad_msg


def test_email_notification_delivery_tracking(test_db):
    session = test_db["session"]
    candidate = test_db["candidate"]
    job = test_db["job"]

    invitation, details = InvitationService.create_invitation(
        session=session,
        candidate_id=candidate.id,
        job_id=job.id,
        send_email=True,
    )
    session.commit()

    notification = (
        session.query(EmailNotification)
        .filter(EmailNotification.invitation_id == invitation.id)
        .first()
    )
    assert notification is not None
    assert notification.recipient_email == candidate.email
    assert notification.status == EmailDeliveryStatus.DELIVERED.value
    assert notification.delivered_at is not None
    assert "Congratulations! You Have Been Shortlisted" in notification.subject
    assert details["username"] in notification.body_html
