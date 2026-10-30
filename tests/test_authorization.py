from src.database.models import Company, Recruiter, RecruitmentCampaign, UserRole
from src.database.repository import get_db_session, init_db
from src.security.authorization import AuthorizationService, Permission
from src.security.session_manager import AuthUser


def test_rbac_permission_matrix():
    """Verify role-based access control permission matrices."""
    # Admin Permissions
    admin_user = AuthUser(
        id="admin-1",
        name="Admin User",
        email="admin@test.com",
        role=UserRole.ADMIN.value,
        company_id="company-1",
        company_name="Acme",
        login_time=None,
    )
    assert AuthorizationService.has_permission(admin_user, Permission.CREATE_JOB) is True
    assert AuthorizationService.has_permission(admin_user, Permission.MANAGE_USERS) is True
    assert AuthorizationService.has_permission(admin_user, Permission.MANAGE_PRIVACY_PURGE) is True
    assert AuthorizationService.has_permission(admin_user, Permission.VIEW_AUDIT_LOGS) is True

    # Recruiter Permissions
    recruiter_user = AuthUser(
        id="recruiter-1",
        name="Recruiter User",
        email="recruiter@test.com",
        role=UserRole.RECRUITER.value,
        company_id="company-1",
        company_name="Acme",
        login_time=None,
    )
    assert AuthorizationService.has_permission(recruiter_user, Permission.CREATE_JOB) is True
    assert AuthorizationService.has_permission(recruiter_user, Permission.UPLOAD_RESUMES) is True
    assert AuthorizationService.has_permission(recruiter_user, Permission.INVITE_CANDIDATE) is True
    assert AuthorizationService.has_permission(recruiter_user, Permission.MANAGE_USERS) is False
    assert AuthorizationService.has_permission(recruiter_user, Permission.MANAGE_PRIVACY_PURGE) is False

    # Hiring Manager Permissions
    hm_user = AuthUser(
        id="hm-1",
        name="Hiring Manager",
        email="hm@test.com",
        role=UserRole.HIRING_MANAGER.value,
        company_id="company-1",
        company_name="Acme",
        login_time=None,
    )
    assert AuthorizationService.has_permission(hm_user, Permission.VIEW_SCREENING) is True
    assert AuthorizationService.has_permission(hm_user, Permission.UPDATE_DECISION) is True
    assert AuthorizationService.has_permission(hm_user, Permission.CREATE_JOB) is False
    assert AuthorizationService.has_permission(hm_user, Permission.UPLOAD_RESUMES) is False

    # Candidate Permissions
    cand_user = AuthUser(
        id="cand-1",
        name="Candidate User",
        email="cand@test.com",
        role=UserRole.CANDIDATE.value,
        company_id="company-1",
        company_name="Acme",
        login_time=None,
    )
    assert AuthorizationService.has_permission(cand_user, Permission.ATTEND_INTERVIEW) is True
    assert AuthorizationService.has_permission(cand_user, Permission.VIEW_SCREENING) is False
    assert AuthorizationService.has_permission(cand_user, Permission.CREATE_JOB) is False


def test_audit_logging_and_retrieval():
    """Verify tamper-evident audit log creation and company filtering."""
    init_db()
    with get_db_session() as session:
        user = AuthUser(
            id="recruiter-test-1",
            name="Audited Recruiter",
            email="audit_recruiter@hiresphere.ai",
            role=UserRole.RECRUITER.value,
            company_id="comp-audit-test-123",
            company_name="Audit Corp",
            login_time=None,
        )

        event = AuthorizationService.log_audit_action(
            session=session,
            action="JOB_CANDIDATE_SHORTLISTED",
            entity_type="CandidateProfile",
            entity_id="cand-12345",
            details={"notes": "Strong Python and distributed systems background"},
            user=user,
        )
        assert event.id is not None
        assert event.action == "JOB_CANDIDATE_SHORTLISTED"
        assert event.company_id == "comp-audit-test-123"

        # Retrieve audit trail
        trail = AuthorizationService.get_audit_trail(session, company_id="comp-audit-test-123", limit=10)
        assert len(trail) >= 1
        assert any(e.entity_id == "cand-12345" for e in trail)
