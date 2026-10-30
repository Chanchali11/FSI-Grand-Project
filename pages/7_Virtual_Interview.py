import html
from datetime import datetime
import streamlit as st

from src.avatar.avatar_component import render_avatar_component
from src.avatar.speech_service import SpeechService
from src.database.models import (
    CandidateProfile,
    InterviewInvitation,
    InterviewQuestion,
    InterviewSecurityEvent,
    InterviewSession,
    InterviewStatus,
    Job,
    ParsedResumeData,
    ResumeDocument,
)
import json
from src.database.repository import DatabaseRepository, get_db_session, init_db
init_db()
from src.interview.interview_engine import InterviewEngine
from src.recruitment.invitation_service import InvitationService
from src.reports.interview_report_service import InterviewReportService
from src.security.interview_security_shield import render_interview_security_shield, render_camera_shutdown
from src.security.privacy_manager import PrivacyManager
from src.security.session_manager import SessionManager
from src.ui.layout import load_custom_css, render_badge

st.set_page_config(
    page_title="Hirexp AI — Virtual Interview Room",
    page_icon="🎙",
    layout="wide",
    initial_sidebar_state="collapsed",
)
load_custom_css()

# ── 1. ISOLATE STUDENT INTERVIEW & ENFORCE ZERO-SCROLL VIEWPORT ──
st.markdown(
    """
    <style>
      [data-testid="stSidebar"], [data-testid="collapsedControl"] {
        display: none !important;
      }
      #MainMenu { visibility: hidden; height: 0 !important; }
      header { visibility: hidden; height: 0 !important; }
      footer { visibility: hidden; height: 0 !important; }

      /* Compact single-window cockpit styling */
      .block-container {
        padding-top: 0.65rem !important;
        padding-bottom: 1.25rem !important;
        padding-left: 1.25rem !important;
        padding-right: 1.25rem !important;
        max-width: 100% !important;
      }
      [style*="background: #FFF"] *, [style*="background: white"] *, [style*="background: #F8FAFC"] * {
        color: #0F172A !important;
      }
      [style*="background: #FFF"] p, [style*="background: white"] p, [style*="background: #F8FAFC"] p {
        color: #475569 !important;
      }
      [style*="background: #FFF"] [style*="color: #15803D"] {
        color: #15803D !important;
      }
      [style*="background: #FFF"] [style*="color: #991B1B"] {
        color: #991B1B !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── 2. EXIT SCREEN (AFTER COMPLETING INTERVIEW, STUDENT IS SAFELY OUT) ──
if st.session_state.get("interview_finished_exit"):
    render_camera_shutdown()
    st.markdown(
        """
        <div class="hs-card" style="text-align: center; padding: 2.5rem 1.5rem; margin: 2rem auto; max-width: 600px; border-top: 4px solid #22C55E;">
          <div style="font-size: 3.2rem; margin-bottom: 8px;">✅</div>
          <h2 style="color: #4ADE80 !important; margin: 0 0 8px 0; font-size: 1.5rem; font-weight: 800;">Interview Successfully Completed!</h2>
          <p style="color: #CBD5E1 !important; font-size: 0.92rem; line-height: 1.5; margin: 0 auto 1.5rem auto;">
            Your interview responses and AI evaluation report have been securely recorded and submitted to the recruitment team.
            You have been safely signed out of the platform.
          </p>
          <div style="background: #19223C; border: 1px solid #232D4B; border-radius: 8px; padding: 10px; font-size: 0.84rem; color: #CBD5E1 !important;">
            🔒 All camera and microphone sensors have been deactivated.<br>
            You may now safely close this browser window.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# ── 3. STRICT CANDIDATE ACCESS CONTROL ──
student = SessionManager.get_current_student()
token_in_url = st.query_params.get("token", "").strip()

if "invitation_token" not in st.session_state:
    st.session_state.invitation_token = token_in_url
elif token_in_url and not st.session_state.invitation_token:
    st.session_state.invitation_token = token_in_url

# If student is logged in, auto-bind their assigned invitation token
if student and not st.session_state.invitation_token:
    with get_db_session() as s_init:
        s_inv = (
            s_init.query(InterviewInvitation)
            .filter(
                (InterviewInvitation.student_user_id == student["id"]) |
                (InterviewInvitation.candidate_id == student.get("candidate_profile_id"))
            )
            .filter(InterviewInvitation.is_used == False)
            .order_by(InterviewInvitation.created_at.desc())
            .first()
        )
        if s_inv:
            st.session_state.invitation_token = s_inv.token

# Block unauthorized visitors (Recruiters or uninvited guests without token)
if not student and not st.session_state.invitation_token:
    st.markdown(
        """
        <div class="hs-card" style="padding: 2.2rem; text-align: center; margin: 2rem auto; max-width: 580px; border-left: 4px solid #EF4444;">
          <div style="font-size: 2.5rem; margin-bottom: 8px;">🔒</div>
          <h2 style="color: #F87171 !important; margin: 0 0 8px 0; font-size: 1.3rem;">Student Interview Portal — Restricted</h2>
          <p style="color: #CBD5E1 !important; font-size: 0.9rem; line-height: 1.5; margin: 0 auto 1.3rem auto;">
            This Virtual AI Interview Room is exclusively for invited student candidates.
            Recruiters cannot take candidate interviews. Please log in through the Student Portal or use your unique invitation email link.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col_c1, col_c2 = st.columns([1, 1])
    with col_c1:
        if st.button("🎓 Student Login", type="primary", use_container_width=True):
            st.switch_page("pages/11_Student_Login.py")
    with col_c2:
        if st.button("🚪 Return to Sign Up / Home", use_container_width=True):
            st.switch_page("pages/0_Sign_Up.py")
    st.stop()

# Session State Initialization
if "active_session_id" not in st.session_state:
    st.session_state.active_session_id = None
if "avatar_state" not in st.session_state:
    st.session_state.avatar_state = "idle"
if "last_feedback" not in st.session_state:
    st.session_state.last_feedback = None
if "avatar_persona" not in st.session_state:
    st.session_state.avatar_persona = "Sophia (Lead AI Interviewer)"
if "interview_difficulty" not in st.session_state:
    st.session_state.interview_difficulty = "Intermediate"
if "interview_num_questions" not in st.session_state:
    st.session_state.interview_num_questions = 5
if "camera_position" not in st.session_state:
    st.session_state.camera_position = "right"  # Default to Extreme Right side

# ── 4. CANDIDATE SETUP & CONSENT (BEFORE SESSION STARTS) ──
if not st.session_state.active_session_id:
    # Compact Header Bar
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #1E1B4B 0%, #312E81 60%, #4F46E5 100%); border-radius: 10px; padding: 10px 16px; margin-bottom: 12px; color: #FFFFFF; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
          <div>
            <div style="font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; color: #C7D2FE; font-weight: 700;">Hirexp AI &bull; Proctored Candidate Assessment</div>
            <h2 style="margin: 2px 0 0 0; font-size: 1.25rem; font-weight: 800; letter-spacing: -0.02em;">Virtual AI Interview Room Setup</h2>
          </div>
          <div style="font-size: 0.8rem; color: #E0E7FF; background: rgba(0, 0, 0, 0.25); padding: 4px 10px; border-radius: 6px;">
            Single-Window Mode &bull; Zero Scroll
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_verif, col_guide = st.columns([3, 2])

    with col_verif:
        st.markdown(
            """
            <div class="hs-card" style="margin-bottom: 10px; padding: 12px 16px;">
              <h3 style="margin: 0 0 4px 0; font-size: 1rem; font-weight: 700; color: #F8FAFC !important;">Candidate Verification & Consent</h3>
              <p style="margin: 0; font-size: 0.8rem; color: #94A3B8 !important;">Verify your access token and acknowledge proctoring monitoring</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        token_input = st.text_input(
            "Personal Interview Access Token",
            value=st.session_state.invitation_token,
            placeholder="hs-inv-...",
            help="Found in your interview invitation email.",
        )

        c_diff, c_avatar = st.columns(2)
        with c_diff:
            st.session_state.interview_difficulty = st.selectbox(
                "Assessment Track",
                options=["Intermediate", "Advanced", "Beginner"],
                index=0,
            )
        with c_avatar:
            st.session_state.avatar_persona = st.selectbox(
                "AI Avatar Interviewer",
                options=["Sophia (Lead AI Interviewer)"],
                index=0,
            )

        privacy_info = PrivacyManager.get_privacy_notice()
        with st.expander("📋 Review Candidate Privacy Notice", expanded=False):
            st.write(f"**Purposes:** {', '.join(privacy_info['purposes'])}")
            st.write(f"**Non-Discrimination Policy:** {privacy_info['protected_characteristics_policy']}")
            st.write(f"**Data Retention Window:** {privacy_info['retention_policy']}")

        consent_given = st.checkbox(
            "I agree to camera/audio integrity monitoring (Single-person verification & protected tab focus).",
            value=True,
        )

        st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
        if st.button("🚀 Enter Virtual Interview Room", type="primary", use_container_width=True):
            if not token_input.strip():
                st.error("Please enter a valid invitation token.")
            elif not consent_given:
                st.error("You must provide consent to proceed with the interview.")
            else:
                with get_db_session() as session:
                    val = InvitationService.validate_invitation_token(session, token_input.strip())
                    if not val["valid"]:
                        st.error(val["error"])
                    else:
                        engine = InterviewEngine()
                        interview_sess = engine.start_session(
                            session=session,
                            invitation_id=val["invitation_id"],
                            candidate_id=val["candidate_id"],
                            job_id=val["job_id"],
                            stage=val["stage"],
                            candidate_consent=True,
                            num_questions=st.session_state.interview_num_questions,
                            difficulty=st.session_state.interview_difficulty,
                        )
                        st.session_state.active_session_id = interview_sess.id
                        st.session_state.invitation_token = token_input.strip()
                        st.session_state.avatar_state = "speaking"
                        st.success("Session initialized! Welcome to your interview.")
                        st.rerun()

    with col_guide:
        st.markdown(
            """
            <div class="hs-card" style="margin-bottom: 8px; text-align: center; padding: 10px 14px;">
              <h3 style="margin: 0; font-size: 0.95rem; font-weight: 700; color: #F8FAFC !important;">AI Virtual Interviewer</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_avatar_component(state="idle", message="Hello! Welcome to your virtual interview room. I will guide you through your assessment.", height=240)
        st.markdown(
            """
            <div style="font-size: 0.78rem; color: #94A3B8 !important; margin-top: 8px; line-height: 1.45;">
              <strong style="color: #F8FAFC !important;">Exam Integrity Rules:</strong>
              <ul style="margin: 4px 0; padding-left: 16px;">
                <li><strong>Single Person:</strong> Only one candidate allowed in camera frame.</li>
                <li><strong>Protected Tab:</strong> Switching browser tabs will automatically terminate the session.</li>
                <li><strong>Camera Feed:</strong> Positioned in the extreme corner for continuous proctoring.</li>
              </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ── 5. ACTIVE VIRTUAL INTERVIEW IN PROGRESS ──
else:
    with get_db_session() as session:
        interview_session = session.query(InterviewSession).filter(InterviewSession.id == st.session_state.active_session_id).first()
        if not interview_session:
            st.error("Active interview session not found.")
            st.session_state.active_session_id = None
            st.stop()

        candidate = interview_session.candidate
        job = session.query(Job).filter(Job.id == interview_session.job_id).first()
        company_name = job.campaign.company.name if job and job.campaign and job.campaign.company else "Company"

        engine = InterviewEngine()
        current_q = engine.get_current_question(session, interview_session.id)

        # ── REAL-TIME PROCTORING EVENT INGESTION & DATABASE PERSISTENCE ──
        sync_event_param = st.query_params.get("sync_event")
        if sync_event_param:
            try:
                ev_data = json.loads(sync_event_param)
                ev_type = ev_data.get("event_type", "security_event")
                ev_details = ev_data.get("details", {})
                DatabaseRepository.log_security_event(
                    session=session,
                    session_id=interview_session.id,
                    event_type=ev_type,
                    details=ev_details,
                )
                session.commit()
            except Exception:
                pass

        is_completed = interview_session.status == InterviewStatus.COMPLETED.value or not current_q

        # Candidate & Stage Info Bar
        q_idx = interview_session.current_question_index + 1
        total_q = interview_session.total_questions or 5

        # ── 6. INTERVIEW COMPLETED: FINAL PERFORMANCE REPORT ──
        if is_completed:
            render_camera_shutdown()
            # Check if session has integrity flags for recruiter review
            sec_flags = (
                session.query(InterviewSecurityEvent)
                .filter(
                    InterviewSecurityEvent.session_id == interview_session.id,
                    InterviewSecurityEvent.event_type.in_(["tab_switch_flagged", "multiple_people_detected", "mobile_phone_detected"])
                )
                .all()
            )
            if sec_flags:
                st.markdown(
                    f"""
                    <div style="background: rgba(245, 158, 11, 0.15); border: 1.5px solid #F59E0B; border-radius: 8px; padding: 0.7rem 1rem; margin-bottom: 1rem; text-align: center;">
                      <span style="font-size: 1.15rem;">⚠️</span>
                      <strong style="color: #FBBF24; font-size: 0.92rem; margin-left: 6px;">Integrity Notice:</strong>
                      <span style="color: #CBD5E1; font-size: 0.85rem;"> {len(sec_flags)} proctoring event(s) have been flagged and recorded for recruiter audit review.</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            report_data = InterviewReportService.generate_interview_performance_report(session, interview_session.id)

            st.markdown(
                f"""
                <div class="hs-card" style="text-align: center; padding: 1.5rem 1rem; margin-bottom: 1rem;">
                  <div style="font-size: 2.2rem; margin-bottom: 4px;">🎉</div>
                  <h2 style="color: #F8FAFC !important; margin: 0 0 4px 0; font-size: 1.4rem; font-weight: 700;">Interview Completed!</h2>
                  <p style="color: #94A3B8 !important; font-size: 0.88rem; max-width: 600px; margin: 0 auto 1rem auto;">
                    Responses submitted for <strong style="color: #F8FAFC;">{candidate.name if candidate else 'Candidate'}</strong> &bull; {job.title if job else 'Position'}
                  </p>
                  <div style="display: inline-block; background: rgba(22, 163, 74, 0.2); border: 1px solid #16A34A; border-radius: 10px; padding: 0.8rem 2rem; margin-bottom: 1rem;">
                    <div style="font-size: 2.2rem; font-weight: 800; color: #4ADE80 !important; line-height: 1;">{report_data.get('overall_score', 0):.1f} / 100</div>
                    <div style="font-size: 0.72rem; font-weight: 600; color: #86EFAC !important; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 3px;">Composite Score</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Score Breakdown Metrics Cards
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Technical", f"{report_data.get('technical_knowledge_score', 0):.1f}%")
            with m2:
                st.metric("Project Depth", f"{report_data.get('project_knowledge_score', 0):.1f}%")
            with m3:
                st.metric("Communication", f"{report_data.get('communication_clarity_score', 0):.1f}%")
            with m4:
                st.metric("Relevance", f"{report_data.get('answer_relevance_score', 0):.1f}%")

            report_html = InterviewReportService.generate_report_html(
                report_data, candidate_name=candidate.name if candidate else "Candidate", job_title=job.title if job else "Role"
            )
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.download_button(
                    "📥 Download Complete Performance Report (HTML)",
                    data=report_html,
                    file_name=f"Hirexp_Interview_Report_{candidate.name if candidate else 'Candidate'}.html",
                    mime="text/html",
                    use_container_width=True,
                )
            with col_d2:
                if interview_session.invitation:
                    interview_session.invitation.invitation_status = InterviewStatus.COMPLETED.value
                    interview_session.invitation.completed_at = datetime.utcnow()
                    session.commit()

                if st.button("🚪 Finish & Sign Out (Exit Session)", type="primary", use_container_width=True):
                    st.session_state.active_session_id = None
                    st.session_state.invitation_token = None
                    st.session_state.last_feedback = None
                    st.query_params.clear()
                    SessionManager.logout_student()
                    SessionManager.logout()
                    st.session_state["interview_finished_exit"] = True
                    st.rerun()

            st.stop()

        # ── 7. ACTIVE INTERVIEW COCKPIT (COMPACT SINGLE-WINDOW 3-COLUMN LAYOUT) ──
        # Sleek Single-Line Top Header Bar (Zero scroll footprint)
        col_hdr_info, col_b1, col_b2, col_b3, col_b4 = st.columns([5.5, 1.1, 1.1, 1.1, 1.2])
        with col_hdr_info:
            st.markdown(
                f"""
                <div style="background: #11172A; border: 1px solid #1E293B; border-radius: 8px; padding: 6px 14px; display: flex; align-items: center; gap: 8px;">
                  <span style="font-size: 1.1rem;">⚡</span>
                  <div>
                    <strong style="color: #F8FAFC; font-size: 0.92rem;">Hirexp AI Virtual Interview</strong>
                    <span style="color: #94A3B8; font-size: 0.8rem; margin-left: 6px;">&bull; {candidate.name if candidate else 'Candidate'} &bull; {job.title if job else 'Position'}</span>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_b1:
            st.markdown(render_badge(f"{st.session_state.interview_difficulty}", "neutral"), unsafe_allow_html=True)
        with col_b2:
            st.markdown(render_badge(f"{interview_session.stage}", "primary"), unsafe_allow_html=True)
        with col_b3:
            st.markdown(render_badge(f"Q {min(q_idx, total_q)}/{total_q}", "success"), unsafe_allow_html=True)
        with col_b4:
            cur_cam = st.session_state.camera_position
            cam_label = "📹 Cam: Right" if cur_cam == "right" else "📹 Cam: Left"
            if st.button(cam_label, help="Toggle camera feed between Extreme Right and Extreme Left side", key="toggle_cam_side"):
                st.session_state.camera_position = "left" if cur_cam == "right" else "right"
                st.rerun()

        # ── THREE-COLUMN INTERVIEW COCKPIT ──
        # Fits completely on one window without scrolling
        cam_on_left = st.session_state.camera_position == "left"

        if cam_on_left:
            col_camera, col_chat, col_avatar = st.columns([2.6, 4.8, 2.6])
        else:
            col_avatar, col_chat, col_camera = st.columns([2.6, 4.8, 2.6])

        # ── AVATAR INTERVIEWER COLUMN ──
        with col_avatar:
            st.markdown(
                """
                <div style="background: #151C33; border: 1px solid #232D4B; border-radius: 8px; padding: 6px 10px; margin-bottom: 6px; text-align: center;">
                  <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #818CF8;">
                    🤖 AI Interviewer &bull; Sophia
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            render_avatar_component(
                state=st.session_state.avatar_state,
                message=current_q.question_text,
                avatar_model=st.session_state.avatar_persona,
                height=255,
            )
            SpeechService.render_speech_controls(text_to_speak=current_q.question_text)
            
            pct_complete = (interview_session.current_question_index / max(1, interview_session.total_questions))
            st.progress(pct_complete)
            st.caption(f"Progress: {int(pct_complete * 100)}% ({interview_session.current_question_index}/{interview_session.total_questions} answered)")

        # ── QUESTION & CANDIDATE ANSWER COLUMN (CENTER) ──
        with col_chat:
            st.markdown(
                f"""
                <div style="background: #151C33; border: 1px solid #232D4B; border-left: 4px solid #6366F1; border-radius: 8px; padding: 8px 12px; margin-bottom: 6px;">
                  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px;">
                    <span style="color: #818CF8; font-weight: 700; font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.04em;">
                      Question {current_q.question_order} &bull; {current_q.category}
                    </span>
                    <span style="background: #19223C; color: #94A3B8 !important; border: 1px solid #334155; padding: 1px 6px; border-radius: 9999px; font-size: 0.68rem; font-weight: 600;">
                      {current_q.question_type}
                    </span>
                  </div>
                  <div style="color: #F8FAFC !important; font-size: 0.98rem; font-weight: 600; line-height: 1.35;">
                    {current_q.question_text}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Audio Transcriber (Compact)
            SpeechService.render_audio_recorder_and_transcriber()

            # Answer Input Form
            with st.form(f"answer_form_{current_q.id}"):
                cand_answer = st.text_area(
                    "Your Answer:",
                    placeholder="Type or speak via microphone above. Detail your technical solution, trade-offs, and experiences...",
                    height=100,
                    label_visibility="collapsed",
                )

                c_sub, c_end = st.columns([3, 1])
                with c_sub:
                    submit_btn = st.form_submit_button("Submit Answer & Next ➔", type="primary", use_container_width=True)
                with c_end:
                    end_now_btn = st.form_submit_button("End Early", use_container_width=True)

                if end_now_btn:
                    engine._finalize_session(session, interview_session)
                    interview_session.status = InterviewStatus.COMPLETED.value
                    if interview_session.invitation:
                        interview_session.invitation.invitation_status = InterviewStatus.COMPLETED.value
                        interview_session.invitation.completed_at = datetime.utcnow()
                    session.commit()
                    st.rerun()

                if submit_btn:
                    if not cand_answer.strip():
                        st.warning("Please enter or transcribe an answer before submitting.")
                    else:
                        st.session_state.avatar_state = "thinking"
                        with st.spinner("AI Evaluator scoring response..."):
                            eval_res = engine.submit_answer(
                                session=session,
                                session_id=interview_session.id,
                                question_id=current_q.id,
                                candidate_answer=cand_answer,
                                difficulty=st.session_state.interview_difficulty,
                            )
                            st.session_state.last_feedback = eval_res.get("evaluation")
                            st.session_state.avatar_state = "speaking"
                            st.rerun()

            # Real-time Feedback on previous response
            if st.session_state.last_feedback:
                fb = st.session_state.last_feedback
                st.markdown(
                    f"""
                    <div style="background: rgba(22, 163, 74, 0.12); border: 1px solid #16A34A; border-radius: 6px; padding: 6px 10px; margin-top: 5px; font-size: 0.78rem; max-height: 70px; overflow-y: auto;">
                      <span style="color: #4ADE80; font-weight: 700;">Previous Answer Score: {fb.get('score', 0):.0f}/100 &bull; </span>
                      <span style="color: #CBD5E1;">{fb.get('feedback', '')}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # ── CAMERA CAPTURE COLUMN (EXTREME RIGHT OR LEFT) ──
        with col_camera:
            st.markdown(
                """
                <div style="background: #151C33; border: 1px solid #232D4B; border-radius: 8px; padding: 6px 10px; margin-bottom: 6px; text-align: center;">
                  <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #4ADE80;">
                    📹 Camera & AI Proctoring
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            render_interview_security_shield(session_id=interview_session.id)
