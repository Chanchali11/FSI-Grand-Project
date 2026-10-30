import streamlit as st

from src.database.models import Company, Recruiter, UserRole
from src.database.repository import get_db_session
from src.security.session_manager import AuthUser, SessionManager, hash_password
from src.ui.layout import render_header, setup_sidebar_context

# Initialize sidebar context
context = setup_sidebar_context(require_login=False)

render_header(
    title="Create Recruiter Account",
    subtitle="Register your enterprise organization to screen resumes and run virtual AI interviews",
    breadcrumbs=["Hirexp Ai", "Authentication", "Sign Up"],
)

user = SessionManager.get_current_user()

if user:
    st.success(f"You are already signed in as **{user.name}** ({user.email}).")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 Go to Command Center", type="primary", use_container_width=True):
            st.switch_page("app.py")
    with col2:
        if st.button("🚪 Sign Out", use_container_width=True):
            SessionManager.logout()
            st.rerun()
else:
    st.markdown(
        """
        <div class="hs-card" style="max-width: 580px; margin: 1.5rem auto 2rem; padding: 2.2rem; border-top: 4px solid #06B6D4;">
          <h3 style="margin-top: 0; color: #F8FAFC; font-weight: 800; font-size: 1.35rem; letter-spacing: -0.02em;">
            Join Hirexp Ai
          </h3>
          <p style="color: #94A3B8; font-size: 0.9rem; line-height: 1.55; margin-bottom: 0;">
            Create a verified recruiter account to configure custom job rubrics, parse candidate resumes in bulk, and automate avatar-powered interviews.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("hirexp_dedicated_signup_form"):
        col_name, col_comp = st.columns(2)
        with col_name:
            full_name = st.text_input("Full Name", placeholder="e.g. Eleanor Vance")
        with col_comp:
            company_name = st.text_input("Company / Organization", placeholder="e.g. Apex Technologies")

        col_email, col_role = st.columns(2)
        with col_email:
            email = st.text_input("Work Email Address", placeholder="e.g. eleanor@apextech.io")
        with col_role:
            role_choice = st.selectbox("Role Category", options=["Recruiter", "Administrator"])

        col_pwd1, col_pwd2 = st.columns(2)
        with col_pwd1:
            pwd = st.text_input("Password", type="password", placeholder="Min. 8 characters")
        with col_pwd2:
            confirm_pwd = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")

        terms = st.checkbox("I agree to the GDPR data privacy governance policy and terms of service", value=True)

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        submit_btn = st.form_submit_button("Complete Registration & Enter Platform →", type="primary", use_container_width=True)

        if submit_btn:
            if not full_name.strip() or not email.strip() or not pwd:
                st.error("Please fill in all mandatory fields.")
            elif not terms:
                st.error("You must accept the privacy policy to register.")
            elif pwd != confirm_pwd:
                st.error("Passwords do not match. Please re-enter.")
            elif len(pwd) < 8:
                st.error("Password must be at least 8 characters long.")
            else:
                clean_email = email.strip().lower()
                clean_comp = company_name.strip() or "Independent Organization"

                with get_db_session() as session:
                    existing = session.query(Recruiter).filter(Recruiter.email == clean_email).first()
                    if existing:
                        st.error("An account with this email address already exists. Please sign in.")
                    else:
                        company = session.query(Company).filter(Company.name == clean_comp).first()
                        if not company:
                            company = Company(
                                name=clean_comp,
                                domain=clean_email.split("@")[-1] if "@" in clean_email else None,
                                industry="Software & Cloud Infrastructure",
                            )
                            session.add(company)
                            session.flush()

                        assigned_role = UserRole.ADMIN.value if role_choice == "Administrator" else UserRole.RECRUITER.value
                        new_recruiter = Recruiter(
                            company_id=company.id,
                            name=full_name.strip(),
                            email=clean_email,
                            password_hash=hash_password(pwd),
                            role=assigned_role,
                        )
                        session.add(new_recruiter)
                        session.commit()

                        auth_user = AuthUser(
                            id=new_recruiter.id,
                            name=new_recruiter.name,
                            email=new_recruiter.email,
                            role=new_recruiter.role,
                            company_id=company.id,
                            company_name=company.name,
                        )
                        st.session_state[SessionManager.SESSION_KEY] = {
                            "id": auth_user.id,
                            "name": auth_user.name,
                            "email": auth_user.email,
                            "role": auth_user.role,
                            "company_id": auth_user.company_id,
                            "company_name": auth_user.company_name,
                            "login_time": auth_user.login_time,
                        }
                        st.success(f"Welcome to Hirexp Ai, {new_recruiter.name}! Your account is now active.")
                        st.switch_page("app.py")

    col_ret1, col_ret2 = st.columns([1, 1])
    with col_ret1:
        st.markdown("<p style='font-size: 0.88rem; color: #94A3B8; margin-top: 10px;'>Already have an account?</p>", unsafe_allow_html=True)
    with col_ret2:
        if st.button("Sign In to Existing Account →", use_container_width=True):
            st.switch_page("app.py")
