import time

import pandas as pd
import streamlit as st

from config import SYNTHETIC_DIR, settings
from src.database.models import ResumeDocument
from src.database.repository import get_db_session
from src.resume.batch_processor import BatchResumeProcessor
from src.ui.layout import render_badge, render_header, setup_sidebar_context

context = setup_sidebar_context()
render_header(
    title="Resume Screening & Bulk Ingestion Engine",
    subtitle="Multi-threaded PDF document parsing, SHA-256 deduplication, and automated scoring",
    breadcrumbs=["Hirexp Ai", "Candidate Screening", "Bulk Ingestion"],
)

job = context.get("job")
campaign_id = context.get("campaign_id")
job_id = context.get("job_id")

if not job or not campaign_id or not job_id:
    st.warning("Please select or create an active Campaign and Job in the sidebar.")
    st.stop()

# Active Requisition Banner
st.markdown(
    f"""
    <div class="hs-card" style="margin-bottom: 1.25rem;">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
        <div>
          <div style="font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #8B5CF6; margin-bottom: 2px;">
            Target Position
          </div>
          <h3 style="margin: 0; color: #F8FAFC; font-size: 1.25rem; font-weight: 700;">{job.title}</h3>
          <p style="margin: 4px 0 0 0; color: #94A3B8; font-size: 0.84rem;">
            Campaign: <strong style="color: #F8FAFC;">{context.get('campaign')}</strong> &bull; 
            Department: <strong style="color: #F8FAFC;">{job.department or 'Engineering'}</strong> &bull; 
            Experience Bar: <strong style="color: #F8FAFC;">{job.min_years_experience:.1f}+ yrs</strong> &bull; 
            Shortlist Bar: <strong style="color: #34D399;">{job.shortlist_threshold:.0f}%</strong>
          </p>
        </div>
        <div style="display: flex; gap: 8px;">
          {render_badge("Active Ingestion", "primary")}
          {render_badge(f"Max Workers: {settings.MAX_WORKERS}", "purple")}
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Upload Configuration Area
st.markdown(
    """
    <div class="hs-card" style="margin-bottom: 1.25rem;">
      <h3 style="margin: 0 0 4px 0; font-size: 1.05rem; font-weight: 700; color: #F8FAFC !important;">Resume Batch Ingestion</h3>
      <p style="margin: 0 0 14px 0; font-size: 0.8rem; color: #94A3B8 !important;">Upload enterprise candidate PDF packages or ingest from the verified realistic dataset</p>
      
      <div style="background: #19223C; border: 1px dashed #334155; border-radius: 8px; padding: 10px 14px; margin-bottom: 14px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; font-size: 0.8rem; color: #CBD5E1 !important;">
        <span>📄 <strong style="color: #F8FAFC;">Supported Formats:</strong> PDF (.pdf)</span>
        <span>⚡ <strong style="color: #F8FAFC;">Deduplication:</strong> Cryptographic SHA-256 Hashing</span>
        <span>🧠 <strong style="color: #F8FAFC;">Parsing Engine:</strong> PyPDF & pdfplumber with OCR Fallback</span>
        <span>🔒 <strong style="color: #F8FAFC;">Data Retention:</strong> PII anonymization & GDPR compliance</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

c_mode, c_workers = st.columns([3, 1])
with c_workers:
    worker_count = st.slider("Concurrency Workers", min_value=1, max_value=12, value=settings.MAX_WORKERS)

with c_mode:
    upload_source = st.radio(
        "Ingestion Source",
        options=["Upload Custom PDF Resumes", "Ingest from Synthetic Dataset (105 Realistic Resumes)"],
        horizontal=True,
    )

files_to_process = []

if upload_source == "Upload Custom PDF Resumes":
    uploaded_files = st.file_uploader(
        "Select or Drag & Drop Multiple PDF Resumes",
        type=["pdf"],
        accept_multiple_files=True,
    )
    if uploaded_files:
        st.write(f"📁 Selected **{len(uploaded_files)}** files for ingestion.")
        preview_rows = []
        for f in uploaded_files:
            content = f.read()
            files_to_process.append((f.name, content))
            preview_rows.append({
                "Filename": f.name,
                "Size (KB)": round(len(content) / 1024, 1),
                "Format": "PDF Document",
                "Status": "Ready to Parse",
            })
        with st.expander("📄 View Uploaded Files Preview List", expanded=False):
            st.dataframe(pd.DataFrame(preview_rows), use_container_width=True, hide_index=True)

else:
    synthetic_resumes_dir = SYNTHETIC_DIR / "resumes"
    if synthetic_resumes_dir.exists():
        synth_files = list(synthetic_resumes_dir.glob("*.pdf"))
        st.info(f"📂 Found **{len(synth_files)}** pre-generated synthetic PDF resumes (including intentional duplicates and variations).")
        sample_size = st.slider("Number of synthetic resumes to ingest", min_value=5, max_value=len(synth_files), value=min(50, len(synth_files)))

        if st.checkbox(f"Load {sample_size} synthetic resumes into batch queue", value=True):
            for p in synth_files[:sample_size]:
                with open(p, "rb") as f:
                    files_to_process.append((p.name, f.read()))
    else:
        st.warning("Synthetic dataset not yet generated. Run the synthetic generator first.")


# Start Ingestion Button
if files_to_process and st.button(f"⚡ Start Batch Processing ({len(files_to_process)} Resumes)", type="primary", use_container_width=True):
    progress_bar = st.progress(0.0)
    status_text = st.empty()
    stats_container = st.empty()

    processor = BatchResumeProcessor(max_workers=worker_count)

    def on_progress(stats: dict):
        pct = stats["percent"] / 100.0
        progress_bar.progress(min(1.0, pct))
        status_text.markdown(f"**Processing Status:** {stats['processed']} of {stats['total']} files ({stats['percent']}%)")
        stats_container.markdown(
            f"""
            <div style="display: flex; gap: 12px; margin: 10px 0; flex-wrap: wrap;">
              {render_badge(f"✓ {stats['successful']} Processed", "success")}
              {render_badge(f"⧉ {stats['duplicates']} Duplicates Detected", "primary")}
              {render_badge(f"✕ {stats['failed']} Failed", "error")}
              <span style="color: #94A3B8 !important; font-size: 0.85rem; align-self: center;">Throughput: <strong style="color: #F8FAFC !important;">{stats['throughput']} resumes/sec</strong></span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    t0 = time.time()
    batch_result = processor.process_batch(
        campaign_id=campaign_id,
        job_id=job_id,
        files_data=files_to_process,
        progress_callback=on_progress,
    )
    total_time = round(time.time() - t0, 2)

    st.success(f"🎉 Batch processing completed in **{total_time}s**!")
    
    col_res1, col_res2 = st.columns([3, 1])
    with col_res1:
        st.markdown(
            f"""
            <div style="background: rgba(22, 163, 74, 0.15); border: 1px solid #16A34A; border-radius: 10px; padding: 12px 16px; margin: 10px 0; color: #F8FAFC !important;">
              <strong style="color: #4ADE80 !important;">✓ Ingestion Summary:</strong> 
              Processed <strong>{len(files_to_process)}</strong> candidate resumes with multi-threaded PDF parsing and scoring.
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_res2:
        if st.button("🔍 View Screening Results →", type="primary", use_container_width=True):
            st.switch_page("pages/4_Screening_Results.py")

# Existing Ingested Documents Table
st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="hs-card">
      <h3 style="margin: 0 0 4px 0; font-size: 1.05rem; font-weight: 700; color: #F8FAFC !important;">Ingested Campaign Documents</h3>
      <p style="margin: 0 0 0 0; font-size: 0.8rem; color: #94A3B8 !important;">Repository of extracted candidate documents and deduplication hashes</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with get_db_session() as session:
    resumes = (
        session.query(ResumeDocument)
        .filter(ResumeDocument.campaign_id == campaign_id, ResumeDocument.job_id == job_id)
        .order_by(ResumeDocument.uploaded_at.desc())
        .all()
    )

    if resumes:
        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            if st.button("🔄 Retry Failed Resumes"):
                with st.spinner("Retrying failed documents..."):
                    proc = BatchResumeProcessor(max_workers=worker_count)
                    retry_res = proc.retry_failed_resumes(campaign_id, job_id)
                    st.success(f"Retry completed: {retry_res.get('summary', {}).get('successful', 0)} recovered.")
                    st.rerun()

        table_data = []
        for r in resumes:
            table_data.append({
                "Filename": r.original_filename,
                "Candidate": r.candidate.name if r.candidate else "Pending",
                "Pages": r.page_count,
                "Size (KB)": round(r.file_size_bytes / 1024, 1),
                "Status": r.processing_status,
                "Duplicate": "Yes" if r.is_duplicate else "No",
                "SHA-256 (prefix)": r.sha256_hash[:12],
                "Score": f"{r.screening_result.overall_score:.1f}" if r.screening_result else "-",
                "Error": r.error_message or "-",
            })
        st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)
    else:
        st.info("No resumes uploaded for this job yet. Use the upload control above.")


