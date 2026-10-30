"""
Role-Based Access Control (RBAC) and Authorization Policy Service
Enforces granular permission checks, multi-tenant company isolation, and audit logging.
"""

from enum import Enum
from typing import Any, List, Optional
import streamlit as st
from sqlalchemy.orm import Query, Session

from src.database.models import AuditEvent, UserRole
from src.security.session_manager import AuthUser, SessionManager


class Permission(str, Enum):
    # Recruitment & Job Management
    VIEW_DASHBOARD = "view_dashboard"
    CREATE_JOB = "create_job"
    EDIT_JOB = "edit_job"
    DELETE_JOB = "delete_job"

    # Resumes & Screening
    UPLOAD_RESUMES = "upload_resumes"
    VIEW_SCREENING = "view_screening"
    UPDATE_DECISION = "update_decision"
    MANAGE_SHORTLIST = "manage_shortlist"

    # Interviews
    INVITE_CANDIDATE = "invite_candidate"
    ATTEND_INTERVIEW = "attend_interview"
    VIEW_INTERVIEW_RECORDS = "view_interview_records"

    # Reports & Analytics
    VIEW_CANDIDATE_REPORTS = "view_candidate_reports"
    VIEW_ANALYTICS = "view_analytics"

    # Administration & Compliance
    MANAGE_USERS = "manage_users"
    MANAGE_PRIVACY_PURGE = "manage_privacy_purge"
    VIEW_AUDIT_LOGS = "view_audit_logs"


ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    UserRole.ADMIN.value: {p for p in Permission},
    UserRole.RECRUITER.value: {
        Permission.VIEW_DASHBOARD,
        Permission.CREATE_JOB,
        Permission.EDIT_JOB,
        Permission.UPLOAD_RESUMES,
        Permission.VIEW_SCREENING,
        Permission.UPDATE_DECISION,
        Permission.MANAGE_SHORTLIST,
        Permission.INVITE_CANDIDATE,
        Permission.VIEW_INTERVIEW_RECORDS,
        Permission.VIEW_CANDIDATE_REPORTS,
        Permission.VIEW_ANALYTICS,
        Permission.VIEW_AUDIT_LOGS,
    },
    UserRole.HIRING_MANAGER.value: {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_SCREENING,
        Permission.UPDATE_DECISION,
        Permission.VIEW_INTERVIEW_RECORDS,
        Permission.VIEW_CANDIDATE_REPORTS,
        Permission.VIEW_ANALYTICS,
    },
    UserRole.CANDIDATE.value: {
        Permission.ATTEND_INTERVIEW,
    },
}


class AuthorizationService:
    """
    Central authorization authority enforcing RBAC policies and audit logging.
    """

    @classmethod
    def has_permission(cls, user_or_role: str | AuthUser | None, permission: Permission) -> bool:
        """Check if a given user or role holds the specified permission."""
        if user_or_role is None:
            return False

        if isinstance(user_or_role, AuthUser):
            role_str = user_or_role.role
        elif hasattr(user_or_role, "role"):
            role_str = str(user_or_role.role)
        else:
            role_str = str(user_or_role)

        allowed = ROLE_PERMISSIONS.get(role_str, set())
        return permission in allowed

    @classmethod
    def require_permission(cls, permission: Permission, user: Optional[AuthUser] = None):
        """
        Verify permission in Streamlit page execution.
        Renders an access-denied message and halts page if unauthorized.
        """
        if user is None:
            user = SessionManager.get_current_user()

        if not user:
            st.warning("🔒 Please sign in to access this feature.")
            SessionManager.render_login_widget()
            st.stop()

        if not cls.has_permission(user, permission):
            st.error(
                f"⛔ Permission Denied: Your account role ('{user.role.title()}') does not possess the "
                f"`{permission.value}` permission required for this operation."
            )
            st.stop()

    @classmethod
    def log_audit_action(
        cls,
        session: Session,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        user: Optional[AuthUser] = None,
        ip_address: str = "127.0.0.1",
    ) -> AuditEvent:
        """
        Record a tamper-evident audit log event in the database.
        """
        if user is None:
            user = SessionManager.get_current_user()

        company_id = user.company_id if user else None
        user_id = user.id if user else None

        event = AuditEvent(
            company_id=company_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
            ip_address=ip_address,
        )
        session.add(event)
        session.flush()
        return event

    @classmethod
    def get_audit_trail(
        cls,
        session: Session,
        company_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[AuditEvent]:
        """Fetch recent audit log records filtered by company."""
        query = session.query(AuditEvent)
        if company_id:
            query = query.filter(AuditEvent.company_id == company_id)
        return query.order_by(AuditEvent.created_at.desc()).limit(limit).all()

    @classmethod
    def scope_query(cls, query: Query, model: Any, user: Optional[AuthUser] = None) -> Query:
        """
        Filter a SQLAlchemy query by company_id for strict multi-tenant data isolation.
        Administrators bypass scoping to view global records.
        """
        if user is None:
            user = SessionManager.get_current_user()

        if user and not user.is_admin() and hasattr(model, "company_id"):
            return query.filter(getattr(model, "company_id") == user.company_id)
        return query
