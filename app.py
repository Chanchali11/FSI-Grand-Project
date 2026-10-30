import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Configure wide page layout
st.set_page_config(
    page_title="Hirexp Ai — Recruiter Command Center",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.database.models import AuditEvent, Job
from src.database.repository import get_db_session, init_db
from src.recruitment.campaign_service import CampaignService
from src.ui.layout import apply_plotly_theme, render_empty_state, render_header, render_kpi_card, setup_sidebar_context

# Initialize DB
init_db()

# Render Header & Sidebar
context = setup_sidebar_context()
user = context.get("user")
user_name = user.name if user else "Recruiter"

# Top Banner / Welcome Action Bar
col_welc, col_act1, col_act2 = st.columns([2.4, 0.8, 0.8])
with col_welc:
    render_header(
        title=f"Welcome back, {user_name}",
        subtitle="Here's what's happening with your recruitment pipeline.",
        breadcrumbs=["Hirexp Ai", "Command Center", "Overview"],
    )
with col_act1:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("➕ Create New Job", type="primary", use_container_width=True):
        st.switch_page("pages/2_Create_Job.py")
with col_act2:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("📁 Upload Resumes", use_container_width=True):
        st.switch_page("pages/3_Bulk_Resume_Upload.py")

# Query live metrics & actual application data
with get_db_session() as session:
    metrics = CampaignService.get_dashboard_metrics(session, campaign_id=context.get("campaign_id"))
    total_jobs = session.query(Job).count()
    if context.get("campaign_id"):
        total_jobs = session.query(Job).filter(Job.campaign_id == context.get("campaign_id")).count()

# ── Section 15 Recruiter Dashboard: 7 Summary Metric Cards ───────────
kpi_row1_col1, kpi_row1_col2, kpi_row1_col3, kpi_row1_col4 = st.columns(4)
with kpi_row1_col1:
    render_kpi_card(
        title="Total Candidates",
        value=metrics["total_resumes"],
        icon="👥",
        subtitle="Uploaded to platform",
        color="#4F46E5",
        bg_color="#EEF2FF",
        border_color="#C7D2FE",
        icon_bg="#E0E7FF",
    )
with kpi_row1_col2:
    render_kpi_card(
        title="Screened Candidates",
        value=metrics["processed_count"],
        icon="📄",
        subtitle=f"{metrics['meets_criteria_count']} qualified by AI",
        color="#6366F1",
        bg_color="#EEF2FF",
        border_color="#C7D2FE",
        icon_bg="#E0E7FF",
    )
with kpi_row1_col3:
    render_kpi_card(
        title="Shortlisted Candidates",
        value=metrics["shortlisted_count"],
        icon="✨",
        subtitle="Approved by recruiter",
        color="#7C3AED",
        bg_color="#F5F3FF",
        border_color="#DDD6FE",
        icon_bg="#EDE9FE",
    )
with kpi_row1_col4:
    render_kpi_card(
        title="Invitations Sent",
        value=metrics["invitations_sent"],
        icon="✉️",
        subtitle=f"{metrics['interviews_pending']} pending interview",
        color="#06B6D4",
        bg_color="#ECFEFF",
        border_color="#A5F3FC",
        icon_bg="#CFFAFE",
    )

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

kpi_row2_col1, kpi_row2_col2, kpi_row2_col3 = st.columns(3)
with kpi_row2_col1:
    render_kpi_card(
        title="Interviews Scheduled",
        value=metrics["invitations_sent"],
        icon="🗓️",
        subtitle=f"Across active requisitions",
        color="#8B5CF6",
        bg_color="#F5F3FF",
        border_color="#DDD6FE",
        icon_bg="#EDE9FE",
    )
with kpi_row2_col2:
    render_kpi_card(
        title="Interviews Completed",
        value=metrics["interviews_completed"],
        icon="🎙️",
        subtitle="Evaluated responses",
        color="#10B981",
        bg_color="#ECFDF5",
        border_color="#A7F3D0",
        icon_bg="#D1FAE5",
    )
with kpi_row2_col3:
    render_kpi_card(
        title="Selected for Next Round",
        value=metrics.get("selected_for_next_round_count", 0),
        icon="🚀",
        subtitle="Final round advancement",
        color="#16A34A",
        bg_color="#F0FDF4",
        border_color="#BBF7D0",
        icon_bg="#DCFCE7",
    )

st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

# ── Charts Row: Pipeline Funnel + Candidate Screening Distribution ────
col_pipe, col_dist = st.columns([3, 2])

with col_pipe:
    st.markdown(
        """
        <div class="hs-card" style="margin-bottom: 1.25rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <div>
              <h3 style="margin: 0; font-size: 1.05rem; font-weight: 700; color: #F8FAFC;">Recruitment Pipeline Funnel</h3>
              <p style="margin: 2px 0 0; font-size: 0.8rem; color: #94A3B8;">Stage-by-stage candidate conversion rates</p>
            </div>
            <span style="font-size: 0.75rem; background: rgba(139, 92, 246, 0.2); color: #C084FC; padding: 3px 10px; border-radius: 9999px; font-weight: 600; border: 1px solid rgba(139, 92, 246, 0.4);">Live Funnel</span>
          </div>
        """,
        unsafe_allow_html=True,
    )
    
    stages = ["Uploaded", "Processed", "Qualified", "Shortlisted", "Invited", "Interviewed"]
    values = [
        metrics["total_resumes"],
        metrics["processed_count"],
        metrics["meets_criteria_count"],
        metrics["shortlisted_count"],
        metrics["invitations_sent"],
        metrics["technical_completed"] + metrics["hr_completed"],
    ]

    fig_funnel = go.Figure(
        go.Funnel(
            y=stages,
            x=values,
            textinfo="value+percent initial",
            textfont=dict(color="#F8FAFC", family="Inter", size=12),
            marker=dict(
                color=["#6366F1", "#8B5CF6", "#A78BFA", "#06B6D4", "#10B981", "#34D399"],
                line=dict(width=1, color="rgba(255, 255, 255, 0.2)"),
            ),
            connector=dict(line=dict(color="#2D3A60", width=1.5)),
        )
    )
    apply_plotly_theme(fig_funnel, height=310)
    st.plotly_chart(fig_funnel, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_dist:
    st.markdown(
        """
        <div class="hs-card" style="margin-bottom: 1.25rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <div>
              <h3 style="margin: 0; font-size: 1.05rem; font-weight: 700; color: #F8FAFC;">Candidate Screening Distribution</h3>
              <p style="margin: 2px 0 0; font-size: 0.8rem; color: #94A3B8;">Relevance breakdown by qualification criteria</p>
            </div>
          </div>
        """,
        unsafe_allow_html=True,
    )

    screening_labels = ["Meets Criteria", "Needs Manual Review", "Duplicates", "Failed"]
    screening_values = [
        metrics["meets_criteria_count"],
        metrics["manual_review_count"],
        metrics["duplicate_count"],
        metrics["failed_count"],
    ]

    if sum(screening_values) > 0:
        fig_donut = px.pie(
            names=screening_labels,
            values=screening_values,
            hole=0.6,
            color=screening_labels,
            color_discrete_map={
                "Meets Criteria": "#10B981",
                "Needs Manual Review": "#F59E0B",
                "Duplicates": "#8B5CF6",
                "Failed": "#EF4444",
            },
        )
        apply_plotly_theme(fig_donut, height=310)
        fig_donut.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_donut, use_container_width=True)
    else:
        render_empty_state("No Screening Data Yet", "Upload candidate resumes to see live qualification distribution.", icon="📊")
    st.markdown("</div>", unsafe_allow_html=True)

# ── Recent Recruitment Activity ──────────────────────────────
st.markdown(
    """
    <div class="hs-card" style="margin-bottom: 1.75rem;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <div>
          <h3 style="margin: 0; font-size: 1.05rem; font-weight: 700; color: #F8FAFC;">Recent Recruitment Activity</h3>
          <p style="margin: 2px 0 0; font-size: 0.8rem; color: #94A3B8;">Audit trail of actions and system events</p>
        </div>
        <span style="font-size: 0.75rem; color: #94A3B8;">Automated Security Logging</span>
      </div>
    """,
    unsafe_allow_html=True,
)

with get_db_session() as session:
    recent_events = (
        session.query(AuditEvent)
        .order_by(AuditEvent.created_at.desc())
        .limit(6)
        .all()
    )

if recent_events:
    event_data = []
    for ev in recent_events:
        event_data.append({
            "Timestamp": ev.created_at.strftime("%b %d, %H:%M UTC"),
            "Action Type": ev.action,
            "Target Entity": ev.entity_type,
            "Entity Reference": ev.entity_id[:8] if ev.entity_id else "-",
            "Event Summary": str(ev.details) if ev.details else "Completed",
        })
    st.dataframe(pd.DataFrame(event_data), use_container_width=True, hide_index=True)
else:
    st.caption("No recent activity recorded yet.")

st.markdown("</div>", unsafe_allow_html=True)

# ── Quick Action Workflow Cards ──────────────────────────────
st.markdown("<h3 style='font-size: 1.15rem; font-weight: 700; color: #F8FAFC; margin: 1.5rem 0 1rem 0;'>Recruitment Platform Modules</h3>", unsafe_allow_html=True)

w1, w2, w3 = st.columns(3)

with w1:
    st.markdown(
        """
        <div class="hs-card" style="margin-bottom: 1rem;">
          <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(99, 102, 241, 0.2); display: flex; align-items: center; justify-content: center; font-size: 1.2rem; margin-bottom: 12px;">
            📄
          </div>
          <h4 style="margin: 0 0 6px 0; color: #F8FAFC; font-size: 1rem; font-weight: 700;">1. Resume Screening</h4>
          <p style="color: #94A3B8; font-size: 0.84rem; line-height: 1.5; margin-bottom: 14px;">
            Multi-threaded PDF parsing, SHA-256 deduplication, and multi-factor relevance scoring.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Launch Resume Ingestion →", key="btn_w_upload", use_container_width=True):
        st.switch_page("pages/3_Bulk_Resume_Upload.py")

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="hs-card" style="margin-bottom: 1rem;">
          <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(139, 92, 246, 0.2); display: flex; align-items: center; justify-content: center; font-size: 1.2rem; margin-bottom: 12px;">
            🔍
          </div>
          <h4 style="margin: 0 0 6px 0; color: #F8FAFC; font-size: 1rem; font-weight: 700;">2. Screening Results</h4>
          <p style="color: #94A3B8; font-size: 0.84rem; line-height: 1.5; margin-bottom: 14px;">
            Inspect transparent rubric weights, keyword matches, and verbatim PDF quote evidence.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Inspect Screening Results →", key="btn_w_results", use_container_width=True):
        st.switch_page("pages/4_Screening_Results.py")

with w2:
    st.markdown(
        """
        <div class="hs-card" style="margin-bottom: 1rem;">
          <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(16, 185, 129, 0.2); display: flex; align-items: center; justify-content: center; font-size: 1.2rem; margin-bottom: 12px;">
            ✅
          </div>
          <h4 style="margin: 0 0 6px 0; color: #F8FAFC; font-size: 1rem; font-weight: 700;">3. Shortlisted Candidates</h4>
          <p style="color: #94A3B8; font-size: 0.84rem; line-height: 1.5; margin-bottom: 14px;">
            Recruiter human approval governance and cryptographically secure interview token generation.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Manage Candidate Shortlist →", key="btn_w_shortlist", use_container_width=True):
        st.switch_page("pages/5_Shortlist_Management.py")

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="hs-card" style="margin-bottom: 1rem;">
          <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(6, 182, 212, 0.2); display: flex; align-items: center; justify-content: center; font-size: 1.2rem; margin-bottom: 12px;">
            🤖
          </div>
          <h4 style="margin: 0 0 6px 0; color: #F8FAFC; font-size: 1rem; font-weight: 700;">4. Virtual Interview</h4>
          <p style="color: #94A3B8; font-size: 0.84rem; line-height: 1.5; margin-bottom: 14px;">
            Live interactive 2D AI interviewer avatar with audio synthesis, speech tests, and rubric scoring.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Open Virtual Interview Room →", key="btn_w_virtual", use_container_width=True):
        st.switch_page("pages/7_Virtual_Interview.py")

with w3:
    st.markdown(
        """
        <div class="hs-card" style="margin-bottom: 1rem;">
          <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(245, 158, 11, 0.2); display: flex; align-items: center; justify-content: center; font-size: 1.2rem; margin-bottom: 12px;">
            📊
          </div>
          <h4 style="margin: 0 0 6px 0; color: #F8FAFC; font-size: 1rem; font-weight: 700;">5. Candidate Reports</h4>
          <p style="color: #94A3B8; font-size: 0.84rem; line-height: 1.5; margin-bottom: 14px;">
            Comprehensive dossiers combining resume evidence, transcripts, rubrics, and downloadable reports.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("View Candidate Dossiers →", key="btn_w_reports", use_container_width=True):
        st.switch_page("pages/8_Candidate_Reports.py")

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="hs-card" style="margin-bottom: 1rem;">
          <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(244, 63, 94, 0.2); display: flex; align-items: center; justify-content: center; font-size: 1.2rem; margin-bottom: 12px;">
            📈
          </div>
          <h4 style="margin: 0 0 6px 0; color: #F8FAFC; font-size: 1rem; font-weight: 700;">6. Analytics & Privacy</h4>
          <p style="color: #94A3B8; font-size: 0.84rem; line-height: 1.5; margin-bottom: 14px;">
            Score distributions, skill coverage bottlenecks, audit logs, and GDPR Right-to-be-Forgotten purge.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Explore Analytics & Privacy →", key="btn_w_analytics", use_container_width=True):
        st.switch_page("pages/9_Analytics.py")

