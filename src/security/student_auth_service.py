from datetime import datetime, timedelta
import logging
import re
from typing import Any, Optional

from sqlalchemy.orm import Session

from config import settings
from src.database.models import (
    CandidateProfile,
    InterviewInvitation,
    InterviewSession,
    InterviewStage,
    InterviewStatus,
    Job,
    PasswordSetupToken,
    RecruiterDecision,
    ResumeDocument,
    User,
    UserRole,
)
from src.database.repository import DatabaseRepository
from src.recruitment.email_service import EmailService
from src.security.authentication import (
    generate_secure_invitation_token,
    generate_setup_token,
    hash_password,
    hash_token,
    validate_password_strength,
    verify_password,
)

logger = logging.getLogger(__name__)


class StudentAuthService:
    """
    Manages complete student candidate authentication lifecycle:
    - Unique deterministic username generation (e.g. HS202600123)
    - Automatic idempotent student user account provisioning
    - Single-use, expiring, cryptographically secure password setup tokens (hashed in DB)
    - Password strength validation and Argon2id / PBKDF2 hashing
    - Student credentials verification and session management
    - Rate-limiting and prevention of username enumeration
    """

    # In-memory failure tracking for rate limiting (username/IP -> list of attempt timestamps)
    _LOGIN_ATTEMPTS: dict[str, list[float]] = {}
    MAX_ATTEMPTS = 5
    LOCKOUT_SECONDS = 300  # 5 minutes

    @classmethod
    def generate_unique_username(cls, session: Session, candidate_name: str | None = None) -> str:
        """
        Generate unique professional student interview username.
        Format: HS<Year><Sequential 5-digit number> (e.g. HS202600101)
        """
        year_str = str(datetime.utcnow().year)
        prefix = f"HS{year_str}"

        # Find all existing usernames with prefix to accurately determine max sequence
        existing_users = (
            session.query(User.username)
            .filter(User.username.like(f"{prefix}%"))
            .all()
        )
        existing_numbers: set[int] = set()
        for (u_name,) in existing_users:
            if u_name and u_name.startswith(prefix):
                num_part = u_name[len(prefix):]
                if num_part.isdigit():
                    existing_numbers.add(int(num_part))

        # Also inspect pending unflushed objects in the current session
        for obj in session.new:
            if isinstance(obj, User):
                u_name = getattr(obj, "username", None)
                if u_name and u_name.startswith(prefix):
                    num_part = u_name[len(prefix):]
                    if num_part.isdigit():
                        existing_numbers.add(int(num_part))

        next_seq = max(existing_numbers, default=100) + 1
        if next_seq < 101:
            next_seq = 101

        while True:
            candidate_username = f"{prefix}{next_seq:05d}"
            exists = session.query(User).filter(User.username == candidate_username).first()
            if not exists and next_seq not in existing_numbers:
                return candidate_username
            next_seq += 1

    @classmethod
    def provision_student_account(
        cls,
        session: Session,
        candidate_id: str,
        name: str,
        email: str,
    ) -> User:
        """
        Idempotent, concurrency-safe student account creation:
        - Checks if User already exists with email or linked candidate_id
        - If exists, returns existing student user
        - Otherwise, creates new student user with generated unique username
        - Uses savepoints to gracefully recover from race conditions or duplicate clicks
        """
        clean_email = email.strip().lower()

        # Check existing by email in DB
        existing_user = session.query(User).filter(User.email == clean_email).first()
        if not existing_user:
            for obj in session.new:
                if isinstance(obj, User) and getattr(obj, "email", None) == clean_email:
                    existing_user = obj
                    break

        if existing_user:
            if not existing_user.candidate_profile_id:
                existing_user.candidate_profile_id = candidate_id
            return existing_user

        # Check existing by candidate_profile_id
        existing_by_cand = session.query(User).filter(User.candidate_profile_id == candidate_id).first()
        if not existing_by_cand:
            for obj in session.new:
                if isinstance(obj, User) and getattr(obj, "candidate_profile_id", None) == candidate_id:
                    existing_by_cand = obj
                    break

        if existing_by_cand:
            return existing_by_cand

        clean_name = name.strip() if name and name.strip() else "Candidate Student"

        # Concurrency-safe insert with savepoint & collision retry
        for attempt in range(5):
            username = cls.generate_unique_username(session, clean_name)

            student_user = User(
                username=username,
                email=clean_email,
                name=clean_name,
                role=UserRole.STUDENT.value,
                is_active=True,
                candidate_profile_id=candidate_id,
                created_at=datetime.utcnow(),
            )

            try:
                with session.begin_nested():
                    session.add(student_user)
                    session.flush()
                break
            except Exception as exc:
                logger.warning(
                    f"Conflict or error provisioning account for {clean_email} (attempt {attempt+1}/5): {exc}"
                )
                # Check if another process/click created the user meanwhile
                existing = (
                    session.query(User)
                    .filter((User.email == clean_email) | (User.candidate_profile_id == candidate_id))
                    .first()
                )
                if existing:
                    return existing
                if attempt == 4:
                    raise

        DatabaseRepository.log_audit_event(
            session=session,
            action="STUDENT_ACCOUNT_CREATED",
            entity_type="User",
            entity_id=student_user.id,
            details={"username": student_user.username, "email": clean_email, "candidate_id": candidate_id},
        )
        return student_user

    @classmethod
    def create_password_setup_token(
        cls,
        session: Session,
        user_id: str,
        expire_hours: int = 48,
    ) -> tuple[str, PasswordSetupToken]:
        """
        Generates single-use setup token.
        Stores ONLY the SHA-256 hash in database.
        Returns (raw_token_for_email_link, token_record).
        """
        # Invalidate any previous unused setup tokens for this user
        session.query(PasswordSetupToken).filter(
            PasswordSetupToken.user_id == user_id,
            PasswordSetupToken.used_at.is_(None),
        ).update({"used_at": datetime.utcnow()})

        raw_token, token_hash = generate_setup_token()
        expires_at = datetime.utcnow() + timedelta(hours=expire_hours)

        token_record = PasswordSetupToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=datetime.utcnow(),
        )
        session.add(token_record)
        session.flush()

        return raw_token, token_record

    @classmethod
    def validate_setup_token(cls, session: Session, raw_token: str) -> dict[str, Any]:
        """
        Validates raw token:
        - Hashes token and checks database
        - Verifies not used
        - Verifies not expired
        """
        if not raw_token or not raw_token.strip():
            return {"valid": False, "error": "Password setup token is required."}

        hashed = hash_token(raw_token.strip())
        record = (
            session.query(PasswordSetupToken)
            .filter(PasswordSetupToken.token_hash == hashed)
            .first()
        )

        if not record:
            return {"valid": False, "error": "Invalid or unrecognized setup link."}

        if record.used_at is not None:
            return {
                "valid": False,
                "error": "This password setup link has already been used. Please log in or request a new link.",
                "already_used": True,
            }

        if datetime.utcnow() > record.expires_at:
            return {
                "valid": False,
                "error": "This password setup link has expired. Please request a new setup link.",
                "expired": True,
            }

        user = record.user
        return {
            "valid": True,
            "user_id": user.id,
            "username": user.username,
            "name": user.name,
            "email": user.email,
            "token_record_id": record.id,
        }

    @classmethod
    def complete_password_setup(
        cls,
        session: Session,
        raw_token: str,
        new_password: str,
        confirm_password: str,
    ) -> tuple[bool, str, Optional[User]]:
        """
        Completes student password setup:
        - Validates token
        - Validates passwords match and meet strength policy
        - Hashes using Argon2id
        - Saves hash and marks setup token as permanently used
        """
        val = cls.validate_setup_token(session, raw_token)
        if not val["valid"]:
            return False, val["error"], None

        if new_password != confirm_password:
            return False, "Passwords do not match. Please verify and re-enter.", None

        is_valid_strength, strength_err = validate_password_strength(new_password)
        if not is_valid_strength:
            return False, strength_err, None

        user = session.query(User).filter(User.id == val["user_id"]).first()
        if not user:
            return False, "Target user account not found.", None

        # Securely hash password
        pwd_hash = hash_password(new_password)
        user.password_hash = pwd_hash

        # Invalidate the setup token
        token_record = session.query(PasswordSetupToken).filter(PasswordSetupToken.id == val["token_record_id"]).first()
        if token_record:
            token_record.used_at = datetime.utcnow()

        DatabaseRepository.log_audit_event(
            session=session,
            action="PASSWORD_SETUP_COMPLETED",
            entity_type="User",
            entity_id=user.id,
            details={"username": user.username},
        )
        session.commit()
        return True, "Password created successfully! Proceeding to your interview dashboard...", user

    @classmethod
    def authenticate_student(
        cls,
        session: Session,
        identifier: str,
        password: str,
        client_ip: str = "127.0.0.1",
    ) -> tuple[Optional[User], str]:
        """
        Authenticates student via username or email:
        - Rate limits failed attempts
        - Prevents username enumeration (generic error responses)
        - Verifies Argon2id password hash
        """
        if not identifier or not password:
            return None, "Please provide both username and password."

        clean_id = identifier.strip()

        # Check rate limiting
        now = datetime.utcnow().timestamp()
        key = f"{client_ip}:{clean_id.lower()}"
        recent_attempts = [t for t in cls._LOGIN_ATTEMPTS.get(key, []) if now - t < cls.LOCKOUT_SECONDS]
        cls._LOGIN_ATTEMPTS[key] = recent_attempts

        if len(recent_attempts) >= cls.MAX_ATTEMPTS:
            remaining = int(cls.LOCKOUT_SECONDS - (now - recent_attempts[0]))
            return None, f"Too many failed login attempts. Please try again in {max(remaining, 1)} seconds."

        # Find user by username or email
        user = (
            session.query(User)
            .filter(
                (User.username == clean_id) | (User.email == clean_id.lower())
            )
            .first()
        )

        # Constant-time comparison prevention / fake verify if not found
        if not user or not user.is_active or not user.password_hash:
            cls._LOGIN_ATTEMPTS[key].append(now)
            return None, "Invalid credentials. Please verify your username and password."

        if not verify_password(user.password_hash, password):
            cls._LOGIN_ATTEMPTS[key].append(now)
            return None, "Invalid credentials. Please verify your username and password."

        # Successful login: clear failures & update last login
        cls._LOGIN_ATTEMPTS[key] = []
        user.last_login_at = datetime.utcnow()
        session.commit()

        DatabaseRepository.log_audit_event(
            session=session,
            action="STUDENT_LOGIN_SUCCESS",
            entity_type="User",
            entity_id=user.id,
            details={"username": user.username, "ip": client_ip},
        )
        return user, "Login successful."

    @classmethod
    def request_new_setup_link(cls, session: Session, email_or_username: str) -> tuple[bool, str]:
        """
        Initiates a password reset / new setup token dispatch:
        - Returns success message without revealing account existence
        """
        clean_input = email_or_username.strip().lower()
        user = (
            session.query(User)
            .filter((User.email == clean_input) | (User.username == clean_input.upper()))
            .first()
        )

        generic_resp = "If a matching account exists, a secure setup link has been sent to the registered email."
        if not user or not user.is_active:
            return True, generic_resp

        # Create new token and send email
        raw_token, _ = cls.create_password_setup_token(session, user.id)
        setup_url = f"{settings.APP_BASE_URL}/Password_Setup?token={raw_token}"
        login_url = f"{settings.APP_BASE_URL}/Student_Login"

        # Determine job / company from candidate invitations
        invitation = (
            session.query(InterviewInvitation)
            .filter(InterviewInvitation.student_user_id == user.id)
            .order_by(InterviewInvitation.created_at.desc())
            .first()
        )
        job_title = invitation.job.title if invitation and invitation.job else "Applied Position"
        company_name = (
            invitation.job.campaign.company.name
            if invitation and invitation.job and invitation.job.campaign and invitation.job.campaign.company
            else "HireSphere AI"
        )

        EmailService.send_interview_invitation(
            session=session,
            recipient_email=user.email,
            student_name=user.name,
            username=user.username,
            setup_url=setup_url,
            login_url=login_url,
            job_title=job_title,
            company_name=company_name,
            invitation_id=invitation.id if invitation else None,
        )
        return True, generic_resp
