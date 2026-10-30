from src.security.authentication import (
    generate_secure_invitation_token,
    hash_password,
    verify_password,
)


def test_password_hash_and_verification():
    """Verify standard password hashing and verification succeeds."""
    password = "SuperSecretPassword2026!"
    pw_hash = hash_password(password)

    assert pw_hash != password
    assert "$" in pw_hash
    assert verify_password(pw_hash, password) is True
    assert verify_password(pw_hash, "WrongPassword") is False
    assert verify_password(pw_hash, "") is False


def test_malformed_password_hashes_reject_fallback():
    """Ensure malformed/corrupted hashes do not allow demo password fallback bypasses."""
    malformed_hashes = [
        "not_a_valid_hash",
        "invalid$hash$with$too$many$parts",
        "badhash",
        "",
        None,
        "singlepartwithoutdollar",
        "$",
        "$$",
    ]

    demo_passwords = ["admin123", "recruiter123", "password", "123456"]

    for bad_hash in malformed_hashes:
        for demo_pw in demo_passwords:
            # Must strictly reject and never return True
            assert verify_password(bad_hash, demo_pw) is False


def test_invitation_token_generation():
    """Verify invitation tokens are high entropy and format-compliant."""
    token1 = generate_secure_invitation_token("candidate-1", "job-1")
    token2 = generate_secure_invitation_token("candidate-1", "job-1")

    assert token1.startswith("hs-inv-")
    assert token2.startswith("hs-inv-")
    assert token1 != token2
    assert len(token1) > 40


def test_recruiter_authentication_and_rbac():
    """Verify recruiter authentication against the database and RBAC checks."""
    from src.database.repository import get_db_session, init_db
    from src.security.session_manager import SessionManager

    init_db()
    with get_db_session() as session:
        # Valid recruiter login
        recruiter = SessionManager.authenticate(session, "recruiter@hiresphere.ai", "RecruiterPass2026!")
        assert recruiter is not None
        assert recruiter.email == "recruiter@hiresphere.ai"
        assert recruiter.role == "recruiter"
        assert recruiter.is_recruiter() is True
        assert recruiter.is_admin() is False

        # Valid admin login
        admin = SessionManager.authenticate(session, "admin@hiresphere.ai", "AdminPass2026!")
        assert admin is not None
        assert admin.email == "admin@hiresphere.ai"
        assert admin.role == "admin"
        assert admin.is_admin() is True
        assert admin.is_recruiter() is True

        # Invalid password
        bad_pw = SessionManager.authenticate(session, "recruiter@hiresphere.ai", "WrongPassword!")
        assert bad_pw is None

        # Non-existent user
        non_user = SessionManager.authenticate(session, "nobody@nowhere.com", "SomePassword!")
        assert non_user is None

