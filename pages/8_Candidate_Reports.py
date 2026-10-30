import html
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from src.database.models import (
    CandidateProfile,
    InterviewInvitation,
    InterviewQuestion,
    InterviewSecurityEvent,
    InterviewSession,
    RecruiterDecision,
    RecruitmentDecisionRecord,
    ResumeDocument,
)
from src.database.repository import get_db_session
from src.recruitment.email_service import EmailService
from src.recruitment.shortlist_service import ShortlistService
from src.reports.interview_report_service import InterviewReportService
from src.reports.report_generator import ReportGenerator
from src.security.session_manager import SessionManager
from src.ui.layout import render_badge, render_empty_state, render_header, render_kpi_card, setup_sidebar_context

context = setup_sidebar_context()
render_header(
    title="Candidate Reports & Interview Results Dashboard",
    subtitle="Evaluate multi-category performance rubrics, integrity event logs, and execute next-round selection workflows",
    breadcrumbs=["Hirexp Ai", "Evaluation", "Candidate Dossier & Results"],
)

job_id = context.get("job_id")
job = context.get("job")

if not job_id:
    st.warning("Please select an active Job in the sidebar.")
    st.stop()

with get_db_session() as session:
    candidates = (
        session.query(CandidateProfile)
        .join(ResumeDocument, CandidateProfile.id == ResumeDocument.candidate_id)
        .filter(ResumeDocument.job_id == job_id)
        .all()
    )

    if not candidates:
        render_empty_state("No Candidate Dossiers Found", "No candidates processed for this job requisition yet. Ingest resumes or issue invitations first.", icon="📄")
        st.stop()

    # ── SECTION 11 RESULTS TABLE & FILTERS ───────────────────────────────
    st.markdown(
        """
        <div class="hs-card" style="padding: 1.25rem 1.5rem; margin-bottom: 1.25rem;">
          <h3 style="margin: 0; font-size: 1.05rem; font-weight: 700; color: #F8FAFC !important;">Recruiter Interview Results Table</h3>
          <p style="margin: 2px 0 0 0; font-size: 0.8rem; color: #94A3B8 !important;">Live pipeline assessment metrics, interview scores, and hiring recommendations</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    rf_col1, rf_col2, rf_col3, rf_col4 = st.columns([2, 1.5, 1.5, 1.5])
    with rf_col1:
        tbl_search = st.text_input("🔍 Search Candidate by Name or Email", "", key="tbl_search")
    with rf_col2:
        tbl_int_status = st.selectbox(
            "Filter Interview Status",
            options=["All", "Completed", "In Progress", "Not Started"],
            key="tbl_int_status",
        )
    with rf_col3:
        tbl_ai_rec = st.selectbox(
            "AI Recommendation",
            options=["All", "Strongly Recommended", "Recommended", "Requires Recruiter Review", "Not Recommended"],
            key="tbl_ai_rec",
        )
    with rf_col4:
        tbl_decision = st.selectbox(
            "Recruiter Decision",
            options=["All", "Pending", "Shortlisted", "Selected for Next Round", "Hold for Review", "Rejected"],
            key="tbl_decision",
        )

    # Build Master Results Table
    results_rows = []
    cand_lookup = {}
    for c in candidates:
        doc = session.query(ResumeDocument).filter(ResumeDocument.candidate_id == c.id, ResumeDocument.job_id == job_id).first()
        scr = doc.screening_result if doc else None
        scr_score = f"{scr.overall_score:.1f}/100" if scr else "N/A"
        dec = scr.recruiter_decision if scr else "Pending"

        # Check interview session
        s_sess = (
            session.query(InterviewSession)
            .filter(InterviewSession.candidate_id == c.id, InterviewSession.job_id == job_id)
            .order_by(InterviewSession.started_at.desc())
            .first()
        )
        int_stat = s_sess.status if s_sess else "Not Started"
        int_score = f"{s_sess.overall_interview_score:.1f}/100" if (s_sess and s_sess.overall_interview_score) else "Pending"

        rep_data = InterviewReportService.generate_interview_performance_report(session, s_sess.id) if s_sess else {}
        ai_rec = rep_data.get("ai_recommendation", "Requires Recruiter Review" if s_sess else "Awaiting Interview")
        tech_score = f"{rep_data.get('technical_knowledge_score', 0):.1f}%" if s_sess else "N/A"

        # Filter check
        if tbl_search:
            sq = tbl_search.lower()
            if sq not in (c.name or "").lower() and sq not in (c.email or "").lower():
                continue
        if tbl_int_status != "All" and int_stat != tbl_int_status:
            continue
        if tbl_ai_rec != "All" and ai_rec != tbl_ai_rec:
            continue
        if tbl_decision != "All" and dec != tbl_decision:
            continue

        cand_lookup[c.id] = c
        results_rows.append({
            "Candidate ID": c.id,
            "Candidate Name": c.name,
            "Email": c.email or "N/A",
            "Job Role": job.title,
            "Resume Screening Score": scr_score,
            "Interview Score": int_score,
            "Technical Score": tech_score,
            "Interview Status": int_stat,
            "AI Recommendation": ai_rec,
            "Recruiter Decision": dec,
        })

    if results_rows:
        df_res = pd.DataFrame(results_rows)
        st.dataframe(df_res.drop(columns=["Candidate ID"]), use_container_width=True, hide_index=True)
    else:
        render_empty_state("No Matching Interview Results", "Try broadening the search query or filters above.", icon="🔍")

    # ── CANDIDATE DOSSIER INSPECTOR ──────────────────────────────────────
    cand_options = {f"{c.name} ({c.email or 'N/A'})": c.id for c in candidates}
    selected_name = st.selectbox("Select Candidate for Deep-Dive Evaluation & Next-Round Workflow", options=list(cand_options.keys()))
    cand_id = cand_options[selected_name]

    candidate = session.query(CandidateProfile).filter(CandidateProfile.id == cand_id).first()
    resume_doc = session.query(ResumeDocument).filter(ResumeDocument.candidate_id == cand_id, ResumeDocument.job_id == job_id).first()
    screening = resume_doc.screening_result if resume_doc else None

    # Retrieve Technical/Comprehensive Session
    tech_session = (
        session.query(InterviewSession)
        .filter(
            InterviewSession.candidate_id == cand_id,
            InterviewSession.job_id == job_id,
        )
        .order_by(InterviewSession.started_at.desc())
        .first()
    )

    report_data = InterviewReportService.generate_interview_performance_report(session, tech_session.id) if tech_session else {}

    # Candidate Profile Header Card
    initials = "".join([part[0] for part in candidate.name.split()[:2]]).upper() if candidate.name else "C"
    decision = screening.recruiter_decision if screening else "Pending"
    score_val = screening.overall_score if screening else 0.0
    rec_val = screening.recommendation if screening else "Pending Review"

    st.markdown(
        f"""
        <div class="hs-card" style="padding: 1.5rem; margin-bottom: 1.5rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
            <div style="display: flex; align-items: center; gap: 14px;">
              <div style="width: 52px; height: 52px; border-radius: 12px; background: linear-gradient(135deg, #4F46E5, #06B6D4); display: flex; align-items: center; justify-content: center; color: white; font-size: 1.3rem; font-weight: 700; box-shadow: 0 2px 8px rgba(79, 70, 229, 0.35);">
                {initials}
              </div>
              <div>
                <h2 style="margin: 0; font-size: 1.4rem; font-weight: 800; color: #F8FAFC !important;">{candidate.name}</h2>
                <div style="font-size: 0.85rem; color: #94A3B8 !important; margin-top: 3px;">
                  <span style="color: #CBD5E1 !important;">📧 {candidate.email or 'N/A'}</span> &nbsp;&bull;&nbsp; 
                  <span style="color: #CBD5E1 !important;">📱 {candidate.phone or 'N/A'}</span> &nbsp;&bull;&nbsp; 
                  <span>💼 Applied: <strong style="color: #F8FAFC !important;">{job.title}</strong></span>
                </div>
              </div>
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
              {render_badge(f"Decision: {decision}", "primary" if "Selected" in decision or "Shortlisted" in decision else "neutral")}
              {render_badge(rec_val, "success" if "Meets" in rec_val else "warning")}
            </div>
          </div>
        </div>
            <div style="display: flex; gap: 8px; align-items: center;">
              {render_badge(f"Decision: {decision}", "primary" if "Selected" in decision or "Shortlisted" in decision else "neutral")}
              {render_badge(rec_val, "success" if "Meets" in rec_val else "warning")}
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── SECTION 10 PERFORMANCE EVALUATION TABLE (0-100) ──────────────────
    st.markdown(
        """
        <div class="hs-card" style="padding: 1.25rem 1.5rem; margin-bottom: 1.25rem;">
          <h3 style="margin: 0 0 4px 0; font-size: 1.05rem; font-weight: 700; color: #F8FAFC !important;">AI Performance Evaluation Matrix</h3>
          <p style="margin: 0; font-size: 0.8rem; color: #94A3B8 !important;">Multi-category rubrics evaluated on verified candidate responses</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if tech_session and tech_session.status == "Completed":
        t_tech = report_data.get("technical_knowledge_score", 0)
        t_prob = report_data.get("problem_solving_score", 0)
        t_comm = report_data.get("communication_clarity_score", 0)
        t_proj = report_data.get("project_understanding_score", 0)
        t_behav = report_data.get("behavioral_responses_score", 0)
        t_overall = report_data.get("overall_score", 0)

        eval_df = pd.DataFrame([
            {"Evaluation Category": "Technical Knowledge", "Score (0-100)": f"{t_tech:.1f}", "Performance Tier": "Exceptional" if t_tech >= 80 else ("Proficient" if t_tech >= 65 else "Developing")},
            {"Evaluation Category": "Problem Solving", "Score (0-100)": f"{t_prob:.1f}", "Performance Tier": "Exceptional" if t_prob >= 80 else ("Proficient" if t_prob >= 65 else "Developing")},
            {"Evaluation Category": "Communication Clarity", "Score (0-100)": f"{t_comm:.1f}", "Performance Tier": "Exceptional" if t_comm >= 80 else ("Proficient" if t_comm >= 65 else "Developing")},
            {"Evaluation Category": "Project Understanding", "Score (0-100)": f"{t_proj:.1f}", "Performance Tier": "Exceptional" if t_proj >= 80 else ("Proficient" if t_proj >= 65 else "Developing")},
            {"Evaluation Category": "Behavioral Responses", "Score (0-100)": f"{t_behav:.1f}", "Performance Tier": "Exceptional" if t_behav >= 80 else ("Proficient" if t_behav >= 65 else "Developing")},
            {"Evaluation Category": "Overall Composite Interview Score", "Score (0-100)": f"{t_overall:.1f}", "Performance Tier": "Qualified" if t_overall >= 70 else "Review Needed"},
        ])
        st.dataframe(eval_df, use_container_width=True, hide_index=True)

        # AI Recommendation Banner
        ai_rec = report_data.get("ai_recommendation", "Recommended")
        rec_color = "#16A34A" if "Strongly" in ai_rec or ai_rec == "Recommended" else ("#D97706" if "Review" in ai_rec else "#DC2626")
        st.markdown(
            f"""
            <div style="background: rgba(22, 30, 54, 0.95); border: 1px solid rgba(139, 92, 246, 0.3); border-left: 4px solid {rec_color}; border-radius: 10px; padding: 14px 18px; margin-top: 14px;">
              <span style="font-size: 0.78rem; font-weight: 700; text-transform: uppercase; color: #94A3B8 !important; display: block; margin-bottom: 4px;">AI Recommendation:</span>
              <div style="font-size: 1.2rem; font-weight: 800; color: {rec_color} !important; margin-bottom: 4px;">{ai_rec}</div>
              <div style="font-size: 0.88rem; color: #E2E8F0 !important; line-height: 1.5;">{report_data.get('recommendation_reason', '')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        render_empty_state("Interview In Progress or Not Started", "Performance rubrics will be generated automatically once the candidate submits their interview.", icon="⏳")

    # ── INTEGRITY EVENT AUDIT LOGS ───────────────────────────────────────
    st.markdown(
        """
        <div class="hs-card" style="padding: 1.25rem 1.5rem; margin-bottom: 1.25rem;">
          <h3 style="margin: 0 0 4px 0; font-size: 1.05rem; font-weight: 700; color: #F8FAFC !important;">Interview Integrity & Anti-Cheating Event Log</h3>
          <p style="margin: 0; font-size: 0.8rem; color: #94A3B8 !important;">Recorded deterrent signals during the active interview session</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if tech_session:
        sec_events = (
            session.query(InterviewSecurityEvent)
            .filter(InterviewSecurityEvent.session_id == tech_session.id)
            .order_by(InterviewSecurityEvent.timestamp.desc())
            .all()
        )
        if sec_events:
            event_rows = []
            for ev in sec_events:
                event_rows.append({
                    "Timestamp (UTC)": ev.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "Event Type": ev.event_type.replace("_", " ").title(),
                    "Event Details": str(ev.event_details) if ev.event_details else "Detected",
                })
            st.dataframe(pd.DataFrame(event_rows), use_container_width=True, hide_index=True)
        else:
            st.success("✓ No integrity deterrent violations recorded during this interview session.")
    else:
        st.caption("No session events recorded yet.")

    # ── QUESTION-WISE RESPONSES & RUBRICS ACCORDION ──────────────────────
    if tech_session:
        st.markdown(
            """
            <div class="hs-card" style="padding: 1.25rem 1.5rem; margin-bottom: 1.25rem;">
              <h3 style="margin: 0; font-size: 1.05rem; font-weight: 700; color: #F8FAFC !important;">Verbatim Interview Q&A Transcript & Rubrics</h3>
              <p style="margin: 2px 0 0 0; font-size: 0.8rem; color: #94A3B8 !important;">Granular question breakdown, candidate answers, and scoring rationales</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        session_questions = (
            session.query(InterviewQuestion)
            .filter(InterviewQuestion.session_id == tech_session.id)
            .order_by(InterviewQuestion.question_order.asc())
            .all()
        )

        for q in session_questions:
            score_q = f"{q.score:.1f}" if q.score is not None else "Pending"
            with st.expander(f"Q{q.question_order}: {q.question_text[:75]}... | Score: {score_q}/100", expanded=False):
                st.markdown(f"**Question:** {q.question_text}")
                st.markdown(
                    f"""
                    <div style="background: #19223C; border: 1px solid #2D3A60; border-radius: 8px; padding: 10px 14px; margin: 8px 0;">
                      <span style="font-size: 0.75rem; color: #94A3B8 !important; text-transform: uppercase; font-weight: 600;">Candidate Response:</span>
                      <div style="color: #F8FAFC !important; font-size: 0.9rem; margin-top: 4px;">{html.escape(q.candidate_answer or 'No answer submitted')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(f"**AI Evaluation:** {q.evaluation_feedback or 'Pending'}")
                if q.correct_concepts:
                    st.markdown(f"**Demonstrated Concepts:** {', '.join(q.correct_concepts)}")
                if q.follow_up_question:
                    st.markdown(f"**Contextual Follow-up:** {q.follow_up_question}")

    # ── SECTION 11 & 12 RECRUITER DECISION & NEXT-ROUND SELECTION ────────
    st.markdown(
        """
        <div class="hs-card" style="padding: 1.25rem 1.5rem; margin-bottom: 1.5rem;">
          <h3 style="margin: 0 0 6px 0; font-size: 1.1rem; font-weight: 700; color: #F8FAFC !important;">Recruiter Final Decision & Next-Round Workflow</h3>
          <p style="margin: 0; font-size: 0.82rem; color: #94A3B8 !important;">Execute hiring decisions with recruiter sign-off, decision auditing, and automated next-round candidate notifications.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form(f"recruiter_decision_action_form_{candidate.id}"):
        rec_dec_type = st.selectbox(
            "Recruiter Decision Action:",
            options=[
                "SELECT FOR NEXT ROUND",
                "REJECT CANDIDATE",
                "HOLD FOR REVIEW",
                "SCHEDULE ANOTHER INTERVIEW",
            ],
            index=0,
        )

        col_nr1, col_nr2 = st.columns(2)
        with col_nr1:
            nr_name = st.text_input("Next Round Name", value="Round 2: Technical Deep-Dive & Architecture Review")
            nr_date = st.date_input("Scheduled Date (Optional)")
        with col_nr2:
            nr_time = st.text_input("Scheduled Time (Optional)", placeholder="e.g. 10:30 AM UTC")
            send_notification_email = st.checkbox("Send Automated Notification Email to Candidate", value=True)

        rec_comments = st.text_area("Recruiter Evaluation Comments & Justification:", placeholder="State the rationale for this hiring decision...", height=80)
        confirm_check = st.checkbox(f"I confirm this final recruitment decision for {candidate.name}", value=False)

        submit_decision = st.form_submit_button("Submit & Finalize Recruiter Decision", type="primary", use_container_width=True)

        if submit_decision:
            if not confirm_check:
                st.warning("Please check the confirmation box before finalizing your decision.")
            else:
                user = SessionManager.get_current_user()
                recruiter_id = user.id if user else "Recruiter"

                # Map selection to enum
                status_mapping = {
                    "SELECT FOR NEXT ROUND": RecruiterDecision.SELECTED_FOR_NEXT_ROUND.value,
                    "REJECT CANDIDATE": RecruiterDecision.REJECTED.value,
                    "HOLD FOR REVIEW": RecruiterDecision.HOLD_FOR_REVIEW.value,
                    "SCHEDULE ANOTHER INTERVIEW": RecruiterDecision.INVITED.value,
                }
                mapped_status = status_mapping.get(rec_dec_type, RecruiterDecision.PENDING.value)

                # Save Decision in ScreeningResult
                if screening:
                    screening.recruiter_decision = mapped_status
                    screening.recruiter_notes = rec_comments

                # Record in RecruitmentDecisionRecord
                nr_datetime = datetime.combine(nr_date, datetime.min.time()) if nr_date else None
                dec_rec = RecruitmentDecisionRecord(
                    candidate_id=candidate.id,
                    job_id=job_id,
                    interview_session_id=tech_session.id if tech_session else None,
                    recruiter_id=recruiter_id,
                    decision=mapped_status,
                    recruiter_comments=rec_comments,
                    next_round_name=nr_name if "SELECT" in rec_dec_type else None,
                    next_round_date=nr_datetime if "SELECT" in rec_dec_type else None,
                    next_round_instructions=rec_comments,
                    decision_date=datetime.utcnow(),
                )
                session.add(dec_rec)
                session.commit()

                # Send Automated Email Notification if requested
                email_status_msg = ""
                if send_notification_email and candidate.email and "@" in candidate.email:
                    if "SELECT" in rec_dec_type:
                        date_str = nr_date.strftime("%B %d, %Y") if nr_date else None
                        company_name = job.campaign.company.name if job and job.campaign and job.campaign.company else "Hirexp AI"
                        ok_email, email_msg = EmailService.send_next_round_notification(
                            session=session,
                            recipient_email=candidate.email,
                            student_name=candidate.name,
                            job_title=job.title,
                            company_name=company_name,
                            round_name=nr_name,
                            round_date_str=date_str,
                            round_time_str=nr_time or None,
                            further_instructions=rec_comments or None,
                            candidate_id=candidate.id,
                        )
                        email_status_msg = f" & Next-Round Notification Email Dispatched ({email_msg})"
                    else:
                        email_status_msg = " & Decision recorded in candidate profile."

                st.success(f"🎉 Decision finalized: **{mapped_status}** for {candidate.name}{email_status_msg}")
                st.rerun()

    # ── GENERATE & DOWNLOAD DOSSIER REPORT ───────────────────────────────
    html_report = ReportGenerator.generate_candidate_html_report(
        candidate=candidate,
        job=job,
        screening=screening,
        technical_session=tech_session,
    )

    c_dl, c_blank = st.columns([1, 2])
    with c_dl:
        st.download_button(
            "📥 Download Formal Printable Dossier (HTML)",
            data=html_report.encode("utf-8"),
            file_name=f"Hirexp_Dossier_{candidate.name.replace(' ', '_')}.html",
            mime="text/html",
            type="primary",
            use_container_width=True,
        )

    with st.expander("📄 Preview Printable Dossier Document", expanded=False):
        components.html(html_report, height=650, scrolling=True)
