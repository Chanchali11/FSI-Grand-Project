import streamlit as st

from src.ai.claude_client import ClaudeClient
from src.database.repository import DatabaseRepository, get_db_session
from src.recruitment.campaign_service import CampaignService
from src.ui.layout import render_header, setup_sidebar_context

context = setup_sidebar_context()
render_header(
    title="Job Requisition & Campaign Creator",
    subtitle="Configure AI screening criteria, candidate rubrics, and interview stages",
    breadcrumbs=["Hirexp Ai", "Jobs & Campaigns", "Create Requisition"],
)

tab_job, tab_campaign = st.tabs(["💼 Create Job Requisition", "🏢 Create New Recruitment Campaign"])

with tab_campaign:
    st.markdown(
        """
        <div class="hs-card" style="margin-bottom: 1.5rem;">
          <h3 style="margin: 0 0 4px 0; font-size: 1.1rem; font-weight: 700; color: #F8FAFC;">New Recruitment Campaign</h3>
          <p style="margin: 0 0 16px 0; font-size: 0.85rem; color: #94A3B8;">Group related job openings under an enterprise campaign</p>
        """,
        unsafe_allow_html=True,
    )
    with st.form("form_create_campaign"):
        c_c1, c_c2 = st.columns(2)
        with c_c1:
            comp_name = st.text_input("Company Name", value="Acme Global Technologies")
            camp_title = st.text_input("Campaign Title", value="Q4 Software Engineering Scale-up")
        with c_c2:
            comp_domain = st.text_input("Company Domain", value="acmetech.io")
            target_hires = st.number_input("Target Hires", min_value=1, max_value=500, value=5)

        btn_camp = st.form_submit_button("Create Campaign", type="primary")
        if btn_camp:
            with get_db_session() as session:
                new_camp = CampaignService.create_campaign(
                    session=session,
                    company_name=comp_name,
                    campaign_title=camp_title,
                    target_hires=target_hires,
                    company_domain=comp_domain,
                )
                session.commit()
                st.success(f"Campaign '{new_camp.title}' created successfully! (ID: {new_camp.id[:8]})")
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

with tab_job:
    st.markdown(
        """
        <div class="hs-card" style="margin-bottom: 1.5rem;">
          <h3 style="margin: 0 0 4px 0; font-size: 1.1rem; font-weight: 700; color: #F8FAFC;">Define Job Requirements & Screening Weights</h3>
          <p style="margin: 0 0 16px 0; font-size: 0.85rem; color: #94A3B8;">Configure automated parsing, multi-factor matching algorithms, and interview stages</p>
        """,
        unsafe_allow_html=True,
    )

    # Select Campaign to attach
    with get_db_session() as session:
        campaigns = DatabaseRepository.get_campaigns(session)
        camp_map = {f"{c.title} ({c.company.name})": c.id for c in campaigns}

    if not camp_map:
        st.warning("Please create a campaign first in the 'Create New Recruitment Campaign' tab.")
        st.stop()

    selected_camp_key = st.selectbox("Assign to Recruitment Campaign", options=list(camp_map.keys()))
    target_campaign_id = camp_map[selected_camp_key]

    c_title, c_dept = st.columns(2)
    with c_title:
        job_title = st.text_input("Job Title", value="Senior Python Backend Engineer")
    with c_dept:
        dept = st.text_input("Department", value="Platform Engineering")

    c_loc, c_exp, c_years = st.columns(3)
    with c_loc:
        location = st.text_input("Location", value="Remote")
    with c_exp:
        exp_level = st.selectbox("Seniority Level", options=["Entry", "Mid-Level", "Senior", "Lead", "Principal"], index=2)
    with c_years:
        min_years = st.number_input("Minimum Years of Experience", min_value=0.0, max_value=25.0, value=4.0, step=0.5)

    job_description = st.text_area(
        "Job Description & Responsibilities",
        value=(
            "We are seeking an experienced Senior Python Backend Engineer to build high-throughput distributed "
            "microservices, design low-latency PostgreSQL and Redis data architectures, and implement asynchronous "
            "messaging pipelines using Kafka. You will lead architectural reviews, mentor engineers, and ensure 99.99% system reliability."
        ),
        height=130,
    )

    # AI Suggestion Trigger
    if "ai_suggested_skills" not in st.session_state:
        st.session_state.ai_suggested_skills = None

    if st.button("✨ Auto-Extract Structured Requirements with AI"):
        with st.spinner("Analyzing job description and extracting criteria..."):
            client = ClaudeClient()
            extracted = client.extract_job_requirements(job_title=job_title, job_description=job_description)
            st.session_state.ai_suggested_skills = extracted
            st.success("Extracted requirements successfully! You can review and edit below.")

    ai_data = st.session_state.ai_suggested_skills or {}

    col_req, col_pref = st.columns(2)
    with col_req:
        def_req = ", ".join(ai_data.get("required_skills", ["Python", "FastAPI", "SQLAlchemy", "PostgreSQL", "Docker", "REST APIs"]))
        required_skills_str = st.text_area("Required Skills (Comma-separated)", value=def_req, height=80)
    with col_pref:
        def_pref = ", ".join(ai_data.get("preferred_skills", ["Kafka", "Redis", "Kubernetes", "AWS", "CI/CD", "Pytest"]))
        preferred_skills_str = st.text_area("Preferred Skills (Comma-separated)", value=def_pref, height=80)

    col_man, col_edu = st.columns(2)
    with col_man:
        def_man = "\n".join(ai_data.get("mandatory_qualifications", ["Minimum 4 years of backend development", "Proficiency in Python"]))
        mandatory_str = st.text_area("Mandatory Qualifications (One per line)", value=def_man, height=80)
    with col_edu:
        edu_req = st.text_input("Education Requirements", value=ai_data.get("education_requirements", "Bachelor's degree in Computer Science or equivalent"))
        tech_subjects_def = ", ".join(ai_data.get("technical_subjects", ["Python Concurrency", "Database Architecture", "System Design"]))
        tech_subjects_str = st.text_input("Technical Interview Topics", value=tech_subjects_def)

    st.markdown("<h4 style='font-size: 1rem; font-weight: 700; color: #F8FAFC; margin: 1.25rem 0 0.5rem 0;'>Screening Scoring Weights (Normalized to 100%)</h4>", unsafe_allow_html=True)
    w1, w2, w3, w4, w5 = st.columns(5)
    with w1:
        w_kw = st.slider("Keyword Coverage", 0.0, 1.0, 0.25, 0.05)
    with w2:
        w_sim = st.slider("TF-IDF Similarity", 0.0, 1.0, 0.25, 0.05)
    with w3:
        w_exp = st.slider("Experience Match", 0.0, 1.0, 0.25, 0.05)
    with w4:
        w_sem = st.slider("Claude Semantic", 0.0, 1.0, 0.25, 0.05)
    with w5:
        threshold = st.slider("Shortlist Threshold", 50.0, 95.0, 70.0, 1.0)

    # Save Job Requisition
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    if st.button("🚀 Publish Job Requisition", type="primary"):
        req_skills = [s.strip() for s in required_skills_str.split(",") if s.strip()]
        pref_skills = [s.strip() for s in preferred_skills_str.split(",") if s.strip()]
        mandatory = [m.strip() for m in mandatory_str.split("\n") if m.strip()]
        subjects = [s.strip() for s in tech_subjects_str.split(",") if s.strip()]

        with get_db_session() as session:
            job = CampaignService.create_job(
                session=session,
                campaign_id=target_campaign_id,
                title=job_title,
                description=job_description,
                department=dept,
                location=location,
                experience_level=exp_level,
                min_years_experience=min_years,
                required_skills=req_skills,
                preferred_skills=pref_skills,
                mandatory_qualifications=mandatory,
                education_requirements=edu_req,
                technical_subjects=subjects,
                interview_duration_minutes=35,
                interview_stages=["Technical", "HR"],
                weight_keywords=w_kw,
                weight_similarity=w_sim,
                weight_experience=w_exp,
                weight_semantic=w_sem,
                shortlist_threshold=threshold,
            )
            session.commit()
            st.success(f"Job '{job.title}' published successfully! Ready for bulk candidate screening.")
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

