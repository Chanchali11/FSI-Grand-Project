"""
EndoVision AI — Gastrointestinal Disease Classification & Grad-CAM Explainability
Enterprise Medical Computer Vision Platform
"""

from datetime import datetime
import os
from pathlib import Path
import sys
from typing import Dict, List, Optional
import numpy as np
from PIL import Image
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Setup Python module path resolution
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.data.dataset import KVASIR_CLASSES
from src.inference.predict import CLINICAL_INSIGHTS, PredictionService
from src.training.evaluate import ModelEvaluator

# Page Configuration
st.set_page_config(
    page_title="EndoVision AI — Gastrointestinal Deep Learning Workstation",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# DESIGN SYSTEM & CSS TOKENS
# ---------------------------------------------------------
CUSTOM_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  /* Base Typography & Color System */
  html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  }

  /* Main Container Spacing */
  .main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1400px;
  }

  /* Clinical Header Banner */
  .med-header {
    background: linear-gradient(135deg, #071326 0%, #0c1e38 50%, #0d2847 100%);
    border: 1px solid rgba(14, 165, 233, 0.22);
    border-radius: 12px;
    padding: 1.6rem 2rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
  }
  .med-header-title {
    color: #f8fafc;
    font-size: 1.85rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -0.02em;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .med-header-tagline {
    color: #94a3b8;
    font-size: 0.96rem;
    margin-top: 6px;
    font-weight: 400;
  }

  /* Modular Cards */
  .med-card {
    background: #0b1329;
    border: 1px solid rgba(148, 163, 184, 0.14);
    border-radius: 10px;
    padding: 1.25rem 1.4rem;
    margin-bottom: 1rem;
    transition: border-color 0.15s ease;
  }
  .med-card:hover {
    border-color: rgba(56, 189, 248, 0.3);
  }
  .med-card-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: #f1f5f9;
    margin-top: 0;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  /* Metric KPI Blocks */
  .kpi-container {
    background: #0b1329;
    border: 1px solid rgba(148, 163, 184, 0.14);
    border-radius: 10px;
    padding: 1rem 1.25rem;
    text-align: left;
  }
  .kpi-val {
    font-size: 1.75rem;
    font-weight: 700;
    color: #38bdf8;
    line-height: 1.1;
  }
  .kpi-label {
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #94a3b8;
    margin-top: 4px;
    font-weight: 500;
  }
  .kpi-sub {
    font-size: 0.78rem;
    color: #64748b;
    margin-top: 4px;
  }

  /* Pill Badges */
  .pill-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.02em;
  }
  .pill-teal {
    background: rgba(20, 184, 166, 0.14);
    color: #2dd4bf;
    border: 1px solid rgba(20, 184, 166, 0.35);
  }
  .pill-blue {
    background: rgba(59, 130, 246, 0.14);
    color: #60a5fa;
    border: 1px solid rgba(59, 130, 246, 0.35);
  }
  .pill-amber {
    background: rgba(245, 158, 11, 0.14);
    color: #fbbf24;
    border: 1px solid rgba(245, 158, 11, 0.35);
  }
  .pill-rose {
    background: rgba(244, 63, 94, 0.14);
    color: #fb7185;
    border: 1px solid rgba(244, 63, 94, 0.35);
  }

  /* Clinical Disclaimer Callout */
  .clinical-notice {
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(245, 158, 11, 0.35);
    border-left: 4px solid #f59e0b;
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    margin: 1.2rem 0;
    color: #e2e8f0;
    font-size: 0.85rem;
    line-height: 1.5;
  }

  /* Image Containers */
  .img-frame {
    background: #080d1a;
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 8px;
    padding: 8px;
    text-align: center;
  }

  /* Sidebar styling */
  .css-1d391kg, [data-testid="stSidebar"] {
    background-color: #060b17;
    border-right: 1px solid rgba(148, 163, 184, 0.12);
  }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------
# SESSION STATE INITIALIZATION
# ---------------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history = []
if "current_image" not in st.session_state:
    st.session_state.current_image = None
if "current_result" not in st.session_state:
    st.session_state.current_result = None
if "selected_sample_key" not in st.session_state:
    st.session_state.selected_sample_key = None

# ---------------------------------------------------------
# SIDEBAR NAVIGATION & SYSTEM CONTROLS
# ---------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div style="padding: 10px 0 16px 0; border-bottom: 1px solid rgba(148, 163, 184, 0.15); margin-bottom: 16px;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 1.5rem;">🔬</span>
            <span style="font-size: 1.15rem; font-weight: 700; color: #f8fafc; letter-spacing: -0.01em;">EndoVision AI</span>
          </div>
          <div style="font-size: 0.78rem; color: #94a3b8; margin-top: 2px;">
            Gastrointestinal Deep Learning Workstation
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    nav_selection = st.radio(
        "Navigation",
        options=[
            "Clinical Dashboard",
            "Image Classification",
            "Explainable AI (Grad-CAM)",
            "Model Performance & Benchmark",
            "Disease Taxonomy & About",
        ],
        index=0,
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("##### ⚙️ Neural Backbone Configuration")

    model_option = st.selectbox(
        "Active Classifier",
        options=["ConvNeXt-Tiny + CBAM (Proposed)", "DenseNet-121 (Baseline)"],
        index=0,
        help="ConvNeXt-Tiny + CBAM includes channel and spatial attention refinement.",
    )
    model_type = "convnext_cbam" if "ConvNeXt" in model_option else "densenet"

    st.markdown("---")
    st.markdown("##### 🎨 Grad-CAM Visualization Settings")
    heatmap_alpha = st.slider(
        "Attention Overlay Opacity (α)",
        min_value=0.1,
        max_value=0.9,
        value=0.45,
        step=0.05,
        help="Higher values make the attention heatmap more prominent.",
    )
    colormap_choice = st.selectbox(
        "Heatmap Colormap",
        options=["JET", "VIRIDIS", "HOT", "TURBO"],
        index=0,
    )

    st.markdown("---")
    # System Status Indicator
    st.markdown(
        """
        <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 8px; padding: 10px 12px;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="color: #34d399; font-size: 0.85rem;">●</span>
            <span style="font-size: 0.82rem; font-weight: 600; color: #e2e8f0;">Inference Engine Online</span>
          </div>
          <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">
            Target resolution: 224×224 RGB<br>
            Dataset: Kvasir 8-Class Benchmark
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------
# SHARED HEADER BANNER
# ---------------------------------------------------------
def render_header(title: str, subtitle: str):
    st.markdown(
        f"""
        <div class="med-header">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <div>
              <div class="med-header-title">
                <span>🔬</span> {title}
              </div>
              <div class="med-header-tagline">{subtitle}</div>
            </div>
            <div>
              <span class="pill-badge pill-teal">ConvNeXt-Tiny + CBAM Active</span> &nbsp;
              <span class="pill-badge pill-blue">Grad-CAM Supported</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------
# VIEW 1: CLINICAL DASHBOARD
# ---------------------------------------------------------
if nav_selection == "Clinical Dashboard":
    render_header(
        "Clinical Endoscopy AI Workstation",
        "Automated mucosal lesion recognition, anatomical landmark identification, and Grad-CAM explainability"
    )

    # Top KPI Metrics Row
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            """
            <div class="kpi-container">
              <div class="kpi-val" style="color: #34d399;">96.2%</div>
              <div class="kpi-label">Test Accuracy (Proposed)</div>
              <div class="kpi-sub">Baseline DenseNet: 92.4% (+3.8%)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            """
            <div class="kpi-container">
              <div class="kpi-val" style="color: #38bdf8;">95.8%</div>
              <div class="kpi-label">Macro F1-Score</div>
              <div class="kpi-sub">Harmonic mean across 8 categories</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            """
            <div class="kpi-container">
              <div class="kpi-val" style="color: #a78bfa;">96.8%</div>
              <div class="kpi-label">Polyp Sensitivity</div>
              <div class="kpi-sub">High recall for precancerous lesions</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            """
            <div class="kpi-container">
              <div class="kpi-val" style="color: #fbbf24;">34.2 ms</div>
              <div class="kpi-label">Mean Inference Latency</div>
              <div class="kpi-sub">Real-time clinical throughput (>28 FPS)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Workspace Navigation Cards
    c_left, c_right = st.columns([3, 2])

    with c_left:
        st.markdown(
            """
            <div class="med-card">
              <div class="med-card-title">🚀 Quick Start Classification Workspace</div>
              <p style="color: #94a3b8; font-size: 0.9rem; line-height: 1.5; margin-bottom: 1rem;">
                Upload upper or lower gastrointestinal endoscopic imagery to detect mucosal pathology (polyps, ulcerative colitis, esophagitis) or anatomical landmarks with pixel-level Grad-CAM saliency heatmaps.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("##### 📁 Supported Kvasir Endoscopy Classes")
        class_cols = st.columns(2)
        half = len(KVASIR_CLASSES) // 2
        with class_cols[0]:
            for cls_name in KVASIR_CLASSES[:half]:
                is_patho = cls_name in ("polyps", "ulcerative-colitis", "esophagitis")
                badge_type = "pill-rose" if is_patho else "pill-blue"
                category_label = "Pathology" if is_patho else ("Therapy" if "dyed" in cls_name else "Landmark")
                st.markdown(
                    f"""
                    <div style="background: rgba(15, 23, 42, 0.5); padding: 8px 12px; border-radius: 6px; margin-bottom: 6px; border: 1px solid rgba(148, 163, 184, 0.1); display: flex; justify-content: space-between; align-items: center;">
                      <span style="font-size: 0.88rem; color: #f1f5f9; font-weight: 500;">{cls_name.replace('-', ' ').title()}</span>
                      <span class="pill-badge {badge_type}">{category_label}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        with class_cols[1]:
            for cls_name in KVASIR_CLASSES[half:]:
                is_patho = cls_name in ("polyps", "ulcerative-colitis", "esophagitis")
                badge_type = "pill-rose" if is_patho else ("pill-amber" if "dyed" in cls_name else "pill-teal")
                category_label = "Pathology" if is_patho else ("Therapy" if "dyed" in cls_name else "Landmark")
                st.markdown(
                    f"""
                    <div style="background: rgba(15, 23, 42, 0.5); padding: 8px 12px; border-radius: 6px; margin-bottom: 6px; border: 1px solid rgba(148, 163, 184, 0.1); display: flex; justify-content: space-between; align-items: center;">
                      <span style="font-size: 0.88rem; color: #f1f5f9; font-weight: 500;">{cls_name.replace('-', ' ').title()}</span>
                      <span class="pill-badge {badge_type}">{category_label}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with c_right:
        st.markdown(
            """
            <div class="med-card">
              <div class="med-card-title">🕒 Session Classification History</div>
            """,
            unsafe_allow_html=True,
        )

        if not st.session_state.history:
            st.info("No images analyzed in this session yet. Upload or select an image in the Classification tab.")
        else:
            for item in reversed(st.session_state.history[-5:]):
                st.markdown(
                    f"""
                    <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(148, 163, 184, 0.12); border-radius: 6px; padding: 10px 12px; margin-bottom: 8px;">
                      <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 600; color: #38bdf8; font-size: 0.88rem;">
                          {item['predicted_class'].replace('-', ' ').title()}
                        </span>
                        <span class="pill-badge pill-teal">{item['confidence'] * 100:.1f}% Confidence</span>
                      </div>
                      <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">
                        <span>{item['model']}</span>
                        <span>{item['timestamp']}</span>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            """
            <div class="clinical-notice">
              <strong>Clinical Use Disclaimer:</strong><br>
              EndoVision AI is a research decision-support tool. Predictions represent statistical likelihoods from endoscopic pixel patterns and do not substitute for histopathological diagnosis or clinical judgment.
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------
# VIEW 2: IMAGE CLASSIFICATION WORKSPACE
# ---------------------------------------------------------
elif nav_selection == "Image Classification":
    render_header(
        "Endoscopic Image Classification Workspace",
        "Upload high-definition endoscopic frames to generate differential diagnoses and confidence distributions"
    )

    # 1. Image Acquisition Section
    c_up1, c_up2 = st.columns([3, 2])

    with c_up1:
        st.markdown(
            """
            <div class="med-card">
              <div class="med-card-title">📤 Upload Endoscopic Imagery</div>
              <p style="color: #94a3b8; font-size: 0.85rem; margin-bottom: 0.8rem;">
                Supported formats: <strong>JPG, JPEG, PNG</strong> &bull; Maximum recommended size: <strong>25 MB</strong>
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        uploaded_file = st.file_uploader(
            "Drag & drop endoscopic image here",
            type=["jpg", "jpeg", "png"],
            help="High-resolution endoscopic frames from colonoscopy or gastroscopy procedures.",
        )

        if uploaded_file is not None:
            try:
                st.session_state.current_image = Image.open(uploaded_file).convert("RGB")
                st.session_state.selected_sample_key = uploaded_file.name
            except Exception as e:
                st.error(f"Error loading image: {e}")

    with c_up2:
        st.markdown(
            """
            <div class="med-card">
              <div class="med-card-title">🖼️ Quick-Load Curated Clinical Samples</div>
              <p style="color: #94a3b8; font-size: 0.85rem; margin-bottom: 0.8rem;">
                Select from verified reference endoscopic samples across the 8 Kvasir classes:
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        sample_dir = project_root / "data" / "samples"
        sample_options = {}
        if sample_dir.exists():
            for folder in sorted(sample_dir.iterdir()):
                if folder.is_dir():
                    for img_file in sorted(folder.glob("*.jpg")):
                        sample_options[f"{folder.name.replace('-', ' ').title()} ({img_file.name})"] = img_file

        if sample_options:
            selected_sample_label = st.selectbox(
                "Choose Reference Sample:",
                options=["-- Select a clinical sample --"] + list(sample_options.keys()),
                index=0,
            )
            if selected_sample_label != "-- Select a clinical sample --":
                sample_path = sample_options[selected_sample_label]
                st.session_state.current_image = Image.open(sample_path).convert("RGB")
                st.session_state.selected_sample_key = selected_sample_label

    # 2. Preview and Execution Toolbar
    if st.session_state.current_image is not None:
        st.markdown("---")
        preview_col, action_col = st.columns([1, 2])

        with preview_col:
            st.markdown("##### Loaded Image Preview")
            img = st.session_state.current_image
            st.image(img, width='stretch')
            st.caption(f"Dimensions: {img.size[0]}×{img.size[1]} px | Mode: {img.mode}")

            btn_clear = st.button("🗑️ Clear / Remove Image", width='stretch')
            if btn_clear:
                st.session_state.current_image = None
                st.session_state.current_result = None
                st.rerun()

        with action_col:
            st.markdown("##### Prediction Controls")
            st.write(
                f"Selected Classifier: **{model_option}**  \n"
                f"Input will be preprocessed with ImageNet normalization and resized to **224×224**."
            )

            btn_analyze = st.button("⚡ Run Deep Learning Analysis", type="primary", width='stretch')

            if btn_analyze:
                with st.spinner("Executing neural inference and computing Grad-CAM salience..."):
                    pred_service = PredictionService(model_type=model_type)
                    res = pred_service.predict(
                        image_input=st.session_state.current_image,
                        colormap=colormap_choice,
                        alpha=heatmap_alpha,
                    )
                    st.session_state.current_result = res

                    # Log to history
                    st.session_state.history.append({
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "predicted_class": res["predicted_class"],
                        "confidence": res["confidence"],
                        "model": model_option,
                    })

        # 3. Results Section
        if st.session_state.current_result is not None:
            res = st.session_state.current_result
            st.markdown("---")
            st.markdown("### 📊 Diagnostic Evaluation Results")

            conf_pct = res["confidence"] * 100
            is_high_conf = conf_pct >= 90.0
            pill_class = "pill-teal" if is_high_conf else "pill-amber"

            st.markdown(
                f"""
                <div class="med-card" style="border-left: 4px solid #38bdf8;">
                  <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div>
                      <div style="font-size: 0.85rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em;">Model Assessment</div>
                      <h2 style="margin: 2px 0 6px 0; color: #f8fafc; font-size: 1.6rem;">
                        {res['predicted_class'].replace('-', ' ').title()}
                      </h2>
                      <div style="font-size: 0.88rem; color: #cbd5e1;">
                        Architecture: <strong>{model_option}</strong> &bull; Latency: <strong>{res['latency_ms']:.1f} ms</strong>
                      </div>
                    </div>
                    <div>
                      <span class="pill-badge {pill_class}" style="font-size: 1.1rem; padding: 6px 16px;">
                        {conf_pct:.1f}% Confidence
                      </span>
                    </div>
                  </div>
                  <div style="margin-top: 14px; padding-top: 10px; border-top: 1px solid rgba(148, 163, 184, 0.15); color: #cbd5e1; font-size: 0.92rem; line-height: 1.5;">
                    <strong>Pathological / Anatomical Significance:</strong> {res['clinical_insight']}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Probabilities Plotly Chart
            st.markdown("##### Differential Probability Distribution (All 8 Kvasir Categories)")
            chart_data = [
                {"Category": k.replace("-", " ").title(), "Probability (%)": v * 100}
                for k, v in res["all_probabilities"].items()
            ]
            chart_data.reverse()

            fig = px.bar(
                chart_data,
                x="Probability (%)",
                y="Category",
                orientation="h",
                text="Probability (%)",
                color="Probability (%)",
                color_continuous_scale="Tealgrn",
                height=320,
            )
            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig.update_layout(
                margin=dict(l=0, r=40, t=10, b=10),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                xaxis=dict(range=[0, 105], showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                yaxis=dict(showgrid=False),
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig, width='stretch')

            st.markdown(
                """
                <div class="clinical-notice">
                  <strong>Diagnostic Caveat:</strong> Model confidence reflects softmax activation over trained Kvasir visual representations, not definitive clinical certainty. Always cross-reference with biopsy and patient history.
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("👆 Please upload an endoscopic image or pick a curated sample above to begin.")


# ---------------------------------------------------------
# VIEW 3: EXPLAINABLE AI (GRAD-CAM STUDIO)
# ---------------------------------------------------------
elif nav_selection == "Explainable AI (Grad-CAM)":
    render_header(
        "Explainable AI Studio — Grad-CAM Feature Attribution",
        "Inspect convolutional salience heatmaps to understand which endoscopic mucosal patches dictated model classification"
    )

    if st.session_state.current_image is None:
        st.warning("⚠️ No active image selected. Please choose or upload an image in 'Image Classification' first.")
        # Load sample fallback
        sample_path = project_root / "data" / "samples" / "polyps" / "sample_01.jpg"
        if sample_path.exists():
            if st.button("Load Reference Colorectal Polyp Sample for Explainability"):
                st.session_state.current_image = Image.open(sample_path).convert("RGB")
                st.rerun()
    else:
        # Re-compute or retrieve prediction with current colormap/alpha settings
        pred_service = PredictionService(model_type=model_type)
        res = pred_service.predict(
            image_input=st.session_state.current_image,
            colormap=colormap_choice,
            alpha=heatmap_alpha,
        )

        st.markdown(
            f"""
            <div style="margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
              <div>
                <span style="font-size: 1.15rem; font-weight: 600; color: #f8fafc;">
                  Target Class: <span style="color: #38bdf8;">{res['predicted_class'].replace('-', ' ').title()}</span>
                </span>
                <span style="color: #94a3b8; font-size: 0.88rem; margin-left: 8px;">
                  ({res['confidence'] * 100:.1f}% Model Confidence)
                </span>
              </div>
              <div>
                <span class="pill-badge pill-teal">Target Layer: { 'CBAM Feature Map' if 'convnext' in model_type else 'DenseBlock4' }</span>
                <span class="pill-badge pill-blue">Colormap: {colormap_choice}</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Side-by-side comparison
        v_col1, v_col2 = st.columns(2)
        with v_col1:
            st.markdown(
                """
                <div class="img-frame">
                  <div style="font-size: 0.88rem; font-weight: 600; color: #cbd5e1; margin-bottom: 6px;">Original Endoscopic RGB View</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.image(res["original_image"], width='stretch')

        with v_col2:
            st.markdown(
                f"""
                <div class="img-frame">
                  <div style="font-size: 0.88rem; font-weight: 600; color: #cbd5e1; margin-bottom: 6px;">
                    Grad-CAM Salience Overlay ({model_option})
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.image(res["overlay_image"], width='stretch')

        st.markdown(
            """
            <div class="med-card" style="margin-top: 1.2rem;">
              <div class="med-card-title">🔍 Grad-CAM Interpretation Guide</div>
              <ul style="color: #94a3b8; font-size: 0.88rem; line-height: 1.6; margin-bottom: 0;">
                <li><strong>Red / Warm Hues:</strong> High activation gradients. These exact pixel neighborhoods contributed most positively to the class prediction.</li>
                <li><strong>Blue / Cold Hues:</strong> Low salience. These background regions (luminal fluid, peripheral dark shadows) were suppressed by channel and spatial attention.</li>
                <li><strong>ConvNeXt-Tiny + CBAM Advantage:</strong> Dual-domain CBAM attention refines feature activations to adhere strictly to mucosal lesion contours rather than diffuse backgrounds.</li>
              </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="clinical-notice">
              <strong>Explainability Limitation:</strong> Saliency heatmaps indicate statistical weight attribution, not biological causality. A highlighted region does not guarantee that the tissue is histologically malignant.
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------
# VIEW 4: MODEL PERFORMANCE & BENCHMARKS
# ---------------------------------------------------------
elif nav_selection == "Model Performance & Benchmark":
    render_header(
        "Empirical Model Evaluation & Benchmark Metrics",
        "Rigorous comparative evaluation between Proposed ConvNeXt-Tiny + CBAM and Baseline DenseNet-121 on Kvasir test split"
    )

    benchmarks = ModelEvaluator.get_benchmark_comparison()

    # Head-to-Head KPI Comparison Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            """
            <div class="kpi-container">
              <div class="kpi-val" style="color: #34d399;">96.2% vs 92.4%</div>
              <div class="kpi-label">Top-1 Accuracy</div>
              <div class="kpi-sub">Gain: <strong style="color: #34d399;">+3.8%</strong> with CBAM</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
            <div class="kpi-container">
              <div class="kpi-val" style="color: #38bdf8;">95.8% vs 91.8%</div>
              <div class="kpi-label">Macro F1-Score</div>
              <div class="kpi-sub">Gain: <strong style="color: #38bdf8;">+4.0%</strong> with CBAM</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            """
            <div class="kpi-container">
              <div class="kpi-val" style="color: #a78bfa;">96.8% vs 90.5%</div>
              <div class="kpi-label">Polyp Sensitivity</div>
              <div class="kpi-sub">Gain: <strong style="color: #a78bfa;">+6.3%</strong> with CBAM</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            """
            <div class="kpi-container">
              <div class="kpi-val" style="color: #fbbf24;">34.2 vs 28.4 ms</div>
              <div class="kpi-label">Inference Latency</div>
              <div class="kpi-sub">Sub-40ms real-time throughput</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Tabbed Visualizations
    eval_tab1, eval_tab2, eval_tab3 = st.tabs([
        "📊 Confusion Matrix",
        "📈 Training Convergence Curves",
        "📋 Per-Category Performance Breakdown",
    ])

    with eval_tab1:
        st.markdown("##### Normalized Test Confusion Matrix (ConvNeXt-Tiny + CBAM)")
        cm_labels, cm_matrix = ModelEvaluator.get_confusion_matrix_data()

        fig_cm = px.imshow(
            cm_matrix,
            labels=dict(x="Predicted Category", y="True Category", color="Normalized Score"),
            x=cm_labels,
            y=cm_labels,
            color_continuous_scale="Viridis",
            text_auto=".2f",
            aspect="auto",
        )
        fig_cm.update_layout(
            margin=dict(l=0, r=0, t=10, b=10),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cbd5e1", size=11),
            xaxis=dict(tickangle=-30),
        )
        st.plotly_chart(fig_cm, width='stretch')

    with eval_tab2:
        st.markdown("##### 25-Epoch Training Loss & Validation Accuracy Convergence")
        hist = ModelEvaluator.get_training_history_data()

        curve_col1, curve_col2 = st.columns(2)
        with curve_col1:
            fig_loss = go.Figure()
            fig_loss.add_trace(go.Scatter(x=hist["epochs"], y=hist["convnext_val_loss"], mode="lines+markers", name="ConvNeXt+CBAM Val Loss", line=dict(color="#34d399", width=2)))
            fig_loss.add_trace(go.Scatter(x=hist["epochs"], y=hist["densenet_val_loss"], mode="lines", name="DenseNet-121 Val Loss", line=dict(color="#60a5fa", width=2, dash="dash")))
            fig_loss.update_layout(
                title="Validation Cross-Entropy Loss",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                xaxis=dict(title="Epoch", showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                yaxis=dict(title="Loss", showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                margin=dict(l=0, r=0, t=40, b=20),
            )
            st.plotly_chart(fig_loss, width='stretch')

        with curve_col2:
            fig_acc = go.Figure()
            fig_acc.add_trace(go.Scatter(x=hist["epochs"], y=[a * 100 for a in hist["convnext_val_acc"]], mode="lines+markers", name="ConvNeXt+CBAM Val Acc", line=dict(color="#38bdf8", width=2)))
            fig_acc.add_trace(go.Scatter(x=hist["epochs"], y=[a * 100 for a in hist["densenet_val_acc"]], mode="lines", name="DenseNet-121 Val Acc", line=dict(color="#f472b6", width=2, dash="dash")))
            fig_acc.update_layout(
                title="Validation Top-1 Accuracy (%)",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                xaxis=dict(title="Epoch", showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                yaxis=dict(title="Accuracy (%)", showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                margin=dict(l=0, r=0, t=40, b=20),
            )
            st.plotly_chart(fig_acc, width='stretch')

    with eval_tab3:
        st.markdown("##### Per-Class Performance Summary (ConvNeXt-Tiny + CBAM)")
        per_class = ModelEvaluator.get_per_class_summary()
        per_class_table = {
            "Kvasir Endoscopic Category": [k.replace("-", " ").title() for k in per_class.keys()],
            "Precision": [f"{v['precision'] * 100:.1f}%" for v in per_class.values()],
            "Recall (Sensitivity)": [f"{v['recall'] * 100:.1f}%" for v in per_class.values()],
            "F1-Score": [f"{v['f1'] * 100:.1f}%" for v in per_class.values()],
        }
        st.table(per_class_table)

    st.markdown("##### Detailed Metric Comparison Matrix")
    comparison_table = {
        "Metric / Property": [
            "Top-1 Accuracy",
            "Macro Precision",
            "Macro Recall",
            "Macro F1-Score",
            "Polyp Sensitivity",
            "Model Parameters",
            "Disk Footprint",
            "Mean Inference Latency",
            "Attention Mechanism",
            "Explainability Saliency",
        ],
        "DenseNet-121 (Baseline)": [
            "92.4%", "92.0%", "91.7%", "91.8%", "90.5%",
            "7.0 M", "28.1 MB", "28.4 ms",
            "Dense Feature Concatenation", "Coarse feature grid (7×7)",
        ],
        "ConvNeXt-Tiny + CBAM (Proposed)": [
            "96.2%", "96.0%", "95.7%", "95.8%", "96.8%",
            "28.6 M", "114.5 MB", "34.2 ms",
            "Dual-Domain CBAM (Channel + Spatial)", "Fine-grained lesion salience",
        ],
        "Advantage / Delta": [
            "+3.8%", "+4.0%", "+4.0%", "+4.0%", "+6.3%",
            "+21.6 M params", "+86.4 MB", "+5.8 ms",
            "Adaptive feature reweighting", "Precise lesion margin localization",
        ],
    }
    st.table(comparison_table)


# ---------------------------------------------------------
# VIEW 5: DISEASE TAXONOMY & ABOUT
# ---------------------------------------------------------
elif nav_selection == "Disease Taxonomy & About":
    render_header(
        "Kvasir Endoscopy Taxonomy & Research Methodology",
        "Detailed pathological glossary, deep learning architecture specifications, and clinical disclaimers"
    )

    st.subheader("1. Kvasir Dataset Disease Taxonomy")
    st.write(
        "The Kvasir dataset is a gold-standard endoscopic image repository collected from the Vestre Viken Health Trust in Norway. "
        "It encompasses three primary functional classifications: pathological findings, endoscopic therapeutic procedures, and anatomical landmarks."
    )

    for cls_name in KVASIR_CLASSES:
        title = cls_name.replace("-", " ").title()
        insight = CLINICAL_INSIGHTS.get(cls_name, "Endoscopic visual assessment.")
        is_patho = cls_name in ("polyps", "ulcerative-colitis", "esophagitis")
        category_label = "Pathological Finding" if is_patho else ("Therapeutic Intervention" if "dyed" in cls_name else "Normal Landmark")

        with st.expander(f"📌 {title} &nbsp;—&nbsp; {category_label}", expanded=False):
            st.markdown(f"**Clinical Description:** {insight}")
            # Check for sample image
            sample_img_path = project_root / "data" / "samples" / cls_name / "sample_01.jpg"
            if sample_img_path.exists():
                c_img, c_desc = st.columns([1, 3])
                with c_img:
                    st.image(Image.open(sample_img_path), width=220, caption=f"Sample: {title}")
                with c_desc:
                    st.markdown(
                        f"""
                        - **Clinical Classification:** {category_label}
                        - **Target Anatomical Site:** {"Upper GI (Esophagus/Stomach)" if "pylorus" in cls_name or "z-line" in cls_name or "esophagitis" in cls_name else "Lower GI (Colon/Rectum)"}
                        - **Clinical Management:** {"Biopsy / Polypectomy" if is_patho else "Standard Landmark Documentation"}
                        """
                    )

    st.markdown("---")
    st.subheader("2. Deep Learning Pipeline Specifications")
    st.markdown(
        """
        ```
        +-------------------------------------------------------------------------+
        |                          Endoscopic RGB Input                           |
        |                           (224 x 224 x 3)                               |
        +------------------------------------+------------------------------------+
                                             |
                                             v
        +-------------------------------------------------------------------------+
        |                     ConvNeXt-Tiny Backbone                              |
        |    - 7x7 Depthwise Separable Convolutions                               |
        |    - Inverted Bottleneck (4x Expansion)                                 |
        |    - Output Features: [Batch, 768, 7, 7]                                |
        +------------------------------------+------------------------------------+
                                             |
                                             v
        +-------------------------------------------------------------------------+
        |            CBAM: Convolutional Block Attention Module                   |
        |  1. Channel Attention: AvgPool & MaxPool -> Shared MLP -> Sigmoid       |
        |  2. Spatial Attention: Channel Mean & Max -> 7x7 Conv -> Sigmoid        |
        |  Refined Feature Tensor: [Batch, 768, 7, 7]                             |
        +------------------------------------+------------------------------------+
                                             |
                                             v
        +------------------------------------+------------------------------------+
        |      Classification Head           |         Explainability Engine      |
        |  - Adaptive Global Avg Pooling     |  - Grad-CAM on ConvNeXt + CBAM     |
        |  - Dropout (0.2) + Linear Layer    |  - Gradient weights alpha_k        |
        |  - Softmax 8-class probabilities   |  - Jet/Viridis Colormap Overlay    |
        +------------------------------------+------------------------------------+
        ```
        """
    )

    st.markdown(
        """
        <div class="clinical-notice">
          <strong>Regulatory & Ethical Notice:</strong><br>
          This application is designed strictly for research, educational, and clinical decision-support experimentation. It has not received FDA 510(k) clearance or CE Mark approval as a standalone medical diagnostic software device.
        </div>
        """,
        unsafe_allow_html=True,
    )
