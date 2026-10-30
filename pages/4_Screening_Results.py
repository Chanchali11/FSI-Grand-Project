import html
import pandas as pd
import streamlit as st

from src.database.models import InterviewInvitation, InterviewSession, Job, RecruiterDecision
from src.database.repository import get_db_session
from src.recruitment.invitation_service import InvitationService
from src.recruitment.shortlist_service import ShortlistService
from src.reports.report_generator import ReportGenerator
from src.ui.layout import render_badge, render_empty_state, render_header, setup_sidebar_context

context = setup_sidebar_context()
render_header(
    title="Candidate Screening Results & Evidence Trace",
    subtitle="Inspect transparent relevance scores, keyword coverage, skill breakdowns, and perform instant shortlisting",
    breadcrumbs=["Hirexp Ai", "Screening", "Candidate Rankings"],
)

job_id = context.get("job_id")
job = context.get("job")

if not job_id or not job:
    st.warning("Please select an active Job in the sidebar.")
    st.stop()

# Session State for Selected Candidates
if "selected_screening_ids" not in st.session_state:
    st.session_state.selected_screening_ids = set()

# AI Transparency Banner
st.markdown(
    """
    <div style="background: #151C33; border: 1px solid #232D4B; border-left: 4px solid #6366F1; border-radius: 8px; padding: 10px 14px; margin-bottom: 1.25rem; font-size: 0.82rem; color: #CBD5E1 !important; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
      <span>💡 <strong style="color: #F8FAFC;">AI Assistance Transparency:</strong> Screening scores represent multi-factor NLP and semantic analysis. Recruiter evaluation remains the deciding authority.</span>
      <span style="color: #818CF8; font-weight: 600;">Shortlist Cutoff: {thresh:.0f}%</span>
    </div>
    """.format(thresh=job.shortlist_threshold),
    unsafe_allow_html=True,
)

# Filter Bar Card
st.markdown(
    """
    <div class="hs-card" style="margin-bottom: 1.25rem;">
      <h3 style="margin: 0; font-size: 1rem; font-weight: 700; color: #F8FAFC !important;">Filter Candidate Pipeline</h3>
    </div>
    """,
    unsafe_allow_html=True,
)

f_col1, f_col2, f_col3, f_col4 = st.columns([2, 1.5, 1.5, 2])
with f_col1:
    search_query = st.text_input("🔍 Search Candidate, Email, or Skill", "")
with f_col2:
    rec_filter = st.selectbox(
        "Recommendation",
        options=["All", "Meets Configured Criteria", "Needs Manual Review", "Does Not Meet Configured Criteria"],
    )
with f_col3:
    decision_filter = st.selectbox(
        "Decision Status",
        options=["All", "Pending", "Shortlisted", "Rejected", "Invited", "Interviewed", "Selected for Next Round", "Hold for Review"],
    )
with f_col4:
    min_score = st.slider("Minimum Relevance Score", 0.0, 100.0, 0.0, 5.0)


with get_db_session() as session:
    candidates = ShortlistService.get_candidate_screening_list(
        session=session,
        job_id=job_id,
        recommendation_filter=rec_filter,
        min_score=min_score,
        decision_filter=decision_filter,
        search_query=search_query,
    )

    # ── ACTION TOOLBAR: Selection & Shortlisting Actions ──────────────────
    st.markdown(
        """
        <div class="hs-card" style="margin-bottom: 1.25rem;">
          <h4 style="margin: 0; font-size: 1rem; font-weight: 700; color: #F8FAFC !important;">Candidate Actions & Bulk Operations</h4>
    </div>
        """,
        unsafe_allow_html=True,
    )

    col_sel_all, col_clear_all, col_shortlist_btn, col_reject_btn = st.columns([1.2, 1.2, 2.3, 1.8])
    with col_sel_all:
        if st.button("☑️ Select All", use_container_width=True):
            st.session_state.selected_screening_ids = {c["screening_id"] for c in candidates}
            st.rerun()
    with col_clear_all:
        if st.button("⬜ Clear Selection", use_container_width=True):
            st.session_state.selected_screening_ids = set()
            st.rerun()

    selected_count = len(st.session_state.selected_screening_ids)

    with col_shortlist_btn:
        shortlist_clicked = st.button(
            f"✨ Shortlist Selected Candidates ({selected_count})",
            type="primary",
            disabled=(selected_count == 0),
            use_container_width=True,
        )
    with col_reject_btn:
        reject_clicked = st.button(
            f"🚫 Reject Selected ({selected_count})",
            disabled=(selected_count == 0),
            use_container_width=True,
        )

    # Shortlist Action Handling
    if shortlist_clicked:
        target_ids = list(st.session_state.selected_screening_ids)
        updated_n = ShortlistService.bulk_update_decisions(
            session=session,
            screening_ids=target_ids,
            decision=RecruiterDecision.SHORTLISTED.value,
            recruiter_notes="Shortlisted via Bulk Actions Toolbar",
        )
        session.commit()
        st.session_state.selected_screening_ids = set()
        st.success(f"🎉 Successfully shortlisted {updated_n} candidate(s)! Decision saved permanently in database.")
        st.rerun()

    # Reject Action Handling
    if reject_clicked:
        target_ids = list(st.session_state.selected_screening_ids)
        updated_n = ShortlistService.bulk_update_decisions(
            session=session,
            screening_ids=target_ids,
            decision=RecruiterDecision.REJECTED.value,
            recruiter_notes="Rejected via Bulk Actions Toolbar",
        )
        session.commit()
        st.session_state.selected_screening_ids = set()
        st.info(f"Updated {updated_n} candidate(s) to Rejected.")
        st.rerun()


    # ── Header Count, Navigation & CSV Export ────────────────────────────
    col_cnt, col_next, col_exp = st.columns([2.5, 1.3, 0.9])
    with col_cnt:
        st.markdown(
            f"<div style='font-size: 0.95rem; font-weight: 600; color: #F8FAFC !important; margin: 4px 0 14px 0;'>Showing <strong>{len(candidates)}</strong> candidate profiles matching filters for <em>{job.title}</em></div>",
            unsafe_allow_html=True,
        )
    with col_next:
        if st.button("✉️ Shortlist & Send Invitations →", use_container_width=True):
            st.switch_page("pages/5_Shortlist_Management.py")
    with col_exp:
        if candidates:
            df_export = ReportGenerator.export_candidates_to_dataframe(candidates)
            csv_bytes = ReportGenerator.export_to_csv_bytes(df_export)
            st.download_button(
                "📥 Export CSV",
                data=csv_bytes,
                file_name=f"Hirexp_Screening_{job.title.replace(' ', '_')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    # ── Section 3 Required 10-Column Screening Table ───────────────────────
    if candidates:
        summary_rows = []
        for c in candidates:
            score = c['overall_score']
            inv = session.query(InterviewInvitation).filter(
                InterviewInvitation.candidate_id == c["candidate_id"],
                InterviewInvitation.job_id == job_id,
            ).first()
            inv_status = inv.invitation_status if inv else "Not Invited"

            int_session = session.query(InterviewSession).filter(
                InterviewSession.candidate_id == c["candidate_id"],
                InterviewSession.job_id == job_id,
            ).order_by(InterviewSession.started_at.desc()).first()
            int_score = f"{int_session.overall_interview_score:.1f}/100" if (int_session and int_session.overall_interview_score) else "N/A"
            int_status = int_session.status if int_session else "Not Started"

            # 10 Required Columns:
            # 1. Student Name, 2. Email Address, 3. Applied Job, 4. Resume Match Score,
            # 5. Technical Skills Score, 6. Experience Score, 7. Education Match,
            # 8. Screening Status, 9. Shortlist Status, 10. Actions
            summary_rows.append({
                "Student Name": c["candidate_name"],
                "Email Address": c["candidate_email"],
                "Applied Job": job.title,
                "Resume Match Score": f"{score:.1f}/100",
                "Technical Skills Score": f"{c['keyword_coverage']:.0f}%",
                "Experience Score": f"{c['experience_score']:.0f}%",
                "Education Match": c.get("education_match", "Under Review"),
                "Screening Status": c["recommendation"],
                "Shortlist Status": c["recruiter_decision"],
                "Interview Progress": f"{int_status} ({int_score})",
            })

        with st.expander("📊 Screened Candidates Master Table (10-Column Compliance View)", expanded=True):
            st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
    else:
        render_empty_state("No Candidate Profiles Found", "No candidates match the specified filter criteria for this job opening.", icon="👥")

    # ── Detailed Candidate Cards Drill-Down with Multi-Select Checkboxes ──
    st.markdown("<h4 style='font-size: 1.05rem; font-weight: 700; color: #F8FAFC !important; margin: 1rem 0 0.75rem 0;'>Individual Candidate Evidence & Recruiter Decisions</h4>", unsafe_allow_html=True)

    for idx, c in enumerate(candidates):
        score_val = c['overall_score']
        score_color = "#16A34A" if score_val >= job.shortlist_threshold else ("#D97706" if score_val >= 50 else "#DC2626")
        s_id = c["screening_id"]

        is_selected = s_id in st.session_state.selected_screening_ids

        # Row with Checkbox and Expander
        col_chk, col_expander = st.columns([0.4, 9.6])
        with col_chk:
            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            chk_val = st.checkbox("", value=is_selected, key=f"chk_cand_{s_id}")
            if chk_val and s_id not in st.session_state.selected_screening_ids:
                st.session_state.selected_screening_ids.add(s_id)
            elif not chk_val and s_id in st.session_state.selected_screening_ids:
                st.session_state.selected_screening_ids.discard(s_id)

        with col_expander:
            with st.expander(
                f"👤 {c['candidate_name']} — Match Score: {score_val:.1f}/100 | {c['recommendation']} | [{c['recruiter_decision']}]",
                expanded=(idx == 0),
            ):
                col_left, col_right = st.columns([3, 2])

                with col_left:
                    safe_name = html.escape(str(c['candidate_name'] or ''))
                    safe_email = html.escape(str(c['candidate_email'] or ''))
                    safe_phone = html.escape(str(c['candidate_phone'] or ''))
                    safe_filename = html.escape(str(c['filename'] or ''))
                    safe_decision = html.escape(str(c['recruiter_decision'] or ''))
                    safe_edu = html.escape(str(c.get('education_match', 'N/A')))

                    st.markdown(
                        f"""
                        <div style="background: #19223C; border: 1px solid #232D4B; border-radius: 8px; padding: 10px 14px; font-size: 0.85rem; margin-bottom: 12px; color: #94A3B8 !important;">
                          <strong style="color: #CBD5E1;">Email:</strong> <span style="color: #F8FAFC !important;">{safe_email}</span> &nbsp;&bull;&nbsp; 
                          <strong style="color: #CBD5E1;">Phone:</strong> <span style="color: #F8FAFC !important;">{safe_phone}</span> &nbsp;&bull;&nbsp; 
                          <strong style="color: #CBD5E1;">File:</strong> <code>{safe_filename}</code><br>
                          <strong style="color: #CBD5E1;">Education Match:</strong> <span style="color: #F8FAFC !important;">{safe_edu}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # Score breakdown pills
                    st.markdown(
                        f"""
                        <div style="display: flex; gap: 8px; margin: 10px 0; flex-wrap: wrap;">
                          {render_badge(f"Keywords: {c['keyword_coverage']:.0f}%", "primary")}
                          {render_badge(f"TF-IDF Similarity: {c['text_similarity']:.0f}%", "purple")}
                          {render_badge(f"Experience: {c['experience_score']:.0f}%", "info")}
                          {render_badge(f"Semantic: {c['semantic_score']:.0f}%", "neutral")}
                          {render_badge(f"Mandatory: {'Passed' if c['mandatory_passed'] else 'Unclear'}", "success" if c['mandatory_passed'] else "error")}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.markdown("<h5 style='font-size: 0.9rem; font-weight: 700; color: #F8FAFC !important; margin: 12px 0 6px 0;'>Matched & Missing Skills</h5>", unsafe_allow_html=True)
                    matched_badges = " ".join([render_badge(html.escape(str(s)), "success") for s in c['matched_skills']])
                    missing_badges = " ".join([render_badge(html.escape(str(s)), "error") for s in c['missing_skills']])
                    st.markdown(f"**Matched:** {matched_badges if matched_badges else '<em>None detected</em>'}", unsafe_allow_html=True)
                    st.markdown(f"**Missing:** {missing_badges if missing_badges else '<em>None</em>'}", unsafe_allow_html=True)

                    st.markdown("<h5 style='font-size: 0.9rem; font-weight: 700; color: #F8FAFC !important; margin: 14px 0 6px 0;'>Verbatim Resume Evidence</h5>", unsafe_allow_html=True)
                    if c["evidence_excerpts"]:
                        for skill, excerpt in c["evidence_excerpts"].items():
                            st.markdown(f"- **{skill}:** *\"{excerpt}\"*")
                    else:
                        st.caption("No specific excerpts mapped.")

                with col_right:
                    st.markdown(
                        f"""
                        <div style="background: #19223C; border: 1px solid #232D4B; border-radius: 10px; padding: 14px; margin-bottom: 12px;">
                          <div style="font-size: 0.75rem; font-weight: 600; text-transform: uppercase; color: #94A3B8 !important;">Recruiter Review Status</div>
                          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
                            <span style="font-size: 1.15rem; font-weight: 700; color: #F8FAFC !important;">{safe_decision}</span>
                            <span style="font-size: 1.3rem; font-weight: 800; color: {score_color};">{score_val:.1f}<span style="font-size: 0.8rem; color: #94A3B8 !important;">/100</span></span>
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    with st.form(f"decision_form_{c['screening_id']}"):
                        decision_options = ["Pending", "Shortlisted", "Rejected", "Selected for Next Round", "Hold for Review", "Offer Extended", "Hired"]
                        current_idx = decision_options.index(c['recruiter_decision']) if c['recruiter_decision'] in decision_options else 0
                        new_decision = st.selectbox(
                            "Update Recruiter Decision",
                            options=decision_options,
                            index=current_idx,
                        )
                        override_reason = st.text_input("Override Reason (if modifying AI score)", value=c.get("override_reason", ""))
                        notes = st.text_area("Recruiter Evaluation Notes", value=c.get("recruiter_notes", ""), height=70)

                        if st.form_submit_button("Save Decision", type="primary", use_container_width=True):
                            ShortlistService.update_recruiter_decision(
                                session=session,
                                screening_id=c["screening_id"],
                                decision=new_decision,
                                recruiter_notes=notes,
                                override_reason=override_reason,
                            )
                            session.commit()
                            st.success(f"Updated status for {c['candidate_name']} to {new_decision}!")
                            st.rerun()

                    # Quick Shortlist & Reject single buttons
                    col_q1, col_q2 = st.columns(2)
                    with col_q1:
                        if st.button("✓ Shortlist", key=f"q_sl_{s_id}", use_container_width=True):
                            ShortlistService.update_recruiter_decision(
                                session=session,
                                screening_id=s_id,
                                decision=RecruiterDecision.SHORTLISTED.value,
                                recruiter_notes="Directly shortlisted from candidate card",
                            )
                            session.commit()
                            st.success(f"Shortlisted {c['candidate_name']}!")
                            st.rerun()
                    with col_q2:
                        if st.button("✕ Reject", key=f"q_rj_{s_id}", use_container_width=True):
                            ShortlistService.update_recruiter_decision(
                                session=session,
                                screening_id=s_id,
                                decision=RecruiterDecision.REJECTED.value,
                                recruiter_notes="Directly rejected from candidate card",
                            )
                            session.commit()
                            st.info(f"Rejected {c['candidate_name']}.")
                            st.rerun()
