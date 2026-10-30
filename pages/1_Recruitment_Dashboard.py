import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.database.models import (
    AuditEvent,
)
from src.database.repository import get_db_session
from src.recruitment.campaign_service import CampaignService
from src.ui.layout import apply_plotly_theme, render_empty_state, render_header, render_kpi_card, setup_sidebar_context

context = setup_sidebar_context()
render_header(
    title="Executive Recruiter Dashboard",
    subtitle="Live funnel conversion, screening health, and candidate pipeline tracking",
    breadcrumbs=["Hirexp Ai", "Dashboards", "Executive View"],
)

campaign_id = context.get("campaign_id")
job_id = context.get("job_id")

with get_db_session() as session:
    metrics = CampaignService.get_dashboard_metrics(session, campaign_id=campaign_id)

    # Section 15 Required 7 Summary Metrics Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card(
            title="Total Candidates",
            value=metrics["total_resumes"],
            icon="👥",
            subtitle="Uploaded resumes",
            color="#4F46E5",
            bg_color="#EEF2FF",
            border_color="#C7D2FE",
            icon_bg="#E0E7FF",
        )
    with c2:
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
    with c3:
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
    with c4:
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

    r2_1, r2_2, r2_3 = st.columns(3)
    with r2_1:
        render_kpi_card(
            title="Interviews Scheduled",
            value=metrics["invitations_sent"],
            icon="🗓️",
            subtitle="Tokens & sessions active",
            color="#8B5CF6",
            bg_color="#F5F3FF",
            border_color="#DDD6FE",
            icon_bg="#EDE9FE",
        )
    with r2_2:
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
    with r2_3:
        render_kpi_card(
            title="Selected for Next Round",
            value=metrics.get("selected_for_next_round_count", 0),
            icon="🚀",
            subtitle="Advanced candidates",
            color="#16A34A",
            bg_color="#F0FDF4",
            border_color="#BBF7D0",
            icon_bg="#DCFCE7",
        )

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Funnel and Status Charts
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown(
            """
            <div class="hs-card" style="margin-bottom: 1.25rem;">
              <h3 style="margin: 0; font-size: 1.05rem; font-weight: 700; color: #F8FAFC !important;">Candidate Recruitment Funnel</h3>
              <p style="margin: 2px 0 0 0; font-size: 0.8rem; color: #94A3B8 !important;">Stage-by-stage candidate throughput</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        funnel_stages = ["Uploaded", "Processed", "Qualified", "Shortlisted", "Invited", "Interviewed"]
        funnel_values = [
            metrics["total_resumes"],
            metrics["processed_count"],
            metrics["meets_criteria_count"],
            metrics["shortlisted_count"],
            metrics["invitations_sent"],
            metrics["technical_completed"] + metrics["hr_completed"],
        ]

        fig_funnel = go.Figure(
            go.Funnel(
                y=funnel_stages,
                x=funnel_values,
                textinfo="value+percent initial",
                textfont=dict(color="#FFFFFF", family="Inter", size=12),
                marker={"color": ["#6366F1", "#8B5CF6", "#A78BFA", "#06B6D4", "#10B981", "#34D399"]},
                connector=dict(line=dict(color="#E2E8F0", width=1.5)),
            )
        )
        apply_plotly_theme(fig_funnel, height=320)
        st.plotly_chart(fig_funnel, use_container_width=True)

    with col_right:
        st.markdown(
            """
            <div class="hs-card" style="margin-bottom: 1.25rem;">
              <h3 style="margin: 0; font-size: 1.05rem; font-weight: 700; color: #F8FAFC !important;">Document Processing Breakdown</h3>
              <p style="margin: 2px 0 0 0; font-size: 0.8rem; color: #94A3B8 !important;">System ingestion status distribution</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        status_labels = ["Processed", "Needs Manual Review", "Duplicate", "Failed"]
        status_counts = [
            metrics["processed_count"],
            metrics["manual_review_count"],
            metrics["duplicate_count"],
            metrics["failed_count"],
        ]

        if sum(status_counts) > 0:
            fig_pie = px.pie(
                names=status_labels,
                values=status_counts,
                hole=0.55,
                color=status_labels,
                color_discrete_map={
                    "Processed": "#10B981",
                    "Needs Manual Review": "#F59E0B",
                    "Duplicate": "#8B5CF6",
                    "Failed": "#EF4444",
                },
            )
            apply_plotly_theme(fig_pie, height=320)
            fig_pie.update_layout(
                legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            render_empty_state("No Documents Ingested", "No documents uploaded in this campaign yet.", icon="📁")

    # Recent Audit Activity Table
    st.markdown(
        """
        <div class="hs-card" style="margin-top: 1rem;">
          <h3 style="margin: 0 0 4px 0; font-size: 1.05rem; font-weight: 700; color: #F8FAFC !important;">Recent System Audit & Recruiter Actions</h3>
          <p style="margin: 0 0 0 0; font-size: 0.8rem; color: #94A3B8 !important;">Security and decision audit trail</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    audit_events = (
        session.query(AuditEvent)
        .order_by(AuditEvent.created_at.desc())
        .limit(10)
        .all()
    )

    if audit_events:
        table_rows = []
        for e in audit_events:
            table_rows.append({
                "Timestamp (UTC)": e.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "Action": e.action,
                "Entity Type": e.entity_type,
                "Entity ID": e.entity_id[:8] if e.entity_id else "-",
                "Details": str(e.details) if e.details else "-",
            })
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
    else:
        st.caption("No audit activity logged yet.")
