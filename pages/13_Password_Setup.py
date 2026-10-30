import streamlit as st

st.set_page_config(
    page_title="HireSphere AI — Password Setup",
    page_icon="🔑",
    layout="centered",
    initial_sidebar_state="collapsed",
)

from src.database.repository import get_db_session
from src.security.session_manager import SessionManager
from src.security.student_auth_service import StudentAuthService
from src.ui.layout import load_custom_css

load_custom_css()

# Parse token from query parameters
query_params = st.query_params
token = query_params.get("token", "")

st.markdown(
    """
    <div style="text-align: center; margin-bottom: 2rem;">
      <div style="display: inline-block; width: 48px; height: 48px; border-radius: 12px; background: linear-gradient(135deg, #4F46E5, #06B6D4); line-height: 48px; font-size: 24px; color: white; margin-bottom: 12px; box-shadow: 0 4px 14px rgba(79, 70, 229, 0.4);">
        ⚡
      </div>
      <h1 style="color: #F8FAFC; font-size: 1.8rem; font-weight: 800; margin: 0; letter-spacing: -0.02em;">
        HireSphere AI — Set Your Password
      </h1>
      <p style="color: #94A3B8; font-size: 0.95rem; margin: 8px 0 0 0;">
        Create a secure password to access your AI-powered candidate interview room.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not token:
    st.markdown(
        """
        <div style="background: rgba(244, 63, 94, 0.12); border: 1px solid rgba(244, 63, 94, 0.35); border-radius: 12px; padding: 1.5rem; text-align: center; margin-bottom: 1.5rem;">
          <h4 style="color: #FB7185; margin: 0 0 8px 0; font-size: 1.05rem;">Missing Setup Token</h4>
          <p style="color: #94A3B8; font-size: 0.88rem; margin: 0;">
            No password setup token was detected in your invitation URL. Please verify the link in your email or enter your token below.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    manual_token = st.text_input("Enter Setup Token from Email:", placeholder="hs-setup-token...")
    if manual_token:
        st.query_params["token"] = manual_token.strip()
        st.rerun()

    st.markdown("<hr style='border: 0; border-top: 1px solid #1E293B; margin: 2rem 0;'>", unsafe_allow_html=True)
    st.markdown("<h4 style='color: #F8FAFC; font-size: 1rem;'>Need a new password setup link?</h4>", unsafe_allow_html=True)
    with st.form("request_link_form"):
        req_id = st.text_input("Registered Email Address or Username", placeholder="e.g. rahul@example.com or HS202600101")
        if st.form_submit_button("Send New Setup Link →", type="primary", use_container_width=True):
            if req_id.strip():
                with get_db_session() as session:
                    ok, msg = StudentAuthService.request_new_setup_link(session, req_id.strip())
                    st.info(msg)
            else:
                st.error("Please enter your registered email address or username.")
    st.stop()

# Validate token against database
with get_db_session() as session:
    token_status = StudentAuthService.validate_setup_token(session, token)

if not token_status["valid"]:
    st.markdown(
        f"""
        <div style="background: rgba(244, 63, 94, 0.12); border: 1px solid rgba(244, 63, 94, 0.35); border-radius: 12px; padding: 1.5rem; text-align: center; margin-bottom: 1.5rem;">
          <h4 style="color: #FB7185; margin: 0 0 8px 0; font-size: 1.05rem;">Token Verification Notice</h4>
          <p style="color: #F8FAFC; font-size: 0.9rem; margin: 0 0 10px 0;">{token_status['error']}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🎓 Go to Student Login", type="primary", use_container_width=True):
            st.switch_page("pages/11_Student_Login.py")
    with col_btn2:
        if st.button("🔄 Request New Link", use_container_width=True):
            st.query_params.clear()
            st.rerun()

    st.stop()

# Valid Token: Display Password Creation Form
st.markdown(
    f"""
    <div style="background: #151C33; border: 1px solid rgba(139, 92, 246, 0.25); border-radius: 14px; padding: 1.5rem 1.75rem; margin-bottom: 1.5rem; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);">
      <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #232D4B; padding-bottom: 12px; margin-bottom: 14px;">
        <span style="color: #94A3B8; font-size: 0.82rem; text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em;">Student Identity</span>
        <span style="background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.35); padding: 2px 10px; border-radius: 9999px; font-size: 0.75rem; font-weight: 700;">
          ✓ Token Verified
        </span>
      </div>
      <div style="font-size: 1.1rem; font-weight: 700; color: #F8FAFC; margin-bottom: 4px;">
        {token_status['name']}
      </div>
      <div style="font-size: 0.88rem; color: #94A3B8;">
        Assigned Username: <strong style="color: #8B5CF6; font-family: monospace;">{token_status['username']}</strong> &bull; Email: {token_status['email']}
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.form("student_password_setup_form"):
    st.markdown("<p style='color: #CBD5E1; font-size: 0.88rem; margin-bottom: 12px;'><strong>Password Policy:</strong> Minimum 8 characters, at least 1 uppercase letter, 1 lowercase letter, and 1 number.</p>", unsafe_allow_html=True)

    pwd = st.text_input("Enter New Password", type="password", placeholder="Create a strong password")
    confirm_pwd = st.text_input("Confirm New Password", type="password", placeholder="Re-enter your password")

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    submit_pwd = st.form_submit_button("Set Password & Proceed to Login →", type="primary", use_container_width=True)

    if submit_pwd:
        if not pwd or not confirm_pwd:
            st.error("Please enter and confirm your new password.")
        else:
            with get_db_session() as session:
                success, msg, student_user = StudentAuthService.complete_password_setup(
                    session=session,
                    raw_token=token,
                    new_password=pwd,
                    confirm_password=confirm_pwd,
                )
                if success and student_user:
                    SessionManager.set_current_student(student_user)
                    st.success("🎉 " + msg)
                    st.balloons()
                    st.query_params.clear()
                    st.switch_page("pages/12_Student_Dashboard.py")
                else:
                    st.error(msg)
