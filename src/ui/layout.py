from pathlib import Path

import streamlit as st

from config import settings
from src.database.repository import DatabaseRepository, get_db_session
from src.security.session_manager import SessionManager


def load_custom_css():
    """Inject the premium dark theme SaaS design system."""
    css_path = Path(__file__).resolve().parent.parent.parent / "assets" / "styles.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()
            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)


def render_breadcrumb(items: list[str]):
    """Render top breadcrumb trail with chevron dividers."""
    crumbs_html = []
    for i, item in enumerate(items):
        if i == len(items) - 1:
            crumbs_html.append(f"<strong style='color: #F8FAFC; font-weight: 600;'>{item}</strong>")
        else:
            crumbs_html.append(f"<span style='color: #94A3B8;'>{item}</span>")
    separator = " <span style='color: #475569; margin: 0 4px;'>/</span> "
    st.markdown(
        f"""
        <div class="hs-breadcrumb" style="display: flex; align-items: center; font-size: 0.8125rem; margin-bottom: 0.6rem; color: #94A3B8;">
          {" ".join(separator.join(crumbs_html).split())}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_header(title: str, subtitle: str = "", breadcrumbs: list[str] | None = None):
    """Render branded enterprise hero banner with glassmorphism card, gradient typography, and AI status."""
    load_custom_css()
    
    crumb_trail = breadcrumbs or ["Hirexp Ai", "Recruitment OS", title]
    crumbs_str = " <span style='color: #475569; margin: 0 5px;'>/</span> ".join(
        [f"<span style='color: {'#F8FAFC; font-weight: 700' if i == len(crumb_trail)-1 else '#94A3B8'};'>{c}</span>" for i, c in enumerate(crumb_trail)]
    )
    
    engine_badge = settings.CLAUDE_MODEL if not settings.USE_MOCK_AI else "Deterministic Hybrid Mock (Active)"
    
    subtitle_tag = f'<p class="hs-hero-tagline">{subtitle}</p>' if subtitle else ''
    hero_html = f"""
    <div class="hs-hero">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap;">
        <div>
          <div style="font-size: 0.8rem; margin-bottom: 6px; display: flex; align-items: center; letter-spacing: 0.01em;">
            {crumbs_str}
          </div>
          <h1 class="hs-hero-title">
            {title}
          </h1>
          {subtitle_tag}
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
          <span class="hs-hero-badge">
            <span style="width: 8px; height: 8px; background: #10B981; border-radius: 50%; display: inline-block;"></span>
            AI Engine: {engine_badge}
          </span>
        </div>
      </div>
    </div>
    """
    st.html(hero_html)


def render_kpi_card(
    title: str,
    value: str | int,
    icon: str = "📊",
    subtitle: str = "",
    delta: str = "",
    color: str = "#8B5CF6",
    bg_color: str = "rgba(22, 30, 54, 0.90)",
    border_color: str = "rgba(139, 92, 246, 0.20)",
    icon_bg: str = "rgba(139, 92, 246, 0.15)",
):
    """Render modern KPI card with glass dark styling, accent borders, and clean metrics."""
    delta_html = f'<div style="font-size: 0.78rem; font-weight: 700; color: #10B981; margin-top: 5px;">{delta}</div>' if delta else ''
    subtitle_html = f'<div style="font-size: 0.78rem; color: #94A3B8; margin-top: 4px; font-weight: 500;">{subtitle}</div>' if subtitle else ''
    
    kpi_html = f"""
    <div class="hs-stat-card">
      <div style="position: absolute; top: 0; left: 0; right: 0; height: 3px; background: {color};"></div>
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
        <span class="hs-stat-label">{title}</span>
        <span style="font-size: 1.15rem; width: 36px; height: 36px; border-radius: 8px; background: {icon_bg}; color: {color}; display: flex; align-items: center; justify-content: center;">{icon}</span>
      </div>
      <div class="hs-stat-value">
        {value}
      </div>
      {delta_html}
      {subtitle_html}
    </div>
    """
    st.html(kpi_html)


def render_badge(text: str, variant: str = "primary") -> str:
    """Return HTML string for modern color-coded badge."""
    styles = {
        "primary": "background: rgba(139, 92, 246, 0.18); color: #C084FC; border: 1px solid rgba(192, 132, 252, 0.35);",
        "secondary": "background: rgba(99, 102, 241, 0.18); color: #A5B4FC; border: 1px solid rgba(165, 180, 252, 0.35);",
        "accent": "background: rgba(6, 182, 212, 0.18); color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.35);",
        "success": "background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.35);",
        "warning": "background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.35);",
        "error": "background: rgba(244, 63, 94, 0.15); color: #FB7185; border: 1px solid rgba(244, 63, 94, 0.35);",
        "info": "background: rgba(6, 182, 212, 0.15); color: #38BDF8; border: 1px solid rgba(6, 182, 212, 0.35);",
        "purple": "background: rgba(139, 92, 246, 0.18); color: #C084FC; border: 1px solid rgba(192, 132, 252, 0.35);",
        "neutral": "background: #19223C; color: #94A3B8; border: 1px solid #2D3A60;",
    }
    style = styles.get(variant, styles["primary"])
    return f'<span style="display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px; border-radius: 9999px; font-size: 0.76rem; font-weight: 600; {style}">{text}</span>'


def render_empty_state(title: str, description: str = "", icon: str = "🔍"):
    """Render a clean, minimal enterprise empty state."""
    desc_html = f'<p class="hs-empty-state-desc">{description}</p>' if description else ""
    empty_html = f"""
    <div class="hs-empty-state">
      <div class="hs-empty-state-icon">{icon}</div>
      <h4 class="hs-empty-state-title">{title}</h4>
      {desc_html}
    </div>
    """
    st.html(empty_html)


def apply_plotly_theme(fig, height: int = 320):
    """Apply a unified, premium SaaS color palette to any Plotly chart."""
    hiresphere_palette = ["#8B5CF6", "#6366F1", "#06B6D4", "#10B981", "#F59E0B", "#F43F5E"]
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, Inter, sans-serif", color="#F8FAFC", size=12),
        margin=dict(l=15, r=15, t=25, b=15),
        height=height,
        colorway=hiresphere_palette,
        hoverlabel=dict(
            bgcolor="#19223C",
            font_size=12,
            font_family="Plus Jakarta Sans, Inter, sans-serif",
            font_color="#FFFFFF",
            bordercolor="#8B5CF6",
        ),
        xaxis=dict(
            gridcolor="#19223C",
            linecolor="#2D3A60",
            tickfont=dict(color="#94A3B8", size=11),
        ),
        yaxis=dict(
            gridcolor="#19223C",
            linecolor="#2D3A60",
            tickfont=dict(color="#94A3B8", size=11),
        ),
        legend=dict(
            font=dict(color="#CBD5E1", size=11),
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    return fig


def render_score_badge(score: float, threshold: float = 70.0) -> str:
    """Return a color-coded HTML score pill based on configurable threshold."""
    if score >= threshold:
        color = "#34D399"
        bg = "rgba(16, 185, 129, 0.18)"
        border = "rgba(16, 185, 129, 0.4)"
        label = "Strong Match"
    elif score >= 50.0:
        color = "#FBBF24"
        bg = "rgba(245, 158, 11, 0.18)"
        border = "rgba(245, 158, 11, 0.4)"
        label = "Moderate Match"
    else:
        color = "#FB7185"
        bg = "rgba(244, 63, 94, 0.18)"
        border = "rgba(244, 63, 94, 0.4)"
        label = "Low Match"

    return (
        f'<span style="background: {bg}; color: {color}; border: 1px solid {border}; '
        f'padding: 3px 9px; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; '
        f'display: inline-flex; align-items: center; gap: 4px;">'
        f'{score:.1f}% &bull; {label}</span>'
    )


def setup_sidebar_context(require_login: bool = True, allowed_roles: list[str] | None = None) -> dict:
    """Provides sidebar campaign/job selection preserved across page navigations with authentication and RBAC."""
    load_custom_css()
    try:
        from src.database.repository import init_db
        init_db()
    except Exception:
        pass
    SessionManager.init_session_state()
    user = SessionManager.get_current_user()

    with st.sidebar:
        # Premium Brand Header (Dark Navy #11172A)
        st.markdown(
            """
            <div style="padding: 16px 14px 12px; border-bottom: 1px solid #1E293B; margin-bottom: 10px; display: flex; align-items: center; gap: 12px;">
              <div style="width: 36px; height: 36px; border-radius: 9px; background: linear-gradient(135deg, #8B5CF6, #6366F1); display: flex; align-items: center; justify-content: center; font-size: 1.15rem; color: white; box-shadow: 0 2px 8px rgba(139, 92, 246, 0.4); flex-shrink: 0;">
                ⚡
              </div>
              <div>
                <h3 style="margin: 0; color: #FFFFFF; font-size: 1.05rem; font-weight: 700; letter-spacing: -0.02em; line-height: 1.2;">Hirexp Ai</h3>
                <p style="margin: 2px 0 0 0; color: #94A3B8; font-size: 0.72rem; font-weight: 500;">Intelligent Recruitment Platform</p>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if user:
            SessionManager.render_sidebar_user_profile()

        # Structured SaaS Navigation Menu
        st.markdown('<div class="hs-nav-category">Workspace</div>', unsafe_allow_html=True)
        st.page_link("app.py", label="Overview", icon="📊")
        st.page_link("pages/1_Recruitment_Dashboard.py", label="Recruitment Dashboard", icon="📈")
        st.page_link("pages/2_Create_Job.py", label="Job Management", icon="💼")

        st.markdown('<div class="hs-nav-category">Candidate Management</div>', unsafe_allow_html=True)
        st.page_link("pages/3_Bulk_Resume_Upload.py", label="Resume Upload", icon="📁")
        st.page_link("pages/4_Screening_Results.py", label="AI Screening Results", icon="🔍")
        st.page_link("pages/5_Shortlist_Management.py", label="Shortlisted Candidates", icon="✨")
        st.page_link("pages/6_Interview_Management.py", label="Interview Scheduling", icon="🗓️")
        st.page_link("pages/8_Candidate_Reports.py", label="Candidate Reports", icon="📄")

        st.markdown('<div class="hs-nav-category">Student Portal</div>', unsafe_allow_html=True)
        st.page_link("pages/11_Student_Login.py", label="Student Login", icon="🎓")
        st.page_link("pages/12_Student_Dashboard.py", label="Student Interview Portal", icon="📋")

        st.markdown('<div class="hs-nav-category">Insights</div>', unsafe_allow_html=True)
        st.page_link("pages/9_Analytics.py", label="Recruitment Analytics", icon="📉")

        st.markdown('<div class="hs-nav-category">Account</div>', unsafe_allow_html=True)
        if not user:
            st.page_link("pages/0_Sign_Up.py", label="Recruiter Sign Up", icon="📝")
        st.page_link("pages/10_Settings_Privacy.py", label="Settings & Privacy", icon="⚙️")

    # Enforce login if required
    if require_login and not user:
        st.markdown(
            f"""
            <div class="hs-hero">
              <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 6px;">
                <span style="font-size: 2rem;">⚡</span>
                <h1 class="hs-hero-title">{settings.APP_NAME}</h1>
              </div>
              <div class="hs-hero-tagline">{settings.APP_TAGLINE}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        SessionManager.render_login_widget()
        st.stop()

    if require_login and user and allowed_roles and user.role not in allowed_roles:
        st.error(f"⛔ Access Denied. Your role ('{user.role}') is not authorized to access this module.")
        st.stop()

    with st.sidebar:
        st.markdown(
            """
            <div style="margin: 14px 4px 6px; padding-top: 10px; border-top: 1px solid #1F2937;">
              <span style="font-size: 0.6875rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #94A3B8;">
                Active Requisition Scope
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with get_db_session() as session:
            # Load all enterprise campaigns so created campaigns/jobs are immediately accessible
            campaigns = DatabaseRepository.get_campaigns(session)
            if not campaigns:
                st.warning("No campaigns found. Please create one in 'Job Management'.")
                return {"campaign_id": None, "job_id": None, "campaign": None, "job": None, "user": user}

            # Prioritize Infosys campaign or user's active campaign to top of list
            campaigns_sorted = sorted(
                campaigns,
                key=lambda c: 0 if "infosys" in c.title.lower() else 1,
            )

            # Unique campaign dictionary with company name
            camp_options = {}
            for c in campaigns_sorted:
                comp_lbl = f" ({c.company.name})" if c.company else ""
                key = f"{c.title}{comp_lbl}"
                # Handle potential duplicate campaign names
                if key in camp_options:
                    key = f"{key} [ID: {c.id[:6]}]"
                camp_options[key] = c.id

            selected_camp_title = st.selectbox(
                "Active Campaign",
                options=list(camp_options.keys()),
                index=0,
                label_visibility="collapsed",
            )
            selected_camp_id = camp_options[selected_camp_title]

            jobs = DatabaseRepository.get_jobs(session, campaign_id=selected_camp_id)
            if not jobs:
                st.info("No job requisitions in this campaign.")
                return {"campaign_id": selected_camp_id, "job_id": None, "campaign": selected_camp_title, "job": None, "user": user}

            # Distinguish multiple jobs by department, experience, or ID
            job_options = {}
            for j in jobs:
                dept_lbl = f" • {j.department}" if j.department else ""
                exp_lbl = f" ({j.experience_level})" if j.experience_level else ""
                lbl = f"{j.title}{dept_lbl}{exp_lbl}"
                if lbl in job_options:
                    lbl = f"{lbl} [#{j.id[:5]}]"
                job_options[lbl] = j.id

            selected_job_title = st.selectbox(
                "Target Job Requisition",
                options=list(job_options.keys()),
                index=0,
            )
            selected_job_id = job_options[selected_job_title]

            job_obj = DatabaseRepository.get_job_by_id(session, selected_job_id)
            if not job_obj:
                return {
                    "campaign_id": selected_camp_id,
                    "job_id": None,
                    "campaign": selected_camp_title,
                    "job": None,
                    "user": user,
                }

            # Requisition Meta Card
            st.markdown(
                f"""
                <div style="background: #1F2937; border: 1px solid #374151; border-radius: 10px; padding: 10px 12px; margin-top: 8px; font-size: 0.78rem; line-height: 1.5; color: #E2E8F0;">
                  <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
                    <span style="color: #94A3B8;">Department:</span>
                    <strong style="color: #F8FAFC;">{job_obj.department or 'Engineering'}</strong>
                  </div>
                  <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
                    <span style="color: #94A3B8;">Location:</span>
                    <strong style="color: #F8FAFC;">{job_obj.location or 'Remote'}</strong>
                  </div>
                  <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
                    <span style="color: #94A3B8;">Shortlist Bar:</span>
                    <strong style="color: #818CF8;">{job_obj.shortlist_threshold:.0f}%</strong>
                  </div>
                  <div style="display: flex; justify-content: space-between;">
                    <span style="color: #94A3B8;">Stages:</span>
                    <strong style="color: #F8FAFC;">{", ".join(job_obj.interview_stages or ['Technical', 'HR'])}</strong>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Detach from session so the object stays usable after session close
            session.expunge(job_obj)

            return {
                "campaign_id": selected_camp_id,
                "job_id": selected_job_id,
                "campaign": selected_camp_title,
                "job": job_obj,
                "user": user,
            }

