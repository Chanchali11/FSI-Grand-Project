# Hirexp Ai ⚡
> **Resume screening with AI-powered interview using interactive AI avatars.**

Hirexp Ai is an enterprise-grade AI-powered bulk resume screening and virtual interview platform built with Python, Streamlit, SQLAlchemy, PyMuPDF, Scikit-learn, and the Anthropic Claude API.

---

## 🌟 Key Features

### 1. Multi-Campaign & Requisition Architecture
- Support for multiple companies and isolated recruitment campaigns.
- Complete job requisition definitions including required/preferred skills, mandatory criteria, interview topics, and customizable weights.
- **AI Job Requirement Extraction**: Automatically structure job descriptions into discrete skills and evaluation criteria.

### 2. High-Throughput Bulk Resume Processing
- **PyMuPDF Document Engine**: High-speed native text extraction from single and multi-page PDFs.
- **Document Health Checking**: Detects encrypted, corrupted, empty, or scanned PDFs.
- **SHA-256 Deduplication**: Prevents duplicate document processing within campaigns.
- **Bounded Concurrency**: Configurable thread-pool workers (tested at **20+ resumes/sec**).
- **Safe Retries & Live Progress**: Batch continues when individual documents fail, with safe one-click retries.

### 3. Multi-Metric Evidence-Based Screening Engine
- **Keyword Coverage**: Direct percentage match against recruiter-specified core skills.
- **TF-IDF Cosine Similarity**: Scikit-learn textual alignment between resume content and job requisitions.
- **Experience Match**: Deterministic calculation verifying minimum years of experience.
- **Claude Semantic Analysis**: Claude AI comparison extracting verifiable evidence excerpts.
- **Demographic Characteristic-Free**: Excludes name, age, gender, race, religion, and marital status from all scoring algorithms.

### 4. Shortlist Governance & Secure Invitations
- Transparent candidate tables with filtering, sorting, and search.
- Recruiter human sign-off with recorded override reasoning.
- **Cryptographic Tokens**: Single-use HMAC-signed invitation tokens with configurable expiration (72h default) and replay protection.

### 5. Virtual AI Avatar Interview Room
- **Animated 2D SVG Avatar**: Interactive interviewer with dynamic states (`idle`, `speaking`, `listening`, `thinking`).
- **Web Speech Synthesis (TTS)**: Reads questions aloud in the browser.
- **Microphone & Audio Check**: Real-time microphone testing with typed answer fallbacks.
- **Technical & HR Interview Tracks**: Adaptive question generation covering architecture, coding logic, and STAR-framework behavioral scenarios.
- **100-Point Transparent Rubrics**: Evaluates correctness, reasoning, edge cases, and communication without bias.

### 6. Candidate Dossiers & Analytics
- Printable, downloadable HTML candidate evaluation dossiers.
- CSV and Excel export formats for recruiting ATS integration.
- Funnel drop-off charts and skill bottleneck analytics via Plotly.
- **GDPR Compliance**: On-demand "Right to be Forgotten" candidate data purge.

---

## 🚀 Benchmark Performance Results

Conducted using the synthetic dataset generator on 50 high-volume PDF resumes with 6 worker threads:

| Metric | Result |
| :--- | :--- |
| **Batch Size** | 50 PDF Resumes |
| **Total Ingestion Time** | **2.41 seconds** |
| **Average Time per Resume** | **0.048 seconds (48.2 ms)** |
| **Throughput** | **20.76 resumes/second** |
| **Successful Processing Rate** | **98.0%** |
| **Duplicate Detection Rate** | **2.0%** (SHA-256 Verified) |
| **Failure Rate** | **0.0%** |

---

## 🛠 Technology Stack

- **Frontend**: Streamlit, Custom CSS (Dark Navy & Purple/Indigo design system), HTML5/SVG, Plotly.
- **Backend**: Python 3.11+, SQLAlchemy 2.0 (SQLite / PostgreSQL ready), Pydantic v2.
- **Document Processing**: PyMuPDF (`pymupdf`), ReportLab (synthetic generation).
- **AI & NLP**: Anthropic Claude API (`anthropic` Python SDK), Scikit-learn (TF-IDF & Cosine Similarity), Hybrid Deterministic Mock Engine.
- **Testing & Quality**: pytest, Ruff.

---

## 📦 Quickstart & Installation

### 1. Clone & Set Up Virtual Environment
```bash
git clone https://github.com/Chanchali11/FSI-Grand-Project.git
cd FSI-Grand-Project
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate # Linux/macOS
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Configure your environment variables:
```ini
ANTHROPIC_API_KEY=your_anthropic_api_key_here
CLAUDE_MODEL=claude-3-5-sonnet-20241022
USE_MOCK_AI=false  # Set to true to run in deterministic offline mode
DATABASE_URL=sqlite:///data/database/hiresphere.db
MAX_WORKERS=6
```

### 4. Generate Synthetic Resumes (Optional)
Generate 105 realistic synthetic resumes for benchmarking:
```bash
python data/synthetic_generator.py
```

### 5. Launch the Application
```bash
streamlit run app.py
```
Open your browser to `http://localhost:8501`.

---

## 🧪 Running Automated Tests

Run the full pytest suite:
```bash
pytest tests -v
```

Run the bulk benchmark:
```bash
python scripts/benchmark_bulk.py
```

---

## 🔒 Privacy & Compliance

- **GDPR Article 17 Compliant**: Recruiters or candidates can trigger instantaneous, permanent erasure of resumes, transcripts, and evaluation data.
- **Audit Trails**: Security audit records track every decision, interview creation, and deletion event without logging full resume contents.
- **Unbiased Scoring**: AI scoring is strictly restricted to verified skills, experience, and candidate responses.

---

## 📄 License
MIT License.