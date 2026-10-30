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
from src.database.repository import get_db_session
from src.interview.interview_engine import InterviewEngine
from src.recruitment.invitation_service import InvitationService
from src.reports.interview_report_service import InterviewReportService
from src.resume.pdf_parser import PDFParser
from src.resume.resume_extractor import ResumeExtractor
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

# ── 1. ISOLATE STUDENT INTERVIEW (HIDE ALL RECRUITER SIDEBAR & PAGES) ──
st.markdown(
    """
    <style>
      [data-testid="stSidebar"], [data-testid="collapsedControl"] {
        display: none !important;
      }
      #MainMenu { visibility: hidden; }
      header { visibility: hidden; }
      footer { visibility: hidden; }
      .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 1200px !important;
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

# ── 2. EXIT SCREEN (AFTER COMPLETING INTERVIEW, STUDENT IS OUTSIDE THE SITE) ──
if st.session_state.get("interview_finished_exit"):
    render_camera_shutdown()
    st.markdown(
        """
        <div class="hs-card" style="text-align: center; padding: 3.5rem 2rem; margin: 3rem auto; max-width: 650px; border-top: 4px solid #22C55E;">
          <div style="font-size: 3.8rem; margin-bottom: 10px;">✅</div>
          <h2 style="color: #4ADE80 !important; margin: 0 0 10px 0; font-size: 1.7rem; font-weight: 800;">Interview Successfully Completed!</h2>
          <p style="color: #CBD5E1 !important; font-size: 1rem; line-height: 1.6; margin: 0 auto 1.8rem auto;">
            Your interview responses and AI evaluation report have been securely recorded and submitted to the recruitment team.
            You have been safely signed out of the platform.
          </p>
          <div style="background: #19223C; border: 1px solid #232D4B; border-radius: 8px; padding: 12px; font-size: 0.88rem; color: #CBD5E1 !important;">
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
        <div class="hs-card" style="padding: 2.5rem; text-align: center; margin: 3rem auto; max-width: 600px; border-left: 4px solid #EF4444;">
          <div style="font-size: 2.8rem; margin-bottom: 10px;">🔒</div>
          <h2 style="color: #F87171 !important; margin: 0 0 8px 0; font-size: 1.4rem;">Student Interview Portal — Restricted</h2>
          <p style="color: #CBD5E1 !important; font-size: 0.95rem; line-height: 1.6; margin: 0 auto 1.5rem auto;">
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

# Header Banner for Student
st.markdown(
    """
    <div style="background: linear-gradient(135deg, #1E1B4B 0%, #312E81 60%, #4F46E5 100%); border-radius: 14px; padding: 1.4rem 1.8rem; margin-bottom: 1.4rem; color: #FFFFFF; box-shadow: 0 4px 16px rgba(79, 70, 229, 0.15);">
      <div style="font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em; color: #C7D2FE; font-weight: 700; margin-bottom: 4px;">
        Hirexp AI &bull; Proctored Candidate Assessment Room
      </div>
      <h1 style="margin: 0; font-size: 1.65rem; font-weight: 800; letter-spacing: -0.02em;">
        Virtual AI Interview Room
      </h1>
      <p style="margin: 6px 0 0 0; color: #E0E7FF; font-size: 0.88rem;">
        Evidence-based, resume-grounded technical & behavioral interview with live AI interviewer.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── 4. CANDIDATE SETUP & CONSENT (BEFORE SESSION STARTS) ──
if not st.session_state.active_session_id:
    col_verif, col_guide = st.columns([3, 2])

    with col_verif:
        st.markdown(
            """
            <div class="hs-card" style="margin-bottom: 1.25rem;">
              <h3 style="margin: 0 0 4px 0; font-size: 1.1rem; font-weight: 700; color: #F8FAFC !important;">Candidate Verification & Consent</h3>
              <p style="margin: 0 0 0 0; font-size: 0.82rem; color: #94A3B8 !important;">Verify your interview access token and consent to AI-assisted proctoring</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        token_input = st.text_input(
            "Your Personal Interview Access Token",
            value=st.session_state.invitation_token,
            placeholder="hs-inv-...",
            help="Found in your interview invitation email.",
        )

        # Candidate Experience Options
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

        # Privacy Notice Accordion
        privacy_info = PrivacyManager.get_privacy_notice()
        with st.expander("📋 Review Candidate Privacy Policy & Data Processing Notice", expanded=False):
            st.write(f"**Purposes:** {', '.join(privacy_info['purposes'])}")
            st.write(f"**Non-Discrimination Policy:** {privacy_info['protected_characteristics_policy']}")
            st.write(f"**Data Retention Window:** {privacy_info['retention_policy']}")

        consent_given = st.checkbox(
            "I acknowledge the privacy notice and agree to audio/video integrity monitoring (Single-person verification & tab focus guard).",
            value=True,
        )

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
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
            <div class="hs-card" style="margin-bottom: 1.25rem; text-align: center;">
              <h3 style="margin: 0 0 4px 0; font-size: 1.05rem; font-weight: 700; color: #F8FAFC !important;">AI Interviewer</h3>
              <p style="margin: 0 0 8px 0; font-size: 0.82rem; color: #94A3B8 !important;">Ready to conduct your evidence-based virtual interview</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_avatar_component(state="idle", message="Hello! Welcome to your virtual interview room. I will guide you through your assessment.", height=320)
        SpeechService.render_audio_recorder_and_transcriber()
        st.markdown(
            """
            <div style="font-size: 0.82rem; color: #94A3B8 !important; margin-top: 14px; line-height: 1.5;">
              <strong style="color: #F8FAFC !important;">Exam Integrity Rules:</strong>
              <ul style="margin: 6px 0; padding-left: 18px;">
                <li><strong>Single Candidate Only:</strong> Only one person may be in camera frame. Multiple faces will trigger an integrity warning.</li>
                <li><strong>Protected Tab:</strong> Switching browser tabs or minimizing the window will automatically terminate the session.</li>
                <li><strong>Microphone:</strong> Speak clearly or type your response in the provided input box.</li>
                <li><strong>Single Submission:</strong> Answers cannot be edited after final submission.</li>
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

        # ── AUTOMATIC TERMINATION CHECK (TAB SWITCH / NAVIGATION DETECTED) ──
        is_auto_term = st.query_params.get("auto_terminated") == "1"
        if is_auto_term and interview_session.status != InterviewStatus.COMPLETED.value:
            engine._finalize_session(session, interview_session)
            interview_session.status = InterviewStatus.COMPLETED.value
            if interview_session.invitation:
                interview_session.invitation.invitation_status = InterviewStatus.COMPLETED.value
                interview_session.invitation.completed_at = datetime.utcnow()
            sec_event = InterviewSecurityEvent(
                session_id=interview_session.id,
                event_type="tab_switch_auto_terminate",
                event_details={
                    "reason": st.query_params.get("term_reason", "Tab switch away from interview room detected"),
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            session.add(sec_event)
            session.commit()

        is_completed = interview_session.status == InterviewStatus.COMPLETED.value or not current_q or is_auto_term

        # Candidate & Stage Info Bar
        q_idx = interview_session.current_question_index + 1
        total_q = interview_session.total_questions or 5

        st.markdown(
            f"""
            <div class="hs-card" style="margin-bottom: 1.25rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
              <div>
                <strong style="color: #F8FAFC !important; font-size: 1.05rem;">{candidate.name if candidate else 'Candidate'}</strong> 
                <span style="color: #94A3B8 !important; font-size: 0.88rem;">&bull; Interviewing for <strong style="color: #F8FAFC !important;">{job.title if job else 'Position'}</strong> at <strong style="color: #F8FAFC !important;">{company_name}</strong></span>
              </div>
              <div style="display: flex; gap: 8px; align-items: center;">
                {render_badge(f"Track: {st.session_state.interview_difficulty}", "neutral")}
                {render_badge(f"Stage: {interview_session.stage}", "primary")}
                {render_badge(f"Question {min(q_idx, total_q)} of {total_q}", "success")}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── CAMERA MANAGEMENT: END CAMERA AFTER INTERVIEW COMPLETES ──
        if is_completed:
            render_camera_shutdown()
        else:
            render_interview_security_shield(session_id=interview_session.id)

        # ── 6. INTERVIEW COMPLETED: FINAL PERFORMANCE REPORT ──
        if is_completed:
            if is_auto_term or st.query_params.get("term_reason"):
                term_msg = st.query_params.get("term_reason", "Tab switch or leaving the interview room was detected.")
                st.markdown(
                    f"""
                    <div style="background: rgba(127, 29, 29, 0.25); border: 2px solid #EF4444; border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 1.5rem; text-align: center;">
                      <div style="font-size: 2.2rem; margin-bottom: 6px;">🚨</div>
                      <h3 style="color: #F87171 !important; margin: 0 0 6px 0; font-size: 1.25rem; font-weight: 800;">Interview Terminated Automatically</h3>
                      <p style="color: #FCA5A5; font-size: 0.95rem; margin: 0 auto; max-width: 650px;">
                        <strong>Integrity Violation:</strong> {term_msg}<br>
                        In accordance with exam proctoring rules, the interview was immediately ended and your answers finalized. The camera has been shut down.
                      </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            report_data = InterviewReportService.generate_interview_performance_report(session, interview_session.id)

            st.markdown(
                f"""
                <div class="hs-card" style="text-align: center; padding: 2.5rem 2rem; margin-bottom: 1.5rem;">
                  <div style="font-size: 3rem; margin-bottom: 6px;">🎉</div>
                  <h2 style="color: #F8FAFC !important; margin: 0 0 6px 0; font-size: 1.6rem; font-weight: 700;">Interview Completed Successfully!</h2>
                  <p style="color: #94A3B8 !important; font-size: 0.95rem; max-width: 600px; margin: 0 auto 1.5rem auto;">
                    Thank you, <strong style="color: #F8FAFC;">{candidate.name if candidate else 'Candidate'}</strong>. Your responses were evaluated in real-time across technical mastery, practical depth, communication clarity, and problem solving.
                  </p>
                  <div style="display: inline-block; background: rgba(22, 163, 74, 0.2); border: 1px solid #16A34A; border-radius: 12px; padding: 1.2rem 2.5rem; margin-bottom: 1.5rem;">
                    <div style="font-size: 2.5rem; font-weight: 800; color: #4ADE80 !important; line-height: 1;">{report_data.get('overall_score', 0):.1f} / 100</div>
                    <div style="font-size: 0.78rem; font-weight: 600; color: #86EFAC !important; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px;">Overall Composite Evaluation</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Score Breakdown Metrics Cards
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Technical Knowledge", f"{report_data.get('technical_knowledge_score', 0):.1f}%")
            with m2:
                st.metric("Project Knowledge", f"{report_data.get('project_knowledge_score', 0):.1f}%")
            with m3:
                st.metric("Communication Clarity", f"{report_data.get('communication_clarity_score', 0):.1f}%")
            with m4:
                st.metric("Answer Relevance", f"{report_data.get('answer_relevance_score', 0):.1f}%")

            # Strengths, Weaknesses, and Improvements
            c_str, c_weak = st.columns(2)
            with c_str:
                st.markdown("#### 💪 Key Strengths")
                for s in report_data.get("strengths", []):
                    st.markdown(f"- **{s}**")
            with c_weak:
                st.markdown("#### 🎯 Identified Weaknesses & Areas for Growth")
                for w in report_data.get("weaknesses", []):
                    st.markdown(f"- {w}")

            st.markdown("#### 🚀 Recommended Practice Topics")
            st.write(", ".join(report_data.get("recommended_practice_topics", [])))

            # Question-by-Question Feedback Accordion
            with st.expander("📝 Detailed Question-by-Question Breakdown & Rubrics", expanded=True):
                for qf in report_data.get("question_feedbacks", []):
                    st.markdown(
                        f"""
                        <div style="background: #19223C; border: 1px solid #232D4B; border-radius: 8px; padding: 12px; margin-bottom: 12px;">
                          <div style="font-weight: 700; color: #A5B4FC;">Question {qf['order']}: {qf['category']}</div>
                          <div style="color: #F8FAFC !important; margin: 4px 0 8px 0; font-size: 0.95rem;">"{qf['question']}"</div>
                          <div style="font-size: 0.88rem; color: #CBD5E1 !important; margin-bottom: 6px;"><strong style="color: #F8FAFC;">Candidate Answer:</strong> {html.escape(qf['answer'])}</div>
                          <div style="display: flex; gap: 14px; font-size: 0.82rem; color: #94A3B8 !important;">
                            <span style="font-weight: 700; color: #818CF8;">Score: {qf['score']:.1f}/100</span>
                            <span><strong style="color: #CBD5E1;">Feedback:</strong> {html.escape(qf['feedback'])}</span>
                          </div>
                          {f'<div style="font-size: 0.8rem; color: #C084FC; margin-top: 4px;"><strong>AI Follow-Up:</strong> {html.escape(qf["follow_up"])}</div>' if qf.get('follow_up') else ''}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            # Downloadable Report Action
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
                # Update invitation status to COMPLETED
                if interview_session.invitation:
                    interview_session.invitation.invitation_status = InterviewStatus.COMPLETED.value
                    interview_session.invitation.completed_at = datetime.utcnow()
                    session.commit()

                # OUTSIDE THE SITE LOGOUT AND TERMINATION
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

        # ── 7. LIVE INTERVIEW STEP ──
        col_avatar, col_chat = st.columns([4, 6])

        with col_avatar:
            st.markdown(
                """
                <div class="hs-card" style="margin-bottom: 1rem; text-align: center; padding: 1rem;">
                  <div style="font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #94A3B8 !important;">
                    AI Virtual Interviewer
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            render_avatar_component(
                state=st.session_state.avatar_state,
                message=current_q.question_text,
                avatar_model=st.session_state.avatar_persona,
                height=390,
            )
            SpeechService.render_speech_controls(text_to_speak=current_q.question_text)
            
            pct_complete = (interview_session.current_question_index / max(1, interview_session.total_questions))
            st.progress(pct_complete)
            st.caption(f"Session Progress: {int(pct_complete * 100)}% complete ({interview_session.current_question_index}/{interview_session.total_questions} questions)")

        with col_chat:
            st.markdown(
                f"""
                <div style="background: #151C33; border: 1px solid #232D4B; border-left: 4px solid #6366F1; border-radius: 12px; padding: 1.35rem 1.5rem; margin-bottom: 1.25rem; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);">
                  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="color: #818CF8; font-weight: 700; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.04em;">
                      Question {current_q.question_order} &bull; {current_q.category}
                    </span>
                    <span style="background: #19223C; color: #94A3B8 !important; border: 1px solid #334155; padding: 2px 8px; border-radius: 9999px; font-size: 0.75rem; font-weight: 600;">
                      {current_q.question_type}
                    </span>
                  </div>
                  <div style="color: #F8FAFC !important; font-size: 1.15rem; font-weight: 600; line-height: 1.45;">
                    {current_q.question_text}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Microphone Recording & Speech-to-Text Component
            SpeechService.render_audio_recorder_and_transcriber()

            # Rubric Transparency Box
            with st.expander("🔍 Rubric Criteria & Expected Concepts", expanded=False):
                st.write(f"**Target Concepts:** {', '.join(current_q.expected_concepts or [])}")
                st.write(f"**Rubric Points:** {current_q.rubric_criteria}")

            # Candidate Answer Input Form
            with st.form(f"answer_form_{current_q.id}"):
                cand_answer = st.text_area(
                    "Your Answer (Type or speak via microphone):",
                    placeholder="Provide your detailed answer here. Focus on real-world engineering experiences, architecture trade-offs, and practical lessons...",
                    height=160,
                )

                c_sub, c_end = st.columns([2, 1])
                with c_sub:
                    submit_btn = st.form_submit_button("Submit Answer & Next Question ➔", type="primary", use_container_width=True)
                with c_end:
                    end_now_btn = st.form_submit_button("End Interview Early", use_container_width=True)

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
                        with st.spinner("AI Evaluator scoring response and formulating follow-up..."):
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

            # Display Constructive Real-time Feedback & Contextual Follow-up
            if st.session_state.last_feedback:
                fb = st.session_state.last_feedback
                st.markdown(
                    f"""
                    <div style="background: rgba(22, 163, 74, 0.15); border: 1px solid #16A34A; border-radius: 10px; padding: 14px 16px; margin-top: 14px;">
                      <div style="color: #4ADE80 !important; font-weight: 700; font-size: 0.9rem;">
                        Feedback on Previous Answer (Score: {fb.get('score', 0):.1f}/100)
                      </div>
                      <div style="color: #F8FAFC !important; font-size: 0.88rem; margin: 6px 0; line-height: 1.45;">{fb.get('feedback', '')}</div>
                      {f'<div style="color: #818CF8; font-size: 0.84rem; margin-top: 6px;"><strong>Contextual Follow-up Generated:</strong> "{fb.get("follow_up_question")}"</div>' if fb.get("follow_up_question") else ''}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
