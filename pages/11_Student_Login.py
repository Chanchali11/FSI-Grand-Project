import streamlit as st

st.set_page_config(
    page_title="HireSphere AI — Student Interview Portal",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed",
)

from src.database.repository import get_db_session
from src.security.session_manager import SessionManager
from src.security.student_auth_service import StudentAuthService
from src.ui.layout import load_custom_css

load_custom_css()

# Session State for password visibility toggle
if "show_student_pwd" not in st.session_state:
    st.session_state.show_student_pwd = False
if "student_login_tab" not in st.session_state:
    st.session_state.student_login_tab = "login"

# Check if student is already logged in
current_student = SessionManager.get_current_student()
if current_student:
    st.markdown(
        f"""
        <div style="background: #151C33; border: 1px solid rgba(139, 92, 246, 0.25); border-radius: 14px; padding: 1.75rem; text-align: center; margin-top: 2rem;">
          <h3 style="color: #F8FAFC; margin: 0 0 8px 0; font-size: 1.25rem;">Already Signed In</h3>
          <p style="color: #94A3B8; font-size: 0.92rem; margin: 0 0 16px 0;">
            Logged in as <strong style="color: #F8FAFC;">{current_student['name']}</strong> (<code style="color: #8B5CF6;">{current_student['username']}</code>).
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📋 Go to Interview Dashboard →", type="primary", use_container_width=True):
            st.switch_page("pages/12_Student_Dashboard.py")
    with c2:
        if st.button("🚪 Logout", use_container_width=True):
            SessionManager.logout_student()
            st.rerun()
    st.stop()

# Student Portal Header
st.markdown(
    """
    <div style="text-align: center; margin-bottom: 2rem;">
      <div style="display: inline-block; width: 50px; height: 50px; border-radius: 12px; background: linear-gradient(135deg, #4F46E5, #6366F1); line-height: 50px; font-size: 26px; color: white; margin-bottom: 12px; box-shadow: 0 4px 14px rgba(79, 70, 229, 0.4);">
        🎓
      </div>
      <h1 style="color: #F8FAFC; font-size: 1.85rem; font-weight: 800; margin: 0; letter-spacing: -0.02em;">
        HireSphere AI — Student Interview Portal
      </h1>
      <p style="color: #94A3B8; font-size: 0.95rem; margin: 8px 0 0 0;">
        Sign in with your assigned interview username and password to access your virtual AI interview.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_login, tab_forgot = st.tabs(["🔑 Sign In", "❓ Forgot Password / Setup Link"])

with tab_login:
    st.markdown(
        """
        <div style="background: #151C33; border: 1px solid rgba(139, 92, 246, 0.25); border-radius: 14px; padding: 1.75rem; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4); margin-bottom: 1rem;">
          <h3 style="color: #F8FAFC; margin: 0 0 4px 0; font-size: 1.15rem; font-weight: 700;">Student Credentials</h3>
          <p style="color: #94A3B8; font-size: 0.82rem; margin: 0 0 16px 0;">Enter your username (e.g. HS202600101) or registered email.</p>
        """,
        unsafe_allow_html=True,
    )

    with st.form("student_login_form"):
        username_input = st.text_input("Username or Email", placeholder="e.g. HS202600101 or rahul@example.com")
        
        pwd_type = "default" if st.session_state.show_student_pwd else "password"
        password_input = st.text_input("Password", type=pwd_type, placeholder="Enter your chosen password")
        
        col_show, col_space = st.columns([1.5, 2])
        with col_show:
            show_pwd = st.checkbox("Show password", value=st.session_state.show_student_pwd, key="chk_show_pwd")
            if show_pwd != st.session_state.show_student_pwd:
                st.session_state.show_student_pwd = show_pwd

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        login_btn = st.form_submit_button("Sign In to Interview Portal →", type="primary", use_container_width=True)

        if login_btn:
            if not username_input.strip() or not password_input:
                st.error("Please enter both your username and password.")
            else:
                with st.spinner("Verifying credentials & loading interview assignments..."):
                    with get_db_session() as session:
                        user, msg = StudentAuthService.authenticate_student(
                            session=session,
                            identifier=username_input,
                            password=password_input,
                        )
                        if user:
                            SessionManager.set_current_student(user)
                            st.success("✓ Login successful! Redirecting to your interview dashboard...")
                            st.switch_page("pages/12_Student_Dashboard.py")
                        else:
                            st.error(f"✕ {msg}")

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div style="text-align: center; margin-top: 1rem;">
          <span style="color: #94A3B8; font-size: 0.85rem;">Haven't set your password yet? Check the invitation email or </span>
          <a href="Password_Setup" target="_self" style="color: #8B5CF6; font-size: 0.85rem; font-weight: 600; text-decoration: underline;">Set Password Here</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

with tab_forgot:
    st.markdown(
        """
        <div style="background: #151C33; border: 1px solid rgba(139, 92, 246, 0.25); border-radius: 14px; padding: 1.75rem; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4); margin-bottom: 1rem;">
          <h3 style="color: #F8FAFC; margin: 0 0 4px 0; font-size: 1.15rem; font-weight: 700;">Request Password Reset Link</h3>
          <p style="color: #94A3B8; font-size: 0.82rem; margin: 0 0 16px 0;">
            Enter your registered email address or username. A single-use secure setup link will be dispatched to your inbox.
          </p>
        """,
        unsafe_allow_html=True,
    )

    with st.form("forgot_password_form"):
        forgot_ident = st.text_input("Registered Email Address or Username", placeholder="e.g. rahul@example.com")
        send_reset = st.form_submit_button("Send Password Setup Link →", type="primary", use_container_width=True)

        if send_reset:
            if not forgot_ident.strip():
                st.error("Please enter your registered email or username.")
            else:
                with get_db_session() as session:
                    ok, msg = StudentAuthService.request_new_setup_link(session, forgot_ident.strip())
                    st.info(f"📧 {msg}")

    st.markdown("</div>", unsafe_allow_html=True)
