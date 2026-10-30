import streamlit as st

from src.database.models import InterviewQuestion, InterviewSession
from src.database.repository import get_db_session
from src.ui.layout import render_badge, render_empty_state, render_header, setup_sidebar_context

context = setup_sidebar_context()
render_header(
    title="Interview Session Operations & Transcripts",
    subtitle="Track candidate interview progress, transcripts, rubric evaluations, and session timestamps",
    breadcrumbs=["Hirexp Ai", "Interviews", "Session Operations"],
)

job_id = context.get("job_id")
job = context.get("job")

if not job_id:
    st.warning("Please select an active Job in the sidebar.")
    st.stop()

with get_db_session() as session:
    sessions = (
        session.query(InterviewSession)
        .filter(InterviewSession.job_id == job_id)
        .order_by(InterviewSession.started_at.desc())
        .all()
    )

    if not sessions:
        render_empty_state("No Interview Sessions Recorded", "No interview sessions initiated for this job opening yet. Issue invitation tokens in Shortlist Management or launch a test interview.", icon="🎙️")
        if st.button("✨ Issue Invitations in Shortlist Management →", use_container_width=True):
            st.switch_page("pages/5_Shortlist_Management.py")
        st.stop()

    st.markdown(
        f"<div style='font-size: 0.95rem; font-weight: 600; color: #F8FAFC !important; margin-bottom: 1rem;'>Total Recorded Sessions: <strong>{len(sessions)}</strong></div>",
        unsafe_allow_html=True,
    )

    for s in sessions:
        cand_name = s.candidate.name if s.candidate else "Candidate"
        cand_email = s.candidate.email if s.candidate else "N/A"
        overall_score = f"{s.overall_interview_score:.1f}/100" if s.overall_interview_score else "In Progress"

        with st.expander(
            f"🎙 {cand_name} ({cand_email}) | Stage: {s.stage} | Status: {s.status} | Score: {overall_score}",
            expanded=False,
        ):
            st.markdown(
                f"""
                <div style="background: #19223C; border: 1px solid #232D4B; border-radius: 8px; padding: 10px 14px; font-size: 0.84rem; color: #94A3B8 !important; margin-bottom: 14px;">
                  Session ID: <code style="color: #A5B4FC !important;">{s.id}</code> &bull; 
                  Started: <strong style="color: #F8FAFC !important;">{s.started_at.strftime('%Y-%m-%d %H:%M UTC')}</strong> &bull; 
                  Completed: <strong style="color: #F8FAFC !important;">{s.completed_at.strftime('%Y-%m-%d %H:%M UTC') if s.completed_at else 'In Progress'}</strong> &bull;
                  Consent Recorded: {'<strong style="color: #4ADE80 !important;">✓ Yes</strong>' if s.candidate_consent_given else '<strong style="color: #F87171 !important;">✕ No</strong>'}
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Questions & Answers Table
            questions = (
                session.query(InterviewQuestion)
                .filter(InterviewQuestion.session_id == s.id)
                .order_by(InterviewQuestion.question_order.asc())
                .all()
            )

            for q in questions:
                score_str = f"{q.score:.1f}" if q.score is not None else "Pending"
                st.markdown(
                    f"""
                    <div style="background: #151C33; border: 1px solid #232D4B; border-left: 4px solid #6366F1; border-radius: 10px; padding: 1.15rem; margin-bottom: 1rem; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);">
                      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="color: #818CF8; font-weight: 700; font-size: 0.85rem; text-transform: uppercase;">Q{q.question_order} &bull; {q.category}</span>
                        <span style="background: rgba(99, 102, 241, 0.2); color: #C7D2FE; padding: 2px 8px; border-radius: 9999px; font-size: 0.78rem; font-weight: 700; border: 1px solid #6366F1;">
                          Score: {score_str} / 100
                        </span>
                      </div>
                      
                      <div style="margin: 6px 0 10px 0; color: #F8FAFC !important; font-size: 0.95rem; font-weight: 600; line-height: 1.45;">
                        {q.question_text}
                      </div>
                      
                      <div style="background: #19223C; border: 1px solid #232D4B; padding: 10px 14px; border-radius: 8px; margin: 8px 0;">
                        <div style="color: #94A3B8 !important; font-size: 0.75rem; text-transform: uppercase; font-weight: 600;">Candidate Response ({q.answer_mode}):</div>
                        <div style="color: #E2E8F0 !important; font-size: 0.88rem; margin-top: 4px; line-height: 1.5;">
                          {q.candidate_answer or '<em>No answer submitted</em>'}
                        </div>
                      </div>

                      <div style="font-size: 0.84rem; color: #CBD5E1 !important; margin-top: 8px; line-height: 1.45;">
                        <strong style="color: #F8FAFC !important;">AI Evaluation Feedback:</strong> {q.evaluation_feedback or 'Pending evaluation'}
                      </div>
                      
                      <div style="display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap;">
                        {render_badge(f"Demonstrated: {', '.join(q.correct_concepts or ['None'])}", "success")}
                        {render_badge(f"Omitted: {', '.join(q.missing_concepts or ['None'])}", "error")}
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

