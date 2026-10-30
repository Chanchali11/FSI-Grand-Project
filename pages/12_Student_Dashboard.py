from datetime import datetime
import streamlit as st

st.set_page_config(
    page_title="HireSphere AI — Student Interview Dashboard",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from src.database.models import (
    CandidateProfile,
    InterviewInvitation,
    InterviewSession,
    InterviewStatus,
    Job,
    User,
)
from src.database.repository import get_db_session
from src.security.session_manager import SessionManager
from src.ui.layout import load_custom_css

load_custom_css()

# Enforce student authentication
student = SessionManager.get_current_student()
if not student:
    st.warning("🔒 Please sign in with your student credentials to view your assigned interviews.")
    if st.button("Go to Student Login →", type="primary"):
        st.switch_page("pages/11_Student_Login.py")
    st.stop()

# Top Header / Welcome Banner
st.markdown(
    f"""
    <div style="background: linear-gradient(135deg, #151C33 0%, #1E1B4B 100%); border: 1px solid rgba(139, 92, 246, 0.25); border-radius: 14px; padding: 1.5rem 2rem; margin-bottom: 1.5rem; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
      <div>
        <div style="font-size: 0.8rem; color: #8B5CF6; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">
          Student Interview Portal &bull; Verified Candidate
        </div>
        <h1 style="color: #F8FAFC; font-size: 1.65rem; font-weight: 800; margin: 0; letter-spacing: -0.02em;">
          Welcome, {student['name']}
        </h1>
        <p style="color: #94A3B8; font-size: 0.88rem; margin: 4px 0 0 0;">
          Username: <strong style="color: #A5B4FC; font-family: monospace;">{student['username']}</strong> &bull; Email: {student['email']}
        </p>
      </div>
      <div>
        <span style="background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.35); padding: 6px 14px; border-radius: 9999px; font-size: 0.82rem; font-weight: 700;">
          ● Authenticated Session Active
        </span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Top Action row
col_nav1, col_nav2 = st.columns([4, 1])
with col_nav2:
    if st.button("🚪 Logout", use_container_width=True):
        SessionManager.logout_student()
        st.success("Signed out successfully.")
        st.switch_page("pages/11_Student_Login.py")

# Query assigned interviews for this student user
with get_db_session() as session:
    # Match by student_user_id or candidate_profile_id
    query = session.query(InterviewInvitation).filter(
        (InterviewInvitation.student_user_id == student["id"])
        | (InterviewInvitation.candidate_id == student.get("candidate_profile_id"))
    )
    invitations = query.order_by(InterviewInvitation.created_at.desc()).all()

    if not invitations:
        st.markdown(
            """
            <div style="background: #151C33; border: 1px solid #232D4B; border-radius: 12px; padding: 2.5rem; text-align: center; margin: 1.5rem 0;">
              <div style="font-size: 2.5rem; margin-bottom: 12px;">📋</div>
              <h3 style="color: #F8FAFC; margin: 0 0 6px 0;">No Active Interviews Assigned</h3>
              <p style="color: #94A3B8; font-size: 0.9rem; max-width: 500px; margin: 0 auto 16px;">
                You do not have any pending virtual interviews assigned at this moment. You will receive an email notification when a recruiter shortlists your profile.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.stop()

    st.markdown(
        f"<h3 style='color: #F8FAFC; font-size: 1.15rem; font-weight: 700; margin: 1rem 0 0.75rem 0;'>Assigned Interviews ({len(invitations)})</h3>",
        unsafe_allow_html=True,
    )

    for inv in invitations:
        job = inv.job
        company_name = job.campaign.company.name if job and job.campaign and job.campaign.company else "Acme Technologies"
        job_title = job.title if job else "Software Engineer"
        duration = job.interview_duration_minutes if job else 30
        q_count = 5

        # Check existing sessions for this invitation
        existing_session = (
            session.query(InterviewSession)
            .filter(InterviewSession.invitation_id == inv.id)
            .order_by(InterviewSession.started_at.desc())
            .first()
        )

        # Determine precise status
        is_expired = inv.deadline_at and datetime.utcnow() > inv.deadline_at
        if inv.is_used or (existing_session and existing_session.status == InterviewStatus.COMPLETED.value):
            status_label = "COMPLETED"
            status_color = "#34D399"
            status_bg = "rgba(16, 185, 129, 0.15)"
            status_border = "rgba(16, 185, 129, 0.35)"
        elif is_expired:
            status_label = "EXPIRED"
            status_color = "#FB7185"
            status_bg = "rgba(244, 63, 94, 0.15)"
            status_border = "rgba(244, 63, 94, 0.35)"
        elif existing_session and existing_session.status == InterviewStatus.IN_PROGRESS.value:
            status_label = "IN_PROGRESS"
            status_color = "#FBBF24"
            status_bg = "rgba(245, 158, 11, 0.15)"
            status_border = "rgba(245, 158, 11, 0.35)"
        else:
            status_label = "NOT_STARTED"
            status_color = "#8B5CF6"
            status_bg = "rgba(139, 92, 246, 0.15)"
            status_border = "rgba(139, 92, 246, 0.35)"

        deadline_display = inv.deadline_at.strftime("%B %d, %Y at %I:%M %p UTC") if inv.deadline_at else "No expiration configured"

        st.markdown(
            f"""
            <div style="background: #151C33; border: 1px solid rgba(139, 92, 246, 0.22); border-radius: 14px; padding: 1.5rem; margin-bottom: 1.25rem; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);">
              <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px; margin-bottom: 14px;">
                <div>
                  <div style="font-size: 0.8rem; color: #8B5CF6; font-weight: 700; text-transform: uppercase;">{company_name}</div>
                  <h3 style="color: #F8FAFC; margin: 2px 0 6px 0; font-size: 1.25rem; font-weight: 700;">Job Applied: {job_title}</h3>
                  <div style="color: #94A3B8; font-size: 0.85rem;">
                    Stage: <strong style="color: #CBD5E1;">{inv.stage} Assessment</strong> &bull;
                    Duration: <strong style="color: #CBD5E1;">{duration} minutes</strong> &bull;
                    Questions: <strong style="color: #CBD5E1;">{q_count} Questions</strong>
                  </div>
                </div>
                <div>
                  <span style="background: {status_bg}; color: {status_color}; border: 1px solid {status_border}; padding: 4px 12px; border-radius: 9999px; font-size: 0.8rem; font-weight: 700; text-transform: uppercase;">
                    ● {status_label}
                  </span>
                </div>
              </div>
              <div style="background: #19223C; border-radius: 8px; padding: 10px 14px; font-size: 0.82rem; color: #94A3B8; margin-bottom: 14px;">
                ⏰ <strong>Interview Deadline:</strong> <span style="color: {'#FB7185' if is_expired else '#F8FAFC'}; font-weight: 600;">{deadline_display}</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_act1, col_act2, col_act3 = st.columns([2, 2, 3])
        with col_act1:
            if status_label == "COMPLETED":
                st.button("✓ Interview Completed", disabled=True, key=f"btn_comp_{inv.id}", use_container_width=True)
            elif is_expired:
                st.button("✕ Link Expired", disabled=True, key=f"btn_exp_{inv.id}", use_container_width=True)
            else:
                btn_text = "▶ Resume Interview" if status_label == "IN_PROGRESS" else "▶ Start Interview"
                if st.button(btn_text, type="primary", key=f"btn_start_{inv.id}", use_container_width=True):
                    # Store selected invitation token and candidate context into session
                    st.session_state.invitation_token = inv.token
                    st.session_state.student_selected_invitation_id = inv.id
                    st.session_state.student_candidate_id = inv.candidate_id
                    st.session_state.student_job_id = inv.job_id
                    st.switch_page("pages/7_Virtual_Interview.py")

        with col_act2:
            with st.expander("📖 View Instructions", expanded=False):
                st.markdown(
                    """
                    <div style="font-size: 0.85rem; color: #CBD5E1; line-height: 1.55;">
                      <p><strong>Guidelines for your Virtual AI Interview:</strong></p>
                      <ul>
                        <li>Use Chrome, Edge, or a modern browser with microphone access enabled.</li>
                        <li>The interactive AI interviewer (Sophia) will read each question aloud.</li>
                        <li>You can speak your response via your microphone or type in the response area.</li>
                        <li>Real-time speech recognition converts your audio into text.</li>
                        <li>Questions are adapted specifically from your uploaded resume.</li>
                        <li>You cannot restart or re-attempt questions once finalized.</li>
                      </ul>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
