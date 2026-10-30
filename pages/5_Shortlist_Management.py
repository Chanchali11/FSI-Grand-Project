import pandas as pd
import streamlit as st

from config import settings
from src.database.models import RecruiterDecision
from src.database.repository import get_db_session
from src.recruitment.invitation_service import InvitationService
from src.recruitment.shortlist_service import ShortlistService
from src.ui.layout import render_badge, render_empty_state, render_header, setup_sidebar_context

context = setup_sidebar_context()
render_header(
    title="Shortlist Governance & Approvals",
    subtitle="Inspect proposed shortlists, authorize human approvals, and generate single-use candidate tokens",
    breadcrumbs=["Hirexp Ai", "Shortlist", "Governance & Approvals"],
)

job_id = context.get("job_id")
job = context.get("job")

if not job_id or not job:
    st.warning("Please select an active Job in the sidebar.")
    st.stop()


with get_db_session() as session:
    # 1. Proposed Candidates (Qualified by AI, Pending Recruiter Approval)
    st.markdown(
        f"""
        <div class="hs-card" style="margin-bottom: 1.25rem;">
          <h3 style="margin: 0 0 4px 0; font-size: 1.05rem; font-weight: 700; color: #F8FAFC !important;">1. Proposed Shortlist Candidates ({job.title})</h3>
          <p style="margin: 0 0 0 0; font-size: 0.8rem; color: #94A3B8 !important;">Candidates meeting the threshold score who require human recruiter sign-off before interview invitations can be issued.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    proposed = ShortlistService.get_candidate_screening_list(
        session=session,
        job_id=job_id,
        decision_filter=RecruiterDecision.PENDING.value,
        min_score=job.shortlist_threshold,
    )

    col_bulk1, col_bulk2 = st.columns([2, 3])
    with col_bulk1:
        st.write(f"**{len(proposed)}** candidates awaiting approval.")
    with col_bulk2:
        if proposed and st.button(f"✓ Bulk-Approve All {len(proposed)} Qualified Candidates", type="primary"):
            count = ShortlistService.bulk_approve_shortlist(session, job_id, threshold_score=job.shortlist_threshold)
            session.commit()
            st.success(f"Approved {count} candidates for shortlisting!")
            st.rerun()

    if proposed:
        prop_rows = []
        for p in proposed:
            prop_rows.append({
                "Candidate": p["candidate_name"],
                "Email": p["candidate_email"],
                "Score": f"{p['overall_score']:.1f}",
                "Keywords (%)": f"{p['keyword_coverage']:.0f}%",
                "Similarity (%)": f"{p['text_similarity']:.0f}%",
                "Mandatory Passed": "✓ Yes" if p["mandatory_passed"] else "✕ Unclear",
                "Recommendation": p["recommendation"],
            })
        st.dataframe(pd.DataFrame(prop_rows), use_container_width=True, hide_index=True)
    else:
        render_empty_state("No Pending Approvals", "No candidates currently pending sign-off in this score tier.", icon="✨")


    # 2. Approved Shortlisted Candidates Ready for Interview Invitation
    st.markdown(
        """
        <div class="hs-card" style="margin-bottom: 1.25rem;">
          <h3 style="margin: 0 0 4px 0; font-size: 1.05rem; font-weight: 700; color: #F8FAFC !important;">2. Authorized Shortlist (Ready to Invite)</h3>
          <p style="margin: 0 0 0 0; font-size: 0.8rem; color: #94A3B8 !important;">Candidates approved for student account creation, secure one-time password setup links, and interview invitation emails.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    approved_list = ShortlistService.get_candidate_screening_list(
        session=session,
        job_id=job_id,
        decision_filter=RecruiterDecision.SHORTLISTED.value,
    )

    col_hdr1, col_hdr2 = st.columns([2.5, 2])
    with col_hdr1:
        st.write(f"**{len(approved_list)}** candidates approved and eligible for interview invitations.")
    with col_hdr2:
        if approved_list:
            bulk_confirm = st.checkbox(f"Confirm bulk dispatch to {len(approved_list)} candidates", key="chk_bulk_confirm")
            if st.button("✉️ Send Bulk Interview Invitations", type="primary", disabled=not bulk_confirm, key="btn_bulk_send"):
                try:
                    invited_count = 0
                    for cand in approved_list:
                        InvitationService.create_invitation(
                            session=session,
                            candidate_id=cand["candidate_id"],
                            job_id=job_id,
                            stage="Comprehensive",
                            expire_hours=72,
                            send_email=True,
                        )
                        invited_count += 1
                    session.commit()
                    st.success(f"Successfully provisioned accounts and emailed {invited_count} candidates!")
                except Exception as e:
                    session.rollback()
                    st.error(f"✕ Error sending bulk invitations: {e}")
                st.rerun()

    if not approved_list:
        render_empty_state("No Authorized Candidates Yet", "Approve qualified candidates from the section above to generate interview invitations.", icon="📋")

    for cand in approved_list:
        with st.container():
            st.markdown(
                f"""
                <div style="background: #19223C; border: 1px solid #232D4B; border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 10px;">
                  <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div>
                      <h4 style="margin: 0; color: #F8FAFC !important; font-size: 1rem; font-weight: 700;">{cand['candidate_name']} ({cand['candidate_email']})</h4>
                      <p style="color: #94A3B8 !important; font-size: 0.84rem; margin: 3px 0 0 0;">Screening Score: <strong style="color: #4ADE80 !important;">{cand['overall_score']:.1f}/100</strong> &bull; Status: <strong style="color: #818CF8;">Authorized Shortlist</strong></p>
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col_stage, col_hours, col_inv = st.columns([2, 1.5, 2])
            with col_stage:
                inv_stage = st.selectbox(
                    f"Interview Stage for {cand['candidate_name']}",
                    options=["Comprehensive", "Technical", "HR"],
                    key=f"stage_{cand['candidate_id']}",
                )
            with col_hours:
                exp_hours = st.number_input(
                    "Token Expiry (Hrs)",
                    min_value=12,
                    max_value=168,
                    value=72,
                    key=f"exp_{cand['candidate_id']}",
                )
            with col_inv:
                st.write("")
                if st.button("✉️ Create Account & Send Invite", key=f"btn_inv_{cand['candidate_id']}", type="primary"):
                    try:
                        invitation, details = InvitationService.create_invitation(
                            session=session,
                            candidate_id=cand["candidate_id"],
                            job_id=job_id,
                            stage=inv_stage,
                            expire_hours=exp_hours,
                            send_email=True,
                        )
                        session.commit()
                        st.session_state[f"last_inv_details_{cand['candidate_id']}"] = details
                        st.success(
                            f"✓ Created student account **{details['username']}** and dispatched invitation for {cand['candidate_name']}!"
                        )
                    except Exception as e:
                        session.rollback()
                        st.error(f"✕ Error creating invitation: {e}")
                    st.rerun()

            # Display direct activation credentials & link card if just issued
            if f"last_inv_details_{cand['candidate_id']}" in st.session_state:
                d = st.session_state[f"last_inv_details_{cand['candidate_id']}"]
                st.markdown(
                    f"""
                    <div style="background: #19223C; border: 1px solid #3730A3; border-left: 4px solid #6366F1; border-radius: 8px; padding: 12px 14px; margin-top: 8px; font-size: 0.85rem; color: #CBD5E1 !important;">
                      <strong style="color: #F8FAFC;">Assigned Student Username:</strong> <code style="color: #A5B4FC; font-weight: 700;">{d['username']}</code><br>
                      <strong style="color: #F8FAFC;">Direct Activation Link:</strong> <a href="{d['setup_url']}" target="_blank" style="color: #818CF8; text-decoration: underline; word-break: break-all;">{d['setup_url']}</a><br>
                      <span style="font-size: 0.8rem; color: #94A3B8 !important;">Delivery Status: {d.get('email_message', 'Dispatched')}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


    # 3. Issued Invitations Log & Recruiter Action Table
    smtp_mode_info = "⚡ <strong>Mock Transport Mode</strong> (Local dev/testing: delivery simulated and recorded in database)" if settings.SMTP_MOCK_MODE or not settings.SMTP_HOST else f"🌐 <strong>Live SMTP Mode</strong> (Host: {settings.SMTP_HOST})"
    st.markdown(
        f"""
        <div class="hs-card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; flex-wrap: wrap; gap: 8px;">
            <div>
              <h3 style="margin: 0; font-size: 1.05rem; font-weight: 700; color: #F8FAFC !important;">3. Active & Completed Interview Invitations</h3>
              <p style="margin: 2px 0 0; font-size: 0.8rem; color: #94A3B8 !important;">Audit trail of provisioned student usernames, single-use setup links, and email delivery status &bull; {smtp_mode_info}</p>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    invitations = InvitationService.get_invitations_for_job(session, job_id)
    if invitations:
        inv_rows = []
        for inv in invitations:
            delivery_display = inv["email_status"]
            if settings.SMTP_MOCK_MODE or not settings.SMTP_USER:
                delivery_display = "SIMULATED (Mock Mode - see .env)"

            inv_rows.append({
                "Student Name": inv["candidate_name"],
                "Email": inv["candidate_email"],
                "Username": inv["username"],
                "Stage": inv["stage"],
                "Invitation Status": inv["invitation_status"],
                "Email Delivery Status": delivery_display,
                "Created (UTC)": inv["created_at"].strftime("%Y-%m-%d %H:%M"),
                "Expires (UTC)": inv["expires_at"].strftime("%Y-%m-%d %H:%M"),
            })
        st.dataframe(pd.DataFrame(inv_rows), use_container_width=True, hide_index=True)

        st.markdown("<h4 style='color: #F8FAFC !important; font-size: 0.92rem; margin: 12px 0 6px 0;'>Quick Recruiter Actions:</h4>", unsafe_allow_html=True)
        col_resend_select, col_resend_btn = st.columns([3, 1])
        with col_resend_select:
            resend_opts = {f"{i['candidate_name']} ({i['username']}) - {i['candidate_email']}": i["id"] for i in invitations}
            sel_inv_label = st.selectbox("Select Candidate to Resend Invitation Email:", options=list(resend_opts.keys()))
        with col_resend_btn:
            st.write("")
            if st.button("🔄 Resend Invitation", use_container_width=True):
                target_inv_id = resend_opts[sel_inv_label]
                try:
                    ok, msg = InvitationService.resend_invitation(session, target_inv_id)
                    session.commit()
                    if ok:
                        st.success(f"✓ Invitation resent successfully! {msg}")
                    else:
                        st.error(f"✕ Failed to resend: {msg}")
                except Exception as e:
                    session.rollback()
                    st.error(f"✕ Unexpected error during resend: {e}")
                st.rerun()

        st.markdown("<hr style='border: 0; border-top: 1px solid #E2E8F0; margin: 15px 0;'>", unsafe_allow_html=True)
        if st.button("🗓️ View Sessions in Interview Management →", use_container_width=True):
            st.switch_page("pages/6_Interview_Management.py")
    else:
        render_empty_state("No Invitations Issued", "No candidate interview tokens have been issued for this requisition yet.", icon="✉️")

