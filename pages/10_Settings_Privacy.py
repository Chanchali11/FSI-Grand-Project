import pandas as pd
import streamlit as st

from config import settings
from src.database.models import AuditEvent, CandidateProfile
from src.database.repository import get_db_session
from src.security.privacy_manager import PrivacyManager
from src.ui.layout import render_badge, render_empty_state, render_header, setup_sidebar_context

context = setup_sidebar_context()
render_header(
    title="Settings, Governance & GDPR Privacy",
    subtitle="Enterprise configuration, Claude AI engine status, and GDPR Right-to-be-Forgotten workflows",
    breadcrumbs=["Hirexp Ai", "Administration", "Settings & Privacy"],
)

tab_profile, tab_privacy, tab_ai, tab_audit = st.tabs([
    "👤 Profile & Workspace",
    "🔒 GDPR Privacy & Data Purge",
    "⚡ AI Engine Configuration",
    "🛡️ System Audit Logs",
])

with tab_profile:
    user = context.get("user")
    user_name = user.name if user else "Recruiter"
    user_email = user.email if user else "recruiter@hiresphere.ai"
    user_role = (user.role.title() if user and user.role else "Recruiter")
    user_company = user.company_name if user else "Global Enterprise"

    st.markdown(
        f"""
        <div class="hs-card" style="margin-bottom: 1.5rem;">
          <h3 style="margin: 0 0 4px 0; font-size: 1.05rem; font-weight: 700; color: #F8FAFC !important;">Authenticated Recruiter Account</h3>
          <p style="margin: 0 0 16px 0; font-size: 0.82rem; color: #94A3B8 !important;">Active session credentials and organization workspace tenancy</p>
          
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-top: 10px;">
            <div style="background: #19223C; border: 1px solid #232D4B; border-radius: 8px; padding: 12px 14px;">
              <span style="font-size: 0.72rem; color: #94A3B8 !important; font-weight: 600; text-transform: uppercase;">User Name</span>
              <div style="font-size: 0.95rem; font-weight: 700; color: #F8FAFC !important; margin-top: 2px;">{user_name}</div>
            </div>
            <div style="background: #19223C; border: 1px solid #232D4B; border-radius: 8px; padding: 12px 14px;">
              <span style="font-size: 0.72rem; color: #94A3B8 !important; font-weight: 600; text-transform: uppercase;">Work Email</span>
              <div style="font-size: 0.95rem; font-weight: 700; color: #F8FAFC !important; margin-top: 2px;">{user_email}</div>
            </div>
            <div style="background: #19223C; border: 1px solid #232D4B; border-radius: 8px; padding: 12px 14px;">
              <span style="font-size: 0.72rem; color: #94A3B8 !important; font-weight: 600; text-transform: uppercase;">Assigned Role</span>
              <div style="margin-top: 4px;">{render_badge(user_role, "primary")}</div>
            </div>
            <div style="background: #19223C; border: 1px solid #232D4B; border-radius: 8px; padding: 12px 14px;">
              <span style="font-size: 0.72rem; color: #94A3B8 !important; font-weight: 600; text-transform: uppercase;">Tenancy / Organization</span>
              <div style="font-size: 0.95rem; font-weight: 700; color: #F8FAFC !important; margin-top: 2px;">🏢 {user_company}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with tab_privacy:
    st.markdown(
        """
        <div class="hs-card" style="margin-bottom: 1.5rem;">
          <h3 style="margin: 0 0 4px 0; font-size: 1.05rem; font-weight: 700; color: #F8FAFC !important;">Candidate Data Deletion ('Right to be Forgotten')</h3>
          <p style="margin: 0 0 0 0; font-size: 0.82rem; color: #94A3B8 !important;">Under GDPR Article 17 and global privacy standards, candidates have the right to demand complete deletion of their profile, resumes, and interview transcripts.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with get_db_session() as session:
        candidates = session.query(CandidateProfile).all()
        cand_map = {f"{c.name} ({c.email or 'N/A'}) - ID: {c.id[:8]}": c.id for c in candidates}

    if cand_map:
        selected_cand_label = st.selectbox("Select Candidate to Erase", options=list(cand_map.keys()))
        target_cand_id = cand_map[selected_cand_label]

        st.warning("⚠️ **Warning**: Deletion is irreversible. All physical PDF resume files, parsed data, screening scores, and interview records will be permanently purged.")
        confirm_purge = st.checkbox("I confirm that the candidate has requested data erasure under GDPR.")

        if st.button("🗑 Permanently Purge Candidate Data", type="primary"):
            if not confirm_purge:
                st.error("Please confirm authorization before proceeding.")
            else:
                with get_db_session() as session:
                    success = PrivacyManager.delete_candidate_data(session, candidate_id=target_cand_id)
                    session.commit()
                    if success:
                        st.success("Successfully purged all records for candidate!")
                        st.rerun()
                    else:
                        st.error("Failed to purge candidate records.")
    else:
        render_empty_state("No Candidate Profiles", "No candidate records currently stored in database.", icon="🛡️")


    st.markdown(
        """
        <div class="hs-card">
          <h3 style="margin: 0 0 4px 0; font-size: 1.05rem; font-weight: 700; color: #F8FAFC !important;">Automated Data Retention Policy</h3>
          <p style="margin: 0 0 0 0; font-size: 0.82rem; color: #94A3B8 !important;">Automated scheduled purging of historical resumes past retention threshold</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    retention_days = st.number_input("Automated Retention Purge Window (Days)", min_value=30, max_value=365, value=settings.DATA_RETENTION_DAYS)
    if st.button("Run Retention Purge Now", type="secondary"):
        with get_db_session() as session:
            count = PrivacyManager.purge_expired_records(session, retention_days=retention_days)
            session.commit()
            st.success(f"Purge complete: {count} expired records removed.")

with tab_ai:
    st.markdown(
        """
        <div class="hs-card" style="margin-bottom: 1.5rem;">
          <h3 style="margin: 0 0 4px 0; font-size: 1.05rem; font-weight: 700; color: #F8FAFC !important;">Anthropic Claude AI Engine Settings</h3>
          <p style="margin: 0 0 0 0; font-size: 0.82rem; color: #94A3B8 !important;">Semantic reasoning, rubric extraction, and candidate evaluation models</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c_m1, c_m2 = st.columns(2)
    with c_m1:
        st.markdown(
            f"""
            <div style="background: #19223C; border: 1px solid #232D4B; border-radius: 8px; padding: 12px 14px; margin-bottom: 10px;">
              <span style="font-size: 0.75rem; color: #94A3B8 !important; font-weight: 600; text-transform: uppercase;">Active Claude Model</span>
              <div style="font-size: 1rem; font-weight: 700; color: #F8FAFC !important; margin-top: 2px;"><code>{settings.CLAUDE_MODEL}</code></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c_m2:
        mode_str = "Deterministic Hybrid Mock (Active)" if settings.USE_MOCK_AI else "Live Production Claude API"
        badge_type = "primary" if settings.USE_MOCK_AI else "success"
        st.markdown(
            f"""
            <div style="background: #19223C; border: 1px solid #232D4B; border-radius: 8px; padding: 12px 14px; margin-bottom: 10px;">
              <span style="font-size: 0.75rem; color: #94A3B8 !important; font-weight: 600; text-transform: uppercase;">Engine Mode</span>
              <div style="margin-top: 4px;">{render_badge(mode_str, badge_type)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<h4 style='font-size: 0.95rem; font-weight: 700; color: #F8FAFC !important; margin: 12px 0 6px 0;'>Select Target Model</h4>", unsafe_allow_html=True)
    new_model = st.selectbox(
        "Preferred Claude Model Architecture",
        options=["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"],
        index=0,
    )
    st.info("💡 To connect a live Claude API key, specify `ANTHROPIC_API_KEY` in `.env` or deployment secrets.")

with tab_audit:
    st.markdown(
        """
        <div class="hs-card">
          <h3 style="margin: 0 0 4px 0; font-size: 1.05rem; font-weight: 700; color: #F8FAFC !important;">System Security & Audit Log Stream</h3>
          <p style="margin: 0 0 0 0; font-size: 0.82rem; color: #94A3B8 !important;">Immutable audit logs for compliance, RBAC, and data privacy records</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with get_db_session() as session:
        audit_events = session.query(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(25).all()
        if audit_events:
            records = [
                {
                    "Timestamp (UTC)": e.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "Action": e.action,
                    "Entity": e.entity_type,
                    "Entity ID": e.entity_id or "-",
                    "Details": str(e.details),
                }
                for e in audit_events
            ]
            st.dataframe(pd.DataFrame(records), use_container_width=True, hide_index=True)
        else:
            render_empty_state("No Audit Events Logged", "Audit events will appear here as recruiter and system actions take place.", icon="🛡️")

