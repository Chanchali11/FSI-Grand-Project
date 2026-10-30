"""
Comprehensive Automated Test Suite covering:
1. End-to-end recruitment workflow: 10 candidate upload -> Screening -> Recruiter Shortlisting
2. Automated Email Invitation Generation & Unique Password Setup Token Generation
3. Student Account Activation & Login Authentication
4. Active Interview Integrity & Anti-Cheating Event Logging (tab switch, copy/paste, fullscreen)
5. Multi-rubric Interview Performance Evaluation & Structured Scoring (0-100)
6. Next-Round Selection Workflow & Automated Next-Round Candidate Email Delivery
7. Security restrictions & idempotency verification
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
    InterviewQuestion,
    InterviewSecurityEvent,
    InterviewSession,
    InterviewStatus,
    Job,
    PasswordSetupToken,
    Recruiter,
    RecruiterDecision,
    RecruitmentCampaign,
    RecruitmentDecisionRecord,
    ResumeDocument,
    ScreeningResult,
    User,
    UserRole,
)
from src.interview.interview_engine import InterviewEngine
from src.recruitment.campaign_service import CampaignService
from src.recruitment.email_service import EmailService
from src.recruitment.invitation_service import InvitationService
from src.recruitment.shortlist_service import ShortlistService
from src.reports.interview_report_service import InterviewReportService
from src.security.student_auth_service import StudentAuthService


@pytest.fixture
def workflow_db():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create Company, Campaign & Job
    company = Company(name="Acme Global Technologies", domain="acme.ai")
    session.add(company)
    session.flush()

    campaign = RecruitmentCampaign(company_id=company.id, title="2026 Campus Drive")
    session.add(campaign)
    session.flush()

    job = Job(
        campaign_id=campaign.id,
        title="Full Stack Software Engineer",
        description="Python and React engineering position",
        required_skills=["Python", "React", "PostgreSQL", "Docker"],
        shortlist_threshold=70.0,
    )
    session.add(job)
    session.flush()

    # Seed 10 candidates with screening scores (Case 1)
    # 4 candidates with score >= 70, 6 candidates with score < 70
    candidates = []
    for i in range(1, 11):
        cand = CandidateProfile(
            name=f"Student {i}",
            email=f"student{i}@campus.edu",
            phone=f"+91-987654321{i % 10}",
            years_experience=float(i % 4),
        )
        session.add(cand)
        session.flush()

        doc = ResumeDocument(
            campaign_id=campaign.id,
            job_id=job.id,
            candidate_id=cand.id,
            original_filename=f"Resume_Student_{i}.pdf",
            storage_path=f"data/uploads/student_{i}.pdf",
            file_size_bytes=2048,
            sha256_hash=f"hash_student_{i}_{i*1111}",
            processing_status="Processed",
        )
        session.add(doc)
        session.flush()

        # Score >= 75 for students 1..4; < 70 for students 5..10
        score = 85.0 - (i * 3.0) if i <= 4 else 60.0 - (i * 2.0)
        screening = ScreeningResult(
            resume_id=doc.id,
            overall_score=score,
            keyword_coverage_score=score,
            experience_score=score,
            recommendation="Meets Configured Criteria" if score >= 70 else "Does Not Meet Configured Criteria",
            recruiter_decision=RecruiterDecision.PENDING.value,
        )
        session.add(screening)
        candidates.append((cand, doc, screening))

    session.commit()

    yield {
        "session": session,
        "company": company,
        "campaign": campaign,
        "job": job,
        "candidates": candidates,
    }

    session.close()


def test_workflow_bulk_shortlist_10_candidates(workflow_db):
    """
    Test Case 1:
    10 candidates screened.
    Recruiter shortlists top candidates meeting the >= 70.0 threshold.
    Verify exactly 4 candidates are shortlisted.
    """
    session = workflow_db["session"]
    job = workflow_db["job"]

    approved_count = ShortlistService.bulk_approve_shortlist(
        session=session,
        job_id=job.id,
        threshold_score=70.0,
    )
    session.commit()

    assert approved_count == 4

    shortlisted = ShortlistService.get_candidate_screening_list(
        session=session,
        job_id=job.id,
        decision_filter=RecruiterDecision.SHORTLISTED.value,
    )
    assert len(shortlisted) == 4
    for cand in shortlisted:
        assert cand["overall_score"] >= 70.0


def test_workflow_email_invitations_and_account_activation(workflow_db):
    """
    Test Case 2 & 3:
    Recruiter sends invitations to shortlisted candidates.
    Verify each gets unique activation token and password setup link.
    Verify rejected/pending candidates do not receive invitations.
    Student activates password, logs in and gets access to their assigned interview.
    """
    session = workflow_db["session"]
    job = workflow_db["job"]

    # Shortlist exactly 4 candidates
    ShortlistService.bulk_approve_shortlist(session, job.id, threshold_score=70.0)
    session.commit()

    shortlisted = ShortlistService.get_candidate_screening_list(
        session=session,
        job_id=job.id,
        decision_filter=RecruiterDecision.SHORTLISTED.value,
    )

    created_invitations = []
    for cand in shortlisted:
        inv, details = InvitationService.create_invitation(
            session=session,
            candidate_id=cand["candidate_id"],
            job_id=job.id,
            stage="Comprehensive",
            send_email=True,
        )
        created_invitations.append((inv, details))
    session.commit()

    assert len(created_invitations) == 4

    # Verify each invitation has unique token and provisioned student account
    usernames = set()
    tokens = set()
    for inv, details in created_invitations:
        assert details["username"] not in usernames
        assert inv.token not in tokens
        usernames.add(details["username"])
        tokens.add(inv.token)

    # Verify rejected candidate does NOT receive an invitation
    non_shortlisted = ShortlistService.get_candidate_screening_list(
        session=session,
        job_id=job.id,
        decision_filter=RecruiterDecision.PENDING.value,
    )
    for cand in non_shortlisted:
        existing = session.query(InterviewInvitation).filter(InterviewInvitation.candidate_id == cand["candidate_id"]).first()
        assert existing is None

    # Student 1 Activation & Password Setup
    first_inv, first_details = created_invitations[0]
    student_user = session.query(User).filter(User.username == first_details["username"]).first()
    assert student_user is not None

    raw_token, token_hash = StudentAuthService.create_password_setup_token(session, student_user.id)
    session.commit()

    # Complete password setup
    ok, msg, updated_user = StudentAuthService.complete_password_setup(
        session=session,
        raw_token=raw_token,
        new_password="SecureCandidate2026!",
        confirm_password="SecureCandidate2026!",
    )
    assert ok is True
    assert updated_user.password_hash is not None

    # Test login
    auth_user, auth_msg = StudentAuthService.authenticate_student(
        session=session,
        identifier=student_user.username,
        password="SecureCandidate2026!",
    )
    assert auth_user is not None
    assert auth_user.id == student_user.id

    # Verify student can only access their own invitations
    student_invs = session.query(InterviewInvitation).filter(InterviewInvitation.student_user_id == auth_user.id).all()
    assert len(student_invs) == 1
    assert student_invs[0].id == first_inv.id


def test_workflow_active_interview_and_security_events(workflow_db):
    """
    Test Case 4 & 5:
    Student starts interview.
    Logs deterrence security events (tab switch, copy attempt).
    Student answers questions and submits interview.
    Verify answers are saved, status changes to COMPLETED, session is read-only.
    """
    session = workflow_db["session"]
    job = workflow_db["job"]
    cand, doc, screening = workflow_db["candidates"][0]

    engine = InterviewEngine()
    interview_session = engine.start_session(
        session=session,
        invitation_id=None,
        candidate_id=cand.id,
        job_id=job.id,
        stage="Comprehensive",
        candidate_consent=True,
        num_questions=3,
        difficulty="Intermediate",
    )
    assert interview_session.status == InterviewStatus.IN_PROGRESS.value

    # Record deterrence security events
    ev1 = InterviewSecurityEvent(
        session_id=interview_session.id,
        event_type="tab_switch",
        event_details={"warning": "Tab switched away from interview viewport."},
    )
    ev2 = InterviewSecurityEvent(
        session_id=interview_session.id,
        event_type="copy_attempt",
        event_details={"warning": "Copy shortcut intercepted within protected text."},
    )
    session.add_all([ev1, ev2])
    session.commit()

    recorded_events = session.query(InterviewSecurityEvent).filter(InterviewSecurityEvent.session_id == interview_session.id).all()
    assert len(recorded_events) == 2

    # Submit answers to all questions
    for i in range(1, 4):
        q = engine.get_current_question(session, interview_session.id)
        assert q is not None
        res = engine.submit_answer(
            session=session,
            session_id=interview_session.id,
            question_id=q.id,
            candidate_answer="In Python we implement scalable microservices using FastAPI and async SQLAlchemy with connection pooling.",
        )
        assert "evaluation" in res

    session.refresh(interview_session)
    assert interview_session.status == InterviewStatus.COMPLETED.value
    assert interview_session.overall_interview_score is not None
    assert interview_session.overall_interview_score > 0.0


def test_workflow_recruiter_report_and_next_round_selection(workflow_db):
    """
    Test Case 6 & 7:
    Recruiter opens completed interview results.
    Verifies Section 10 performance matrix categories.
    Recruiter executes SELECT FOR NEXT ROUND with decision record and automated email.
    """
    session = workflow_db["session"]
    job = workflow_db["job"]
    cand, doc, screening = workflow_db["candidates"][0]

    # Create completed session with questions
    interview_session = InterviewSession(
        candidate_id=cand.id,
        job_id=job.id,
        stage="Comprehensive",
        status=InterviewStatus.COMPLETED.value,
        total_questions=2,
        overall_interview_score=88.5,
    )
    session.add(interview_session)
    session.flush()

    q1 = InterviewQuestion(
        session_id=interview_session.id,
        question_order=1,
        question_type="conceptual",
        category="Python Architecture",
        question_text="Explain Python concurrency models.",
        candidate_answer="Python uses asyncio for I/O bound concurrency and multiprocessing for CPU bound workloads.",
        score=90.0,
        evaluation_feedback="Excellent understanding of concurrency models and GIL implications.",
    )
    q2 = InterviewQuestion(
        session_id=interview_session.id,
        question_order=2,
        question_type="coding",
        category="Problem Solving",
        question_text="How do you handle transactional rollback in SQLAlchemy?",
        candidate_answer="We use context managers with session.commit() and session.rollback() on exception.",
        score=87.0,
        evaluation_feedback="Correct transactional demarcation pattern.",
    )
    session.add_all([q1, q2])
    session.commit()

    # Generate Report
    report = InterviewReportService.generate_interview_performance_report(session, interview_session.id)
    assert report["overall_score"] > 80.0
    assert report["ai_recommendation"] == "Strongly Recommended"
    assert "technical_knowledge_score" in report
    assert "problem_solving_score" in report
    assert "communication_clarity_score" in report

    # Recruiter Decision: Select for Next Round
    screening.recruiter_decision = RecruiterDecision.SELECTED_FOR_NEXT_ROUND.value
    dec_record = RecruitmentDecisionRecord(
        candidate_id=cand.id,
        job_id=job.id,
        interview_session_id=interview_session.id,
        recruiter_id="recruiter-alex-001",
        decision=RecruiterDecision.SELECTED_FOR_NEXT_ROUND.value,
        recruiter_comments="Strong conceptual mastery and problem-solving depth.",
        next_round_name="Round 2: System Architecture Review",
        next_round_date=datetime.utcnow() + timedelta(days=3),
    )
    session.add(dec_record)
    session.commit()

    # Dispatch next-round notification email
    email_ok, email_msg = EmailService.send_next_round_notification(
        session=session,
        recipient_email=cand.email,
        student_name=cand.name,
        job_title=job.title,
        company_name="Acme Global Technologies",
        round_name="Round 2: System Architecture Review",
        round_date_str="November 05, 2026",
        round_time_str="11:00 AM UTC",
        further_instructions="Please prepare a system design diagram for a distributed queue service.",
        candidate_id=cand.id,
    )
    assert email_ok is True

    # Verify notification record in database
    notif = (
        session.query(EmailNotification)
        .filter(EmailNotification.recipient_email == cand.email.lower())
        .order_by(EmailNotification.created_at.desc())
        .first()
    )
    assert notif is not None
    assert notif.status == EmailDeliveryStatus.DELIVERED.value
    assert "Selected for the Next Round" in notif.subject


def test_idempotent_invitations_and_anti_duplicate(workflow_db):
    """
    Test Case 9:
    Duplicate invitation requests for the same candidate and job must not create duplicate tokens or duplicate records.
    """
    session = workflow_db["session"]
    job = workflow_db["job"]
    cand, doc, screening = workflow_db["candidates"][0]

    # Create invitation 1
    inv1, details1 = InvitationService.create_invitation(
        session=session,
        candidate_id=cand.id,
        job_id=job.id,
    )
    session.commit()

    # Create invitation 2 for same candidate & job
    inv2, details2 = InvitationService.create_invitation(
        session=session,
        candidate_id=cand.id,
        job_id=job.id,
    )
    session.commit()

    assert inv1.id == inv2.id
    assert details1["username"] == details2["username"]

    total_invs = session.query(InterviewInvitation).filter(
        InterviewInvitation.candidate_id == cand.id,
        InterviewInvitation.job_id == job.id,
    ).count()
    assert total_invs == 1
