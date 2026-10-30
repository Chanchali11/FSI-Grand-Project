from collections import Counter

import pandas as pd
import plotly.express as px
import streamlit as st

from src.database.models import (
    ResumeDocument,
    ScreeningResult,
)
from src.database.repository import get_db_session
from src.ui.layout import apply_plotly_theme, render_empty_state, render_header, render_kpi_card, setup_sidebar_context

context = setup_sidebar_context()
render_header(
    title="Recruitment Campaign Analytics & Intelligence",
    subtitle="Deep dive into score distributions, skill coverage bottlenecks, and funnel velocity",
    breadcrumbs=["Hirexp Ai", "Intelligence", "Analytics"],
)

job_id = context.get("job_id")
job = context.get("job")

if not job_id or not job:
    st.warning("Please select an active Job in the sidebar.")
    st.stop()

with get_db_session() as session:
    screenings = (
        session.query(ScreeningResult)
        .join(ResumeDocument, ScreeningResult.resume_id == ResumeDocument.id)
        .filter(ResumeDocument.job_id == job_id)
        .all()
    )

    if not screenings:
        render_empty_state("No Analytics Data Available", "No candidate screening records found for this job requisition. Upload resumes to see analytics.", icon="📈")
        st.stop()

    scores = [s.overall_score for s in screenings]
    kw_scores = [s.keyword_coverage_score for s in screenings]
    sim_scores = [s.text_similarity_score for s in screenings]

    # Row 1: Summary Statistics Cards
    avg_score = sum(scores) / len(scores) if scores else 0.0
    pass_rate = (sum(1 for s in scores if s >= job.shortlist_threshold) / len(scores)) * 100 if scores else 0.0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card(
            title="Total Candidates Screened",
            value=len(screenings),
            icon="📄",
            subtitle=f"Requisition: {job.title}",
            color="#4F46E5",
        )
    with c2:
        render_kpi_card(
            title="Average Screening Score",
            value=f"{avg_score:.1f}",
            icon="📊",
            subtitle="Normalized composite metric",
            color="#7C3AED",
        )
    with c3:
        render_kpi_card(
            title="Shortlist Pass Rate",
            value=f"{pass_rate:.1f}%",
            icon="🎯",
            subtitle=f"Threshold: ≥{job.shortlist_threshold:.0f}%",
            color="#16A34A",
        )
    with c4:
        render_kpi_card(
            title="Peak Candidate Score",
            value=f"{max(scores):.1f}",
            icon="🏆",
            subtitle="Top performing candidate",
            color="#2563EB",
        )

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Row 2: Score Distribution & Skill Frequency
    col_hist, col_skills = st.columns([1, 1])

    with col_hist:
        st.markdown(
            """
            <div class="hs-card" style="margin-bottom: 1.25rem;">
              <h3 style="margin: 0 0 4px 0; font-size: 1.05rem; font-weight: 700; color: #F8FAFC;">Candidate Score Distribution</h3>
              <p style="margin: 0 0 12px 0; font-size: 0.8rem; color: #94A3B8;">Relevance score histogram with shortlist threshold cutoff</p>
            """,
            unsafe_allow_html=True,
        )
        df_scores = pd.DataFrame({"Overall Score": scores})
        fig_hist = px.histogram(
            df_scores,
            x="Overall Score",
            nbins=12,
            color_discrete_sequence=["#8B5CF6"],
            range_x=[0, 100],
        )
        fig_hist.add_vline(x=job.shortlist_threshold, line_dash="dash", line_color="#10B981", annotation_text="Threshold Bar", annotation_font_color="#10B981")
        apply_plotly_theme(fig_hist, height=320)
        st.plotly_chart(fig_hist, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_skills:
        st.markdown(
            """
            <div class="hs-card" style="margin-bottom: 1.25rem;">
              <h3 style="margin: 0 0 4px 0; font-size: 1.05rem; font-weight: 700; color: #F8FAFC;">Top Matched vs Missing Skills</h3>
              <p style="margin: 0 0 12px 0; font-size: 0.8rem; color: #94A3B8;">Skill frequency and hiring market gaps</p>
            """,
            unsafe_allow_html=True,
        )
        matched_counter = Counter()
        missing_counter = Counter()

        for s in screenings:
            for m in s.matched_skills or []:
                matched_counter[m] += 1
            for miss in s.missing_skills or []:
                missing_counter[miss] += 1

        top_matched = matched_counter.most_common(6)
        top_missing = missing_counter.most_common(6)

        df_skills = pd.DataFrame(
            [{"Skill": s[0], "Count": s[1], "Type": "Matched"} for s in top_matched]
            + [{"Skill": s[0], "Count": s[1], "Type": "Missing"} for s in top_missing]
        )

        if not df_skills.empty:
            fig_bar = px.bar(
                df_skills,
                x="Skill",
                y="Count",
                color="Type",
                barmode="group",
                color_discrete_map={"Matched": "#10B981", "Missing": "#EF4444"},
            )
            apply_plotly_theme(fig_bar, height=320)
            fig_bar.update_layout(
                legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            render_empty_state("No Skills Data", "No skill distribution records available.", icon="📊")
        st.markdown("</div>", unsafe_allow_html=True)

