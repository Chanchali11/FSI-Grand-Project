from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import streamlit as st
from sqlalchemy.orm import Session

from config import settings
from src.database.models import Company, Recruiter, UserRole
from src.security.authentication import hash_password, verify_password


@dataclass
class AuthUser:
    id: str
    name: str
    email: str
    role: str
    company_id: str
    company_name: str
    login_time: datetime

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN.value

    def is_recruiter(self) -> bool:
        return self.role in (UserRole.RECRUITER.value, UserRole.ADMIN.value)

    def is_hiring_manager(self) -> bool:
        return self.role in (UserRole.HIRING_MANAGER.value, UserRole.ADMIN.value)

    def is_student(self) -> bool:
        return self.role == UserRole.STUDENT.value


class SessionManager:
    """Handles recruiter and student session lifecycle, authentication, and role authorization."""

    SESSION_KEY = "hs_current_user"
    STUDENT_SESSION_KEY = "hs_current_student"

    @classmethod
    def init_student_session(cls):
        """Initialize student session state keys."""
        if cls.STUDENT_SESSION_KEY not in st.session_state:
            st.session_state[cls.STUDENT_SESSION_KEY] = None

    @classmethod
    def get_current_student(cls) -> Optional[dict]:
        """Retrieve active authenticated student candidate from session state."""
        cls.init_student_session()
        student_dict = st.session_state.get(cls.STUDENT_SESSION_KEY)
        if not student_dict:
            return None

        login_time = student_dict.get("login_time")
        if login_time and datetime.utcnow() - login_time > timedelta(hours=settings.SESSION_EXPIRE_HOURS):
            cls.logout_student()
            return None
        return student_dict

    @classmethod
    def set_current_student(cls, user_obj, candidate_profile_id: str | None = None):
        """Set active authenticated student session."""
        cls.init_student_session()
        st.session_state[cls.STUDENT_SESSION_KEY] = {
            "id": user_obj.id,
            "username": user_obj.username,
            "name": user_obj.name,
            "email": user_obj.email,
            "role": user_obj.role,
            "candidate_profile_id": candidate_profile_id or user_obj.candidate_profile_id,
            "login_time": datetime.utcnow(),
        }

    @classmethod
    def logout_student(cls):
        """Clear active student session."""
        st.session_state[cls.STUDENT_SESSION_KEY] = None
        if "student_selected_invitation_id" in st.session_state:
            del st.session_state["student_selected_invitation_id"]

    @classmethod
    def init_session_state(cls):
        """Initialize session state keys."""
        if cls.SESSION_KEY not in st.session_state:
            st.session_state[cls.SESSION_KEY] = None

    @classmethod
    def get_current_user(cls) -> Optional[AuthUser]:
        """Retrieve active authenticated user from session state if not expired."""
        cls.init_session_state()
        user_dict = st.session_state.get(cls.SESSION_KEY)
        if not user_dict:
            return None

        # Check session expiry
        login_time = user_dict.get("login_time")
        if login_time and datetime.utcnow() - login_time > timedelta(hours=settings.SESSION_EXPIRE_HOURS):
            cls.logout()
            return None

        return AuthUser(
            id=user_dict["id"],
            name=user_dict["name"],
            email=user_dict["email"],
            role=user_dict["role"],
            company_id=user_dict["company_id"],
            company_name=user_dict["company_name"],
            login_time=user_dict["login_time"],
        )

    @classmethod
    def is_authenticated(cls) -> bool:
        """Check if a valid authenticated user session exists."""
        return cls.get_current_user() is not None

    @classmethod
    def authenticate(cls, session: Session, email: str, password: str) -> Optional[AuthUser]:
        """Verify user credentials against the database."""
        if not email or not password:
            return None

        email_clean = email.strip().lower()
        recruiter = session.query(Recruiter).filter(Recruiter.email == email_clean).first()
        if not recruiter or not recruiter.is_active:
            return None

        if not verify_password(recruiter.password_hash, password):
            return None

        company = session.query(Company).filter(Company.id == recruiter.company_id).first()
        company_name = company.name if company else "Global Workspace"

        auth_user = AuthUser(
            id=recruiter.id,
            name=recruiter.name,
            email=recruiter.email,
            role=recruiter.role or UserRole.RECRUITER.value,
            company_id=recruiter.company_id,
            company_name=company_name,
            login_time=datetime.utcnow(),
        )

        # Store in session state
        st.session_state[cls.SESSION_KEY] = {
            "id": auth_user.id,
            "name": auth_user.name,
            "email": auth_user.email,
            "role": auth_user.role,
            "company_id": auth_user.company_id,
            "company_name": auth_user.company_name,
            "login_time": auth_user.login_time,
        }

        return auth_user

    @classmethod
    def logout(cls):
        """Clear the current authenticated user session."""
        st.session_state[cls.SESSION_KEY] = None

    @classmethod
    def require_auth(cls, allowed_roles: Optional[list[str]] = None) -> Optional[AuthUser]:
        """
        Enforce authentication & RBAC for a page.
        Halts page rendering and displays the login modal if unauthorized.
        """
        cls.init_session_state()
        user = cls.get_current_user()

        if not user:
            st.warning("🔒 Recruiter authentication required to access this module.")
            cls.render_login_widget()
            st.stop()

        if allowed_roles and user.role not in allowed_roles:
            st.error(f"⛔ Access Denied. Your role ('{user.role}') does not have permission to view this resource.")
            st.stop()

        return user

    @classmethod
    def render_login_widget(cls):
        """Render a streamlined login card in Streamlit."""
        from src.database.repository import get_db_session

        st.markdown(
            """
            <div class="hs-card" style="max-width: 480px; margin: 2rem auto; padding: 2.2rem; border-top: 4px solid #8B5CF6; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6);">
              <h3 style="margin-top: 0; color: #F8FAFC; font-weight: 800; font-size: 1.3rem; letter-spacing: -0.02em;">Hirexp Recruiter Portal</h3>
              <p style="color: #94A3B8; font-size: 0.92rem; line-height: 1.55; margin-bottom: 0;">
                Sign in or create a recruiter account to manage campaigns, jobs, candidate screenings, and AI avatar interviews.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab_login, tab_signup = st.tabs(["🔑 Sign In", "📝 Sign Up"])

        with tab_login:
            with st.form("hirexp_login_form"):
                col_mail, col_pwd = st.columns(2)
                with col_mail:
                    login_email = st.text_input("Recruiter Email", placeholder="recruiter@hiresphere.ai")
                with col_pwd:
                    login_password = st.text_input("Password", type="password", placeholder="••••••••")

                submit = st.form_submit_button("Sign In to Hirexp Ai", type="primary", width='stretch')

                if submit:
                    with get_db_session() as session:
                        user = cls.authenticate(session, login_email, login_password)
                        if user:
                            st.success(f"Welcome back, {user.name} ({user.role.title()})!")
                            st.rerun()
                        else:
                            st.error("Invalid email or password. Please verify your credentials.")

            with st.expander("ℹ️ Demo & Development Credentials", expanded=False):
                st.markdown(
                    """
                    - **Recruiter:** `recruiter@hiresphere.ai` &nbsp;|&nbsp; Password: `RecruiterPass2026!`
                    - **Admin:** `admin@hiresphere.ai` &nbsp;|&nbsp; Password: `AdminPass2026!`
                    """
                )

        with tab_signup:
            with st.form("hirexp_signup_form"):
                st.markdown("<p style='font-size: 0.88rem; color: #CBD5E1; margin-bottom: 12px;'>Register as a new recruiter on the Hirexp Ai platform.</p>", unsafe_allow_html=True)
                new_name = st.text_input("Full Name", placeholder="e.g. Sarah Connor")
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    new_company = st.text_input("Company Name", placeholder="e.g. Cyberdyne Systems")
                with col_c2:
                    new_email = st.text_input("Business Email", placeholder="e.g. sarah@cyberdyne.io")

                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    new_pwd = st.text_input("New Password", type="password", placeholder="Min. 8 characters")
                with col_p2:
                    confirm_pwd = st.text_input("Confirm Password", type="password", placeholder="Repeat password")

                signup_submit = st.form_submit_button("Create Recruiter Account", type="primary", width='stretch')

                if signup_submit:
                    if not new_name.strip() or not new_email.strip() or not new_pwd:
                        st.error("Please fill in all required fields.")
                    elif new_pwd != confirm_pwd:
                        st.error("Passwords do not match. Please re-enter.")
                    elif len(new_pwd) < 8:
                        st.error("Password must be at least 8 characters long.")
                    else:
                        from src.database.models import Company, Recruiter, UserRole
                        from src.security.session_manager import hash_password
                        with get_db_session() as session:
                            # Check if email already registered
                            existing = session.query(Recruiter).filter(Recruiter.email == new_email.strip().lower()).first()
                            if existing:
                                st.error("An account with this email address already exists. Please Sign In.")
                            else:
                                # Find or create company
                                company_name_clean = new_company.strip() or "Independent Organization"
                                company = session.query(Company).filter(Company.name == company_name_clean).first()
                                if not company:
                                    company = Company(
                                        name=company_name_clean,
                                        domain=new_email.split("@")[-1] if "@" in new_email else None,
                                        industry="Technology & Recruitment",
                                    )
                                    session.add(company)
                                    session.flush()

                                # Create recruiter
                                new_recruiter = Recruiter(
                                    company_id=company.id,
                                    name=new_name.strip(),
                                    email=new_email.strip().lower(),
                                    password_hash=hash_password(new_pwd),
                                    role=UserRole.RECRUITER.value,
                                )
                                session.add(new_recruiter)
                                session.commit()

                                # Log them in immediately
                                auth_user = AuthUser(
                                    id=new_recruiter.id,
                                    name=new_recruiter.name,
                                    email=new_recruiter.email,
                                    role=new_recruiter.role,
                                    company_id=company.id,
                                    company_name=company.name,
                                )
                                st.session_state[cls.SESSION_KEY] = {
                                    "id": auth_user.id,
                                    "name": auth_user.name,
                                    "email": auth_user.email,
                                    "role": auth_user.role,
                                    "company_id": auth_user.company_id,
                                    "company_name": auth_user.company_name,
                                    "login_time": auth_user.login_time,
                                }
                                st.success("Account created successfully! Welcome to Hirexp Ai.")
                                st.rerun()

    @classmethod
    def render_sidebar_user_profile(cls):
        """Render logged-in recruiter card in sidebar with sign out action."""
        user = cls.get_current_user()
        if not user:
            return

        badge_bg = "rgba(16, 185, 129, 0.2)" if user.is_admin() else "rgba(139, 92, 246, 0.2)"
        badge_color = "#34D399" if user.is_admin() else "#C084FC"
        badge_border = "rgba(16, 185, 129, 0.4)" if user.is_admin() else "rgba(139, 92, 246, 0.4)"
        initial = (user.name[0] if user.name else "U").upper()
        
        st.sidebar.markdown(
            f"""
            <div style="background: #19223C; border: 1px solid #2D3A60; border-radius: 10px; padding: 10px 12px; margin-bottom: 14px; box-shadow: 0 1px 4px rgba(0, 0, 0, 0.4);">
              <div style="display: flex; align-items: center; gap: 10px;">
                <div style="width: 34px; height: 34px; border-radius: 50%; background: linear-gradient(135deg, #8B5CF6, #6366F1); display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 0.85rem; flex-shrink: 0; box-shadow: 0 2px 8px rgba(139, 92, 246, 0.4);">
                  {initial}
                </div>
                <div style="flex-grow: 1; min-width: 0;">
                  <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: 700; color: #FFFFFF; font-size: 0.86rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{user.name}</span>
                    <span style="font-size: 0.68rem; padding: 2px 8px; border-radius: 9999px; background: {badge_bg}; color: {badge_color}; border: 1px solid {badge_border}; font-weight: 700; letter-spacing: 0.04em;">
                      {user.role.upper()}
                    </span>
                  </div>
                  <div style="font-size: 0.74rem; color: #94A3B8; margin-top: 2px;">
                    🏢 {user.company_name}
                  </div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.sidebar.button("🚪 Sign Out", key="hs_btn_signout", width='stretch'):
            cls.logout()
            st.rerun()
