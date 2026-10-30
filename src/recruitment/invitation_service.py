from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from config import settings
from src.database.models import (
    CandidateProfile,
    InterviewInvitation,
    InterviewStage,
    InterviewStatus,
    Job,
    RecruiterDecision,
    ResumeDocument,
    User,
)
from src.database.repository import DatabaseRepository
from src.recruitment.email_service import EmailService
from src.security.authentication import generate_secure_invitation_token
from src.security.student_auth_service import StudentAuthService


class InvitationService:
    """Creates, validates, and manages secure candidate interview invitations and student accounts."""

    @staticmethod
    def create_invitation(
        session: Session,
        candidate_id: str,
        job_id: str,
        stage: str = InterviewStage.COMPREHENSIVE.value,
        expire_hours: int = 72,
        recruiter_id: str | None = None,
        deadline_at: datetime | None = None,
        send_email: bool = True,
    ) -> tuple[InterviewInvitation, dict[str, Any]]:
        """
        Complete Automated Interview Invitation and Student Account Creation:
        Step 1: Retrieve student information from the database.
        Step 2: Check whether the student already has an account.
        Step 3: If an account exists, associate the interview with the existing student account.
        Step 4: Otherwise, create a new interview account with unique username (e.g. HS202600123).
        Step 5: Generate single-use password setup token and store its hash.
        Step 6: Build secure setup link and student login link.
        Step 7: Send interview invitation email to student.
        Ensures idempotency to avoid duplicate invitations.
        """
        # Step 1: Retrieve candidate & job info
        candidate = session.query(CandidateProfile).filter(CandidateProfile.id == candidate_id).first()
        job = session.query(Job).filter(Job.id == job_id).first()
        candidate_name = candidate.name if candidate and candidate.name else "Candidate"
        candidate_email = candidate.email if candidate and candidate.email else "candidate@example.com"
        job_title = job.title if job else "Applied Position"
        company_name = (
            job.campaign.company.name
            if job and job.campaign and job.campaign.company
            else "HireSphere AI"
        )

        # Retrieve resume document (application)
        doc = (
            session.query(ResumeDocument)
            .filter(ResumeDocument.candidate_id == candidate_id, ResumeDocument.job_id == job_id)
            .order_by(ResumeDocument.uploaded_at.desc())
            .first()
        )

        # Step 2, 3, 4: Provision or associate existing student account
        student_user = StudentAuthService.provision_student_account(
            session=session,
            candidate_id=candidate_id,
            name=candidate_name,
            email=candidate_email,
        )

        # Check if an invitation already exists for this candidate & job
        existing_inv = (
            session.query(InterviewInvitation)
            .filter(
                InterviewInvitation.candidate_id == candidate_id,
                InterviewInvitation.job_id == job_id,
            )
            .first()
        )

        token = generate_secure_invitation_token(candidate_id=candidate_id, job_id=job_id)
        expires_at = datetime.utcnow() + timedelta(hours=expire_hours)
        if not deadline_at:
            deadline_at = expires_at

        if existing_inv:
            invitation = existing_inv
            invitation.token = token
            invitation.stage = stage
            invitation.expires_at = expires_at
            invitation.deadline_at = deadline_at
            invitation.student_user_id = student_user.id
            invitation.username = student_user.username
            invitation.application_id = doc.id if doc else invitation.application_id
            invitation.invitation_status = InterviewStatus.INVITED.value
        else:
            invitation = InterviewInvitation(
                candidate_id=candidate_id,
                job_id=job_id,
                student_user_id=student_user.id,
                application_id=doc.id if doc else None,
                username=student_user.username,
                token=token,
                stage=stage,
                invitation_status=InterviewStatus.INVITED.value,
                invited_at=datetime.utcnow(),
                expires_at=expires_at,
                deadline_at=deadline_at,
                is_used=False,
            )
            session.add(invitation)

        # Update screening result recruiter decision to "Invited"
        if doc and doc.screening_result:
            doc.screening_result.recruiter_decision = RecruiterDecision.INVITED.value

        session.flush()

        # Step 5 & 6: Generate password setup token and URLs
        from config import _get_setting
        base_url = _get_setting("APP_BASE_URL", settings.APP_BASE_URL).rstrip("/")
        raw_setup_token, _ = StudentAuthService.create_password_setup_token(session, student_user.id, expire_hours=48)
        setup_url = f"{base_url}/Password_Setup?token={raw_setup_token}"
        login_url = f"{base_url}/Student_Login"

        # Step 7: Send invitation email
        email_sent = False
        email_msg = ""
        if send_email and candidate_email and "@" in candidate_email:
            deadline_str = deadline_at.strftime("%B %d, %Y at %I:%M %p UTC")
            email_sent, email_msg = EmailService.send_interview_invitation(
                session=session,
                recipient_email=candidate_email,
                student_name=candidate_name,
                username=student_user.username,
                setup_url=setup_url,
                login_url=login_url,
                job_title=job_title,
                company_name=company_name,
                deadline_str=deadline_str,
                invitation_id=invitation.id,
            )

        DatabaseRepository.log_audit_event(
            session=session,
            action="INTERVIEW_INVITATION_ISSUED",
            entity_type="InterviewInvitation",
            entity_id=invitation.id,
            user_id=recruiter_id,
            details={
                "candidate_id": candidate_id,
                "job_id": job_id,
                "student_username": student_user.username,
                "email_sent": email_sent,
            },
        )

        return invitation, {
            "username": student_user.username,
            "setup_url": setup_url,
            "login_url": login_url,
            "email_sent": email_sent,
            "email_message": email_msg,
            "raw_setup_token": raw_setup_token,
        }

    @staticmethod
    def validate_invitation_token(session: Session, token: str) -> dict[str, Any]:
        """Validate candidate token for expiry and replay prevention."""
        invitation = (
            session.query(InterviewInvitation)
            .filter(InterviewInvitation.token == token)
            .first()
        )

        if not invitation:
            return {"valid": False, "error": "Invalid invitation link."}

        if invitation.is_used:
            return {
                "valid": False,
                "error": "This interview invitation has already been completed.",
                "used_at": invitation.used_at,
            }

        if datetime.utcnow() > invitation.expires_at:
            return {
                "valid": False,
                "error": "This interview invitation token has expired. Please contact your recruiter.",
            }

        return {
            "valid": True,
            "invitation_id": invitation.id,
            "candidate_id": invitation.candidate_id,
            "candidate_name": invitation.candidate.name if invitation.candidate else "Candidate",
            "candidate_email": invitation.candidate.email if invitation.candidate else None,
            "job_id": invitation.job_id,
            "job_title": invitation.job.title if invitation.job else "Role",
            "company_name": invitation.job.campaign.company.name if invitation.job and invitation.job.campaign and invitation.job.campaign.company else "Company",
            "stage": invitation.stage,
            "duration_minutes": invitation.job.interview_duration_minutes if invitation.job else 30,
        }

    @staticmethod
    def get_invitations_for_job(session: Session, job_id: str) -> list[dict[str, Any]]:
        invitations = (
            session.query(InterviewInvitation)
            .filter(InterviewInvitation.job_id == job_id)
            .order_by(InterviewInvitation.created_at.desc())
            .all()
        )
        results = []
        for inv in invitations:
            # Check latest email delivery status
            latest_email = None
            if inv.email_notifications:
                latest_email = sorted(inv.email_notifications, key=lambda x: x.created_at, reverse=True)[0]

            results.append({
                "id": inv.id,
                "candidate_id": inv.candidate_id,
                "token": inv.token,
                "username": inv.username or (inv.student_user.username if inv.student_user else "N/A"),
                "candidate_name": inv.candidate.name if inv.candidate else "Candidate",
                "candidate_email": inv.candidate.email if inv.candidate else "N/A",
                "stage": inv.stage,
                "created_at": inv.created_at,
                "expires_at": inv.expires_at,
                "deadline_at": inv.deadline_at,
                "is_used": inv.is_used,
                "invitation_status": inv.invitation_status or ("Completed" if inv.is_used else ("Expired" if datetime.utcnow() > inv.expires_at else "Invited")),
                "status": "Completed" if inv.is_used else ("Expired" if datetime.utcnow() > inv.expires_at else "Active"),
                "email_status": latest_email.status if latest_email else "N/A",
            })
        return results

    @staticmethod
    def resend_invitation(
        session: Session,
        invitation_id: str,
        recruiter_id: str | None = None,
    ) -> tuple[bool, str]:
        """Regenerates setup token and resends interview invitation email."""
        invitation = session.query(InterviewInvitation).filter(InterviewInvitation.id == invitation_id).first()
        if not invitation:
            return False, "Invitation record not found."

        if not invitation.student_user:
            return False, "No student account associated with this invitation."

        student_user = invitation.student_user
        job = invitation.job
        company_name = job.campaign.company.name if job and job.campaign and job.campaign.company else "HireSphere AI"

        # Generate fresh setup token
        from config import _get_setting
        base_url = _get_setting("APP_BASE_URL", settings.APP_BASE_URL).rstrip("/")
        raw_setup_token, _ = StudentAuthService.create_password_setup_token(session, student_user.id, expire_hours=48)
        setup_url = f"{base_url}/Password_Setup?token={raw_setup_token}"
        login_url = f"{base_url}/Student_Login"
        deadline_str = invitation.deadline_at.strftime("%B %d, %Y at %I:%M %p UTC") if invitation.deadline_at else None

        sent, msg = EmailService.send_interview_invitation(
            session=session,
            recipient_email=student_user.email,
            student_name=student_user.name,
            username=student_user.username,
            setup_url=setup_url,
            login_url=login_url,
            job_title=job.title if job else "Applied Position",
            company_name=company_name,
            deadline_str=deadline_str,
            invitation_id=invitation.id,
            force_resend=True,
        )

        DatabaseRepository.log_audit_event(
            session=session,
            action="INTERVIEW_INVITATION_RESENT",
            entity_type="InterviewInvitation",
            entity_id=invitation.id,
            user_id=recruiter_id,
            details={"username": student_user.username, "email": student_user.email, "success": sent},
        )
        session.flush()  # Stage all changes; the caller (UI page) commits the transaction
        return sent, msg
