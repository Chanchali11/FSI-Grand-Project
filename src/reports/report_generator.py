import io
from datetime import datetime
from typing import Any

import pandas as pd

from src.database.models import (
    CandidateProfile,
    InterviewSession,
    Job,
    ScreeningResult,
)


class ReportGenerator:
    """Generates candidate feedback reports, executive PDFs/HTML, and CSV/Excel exports."""

    @staticmethod
    def generate_candidate_html_report(
        candidate: CandidateProfile,
        job: Job,
        screening: ScreeningResult | None,
        technical_session: InterviewSession | None,
        hr_session: InterviewSession | None = None,
    ) -> str:
        """Construct a printable, beautifully formatted HTML evaluation dossier."""
        company_name = job.campaign.company.name if job and job.campaign and job.campaign.company else "Company"
        screening_score = f"{screening.overall_score:.1f}/100" if screening else "N/A"
        tech_score = f"{technical_session.overall_interview_score:.1f}/100" if technical_session and technical_session.overall_interview_score else "N/A"
        hr_score = f"{hr_session.overall_interview_score:.1f}/100" if hr_session and hr_session.overall_interview_score else "N/A"

        matched_skills_html = "".join(f"<span class='badge'>{s}</span>" for s in (screening.matched_skills if screening else []))
        missing_skills_html = "".join(f"<span class='badge badge-missing'>{s}</span>" for s in (screening.missing_skills if screening else []))

        evidence_rows = ""
        if screening and screening.evidence_excerpts:
            for skill, excerpt in screening.evidence_excerpts.items():
                evidence_rows += f"""
                <tr>
                  <td><strong>{skill}</strong></td>
                  <td><em>"{excerpt}"</em></td>
                </tr>
                """

        # Technical questions breakdown
        tech_q_html = ""
        if technical_session and technical_session.questions:
            for q in technical_session.questions:
                tech_q_html += f"""
                <div class="q-box">
                  <div class="q-header">Q{q.question_order} ({q.category}): {q.question_text}</div>
                  <div class="q-answer"><strong>Candidate Answer:</strong> {q.candidate_answer or 'No answer submitted'}</div>
                  <div class="q-score">Score: {q.score or 0.0:.1f} / 100 &nbsp;|&nbsp; <em>{q.evaluation_feedback or ''}</em></div>
                </div>
                """

        # HR questions breakdown
        hr_q_html = ""
        if hr_session and hr_session.questions:
            for q in hr_session.questions:
                hr_q_html += f"""
                <div class="q-box">
                  <div class="q-header">Q{q.question_order} ({q.category}): {q.question_text}</div>
                  <div class="q-answer"><strong>Candidate Answer:</strong> {q.candidate_answer or 'No answer submitted'}</div>
                  <div class="q-score">Score: {q.score or 0.0:.1f} / 100 &nbsp;|&nbsp; <em>{q.evaluation_feedback or ''}</em></div>
                </div>
                """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <title>Hirexp Ai Candidate Dossier - {candidate.name}</title>
          <style>
            body {{ font-family: 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #1e293b; margin: 40px; background: #fff; }}
            .header {{ border-bottom: 3px solid #6366f1; padding-bottom: 20px; margin-bottom: 25px; }}
            h1 {{ color: #1e1b4b; margin: 0 0 6px 0; font-size: 26px; }}
            .subtitle {{ color: #64748b; font-size: 14px; text-transform: uppercase; letter-spacing: 0.05em; }}
            .summary-cards {{ display: flex; gap: 20px; margin-bottom: 25px; }}
            .card {{ flex: 1; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; background: #f8fafc; text-align: center; }}
            .card-val {{ font-size: 26px; font-weight: bold; color: #4338ca; }}
            .card-lbl {{ font-size: 12px; color: #64748b; text-transform: uppercase; margin-top: 4px; }}
            .badge {{ display: inline-block; background: #e0e7ff; color: #3730a3; padding: 4px 10px; border-radius: 9999px; font-size: 12px; margin: 2px 4px 2px 0; }}
            .badge-missing {{ background: #fee2e2; color: #991b1b; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }}
            th, td {{ border: 1px solid #cbd5e1; padding: 10px; text-align: left; }}
            th {{ background: #f1f5f9; }}
            .section {{ margin-top: 30px; }}
            .section-title {{ font-size: 18px; color: #0f172a; border-left: 4px solid #6366f1; padding-left: 10px; margin-bottom: 12px; }}
            .q-box {{ border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px; margin-bottom: 12px; background: #fafafa; }}
            .q-header {{ font-weight: bold; color: #1e293b; margin-bottom: 6px; }}
            .q-answer {{ color: #334155; margin-bottom: 6px; font-size: 13px; }}
            .q-score {{ font-size: 12px; color: #4338ca; font-weight: 600; }}
            .footer {{ margin-top: 40px; border-top: 1px solid #e2e8f0; padding-top: 15px; font-size: 11px; color: #94a3b8; text-align: center; }}
          </style>
        </head>
        <body>
          <div class="header">
            <h1>Candidate Evaluation Dossier: {candidate.name}</h1>
            <div class="subtitle">{job.title} &bull; {company_name} &bull; Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</div>
          </div>

          <div class="summary-cards">
            <div class="card">
              <div class="card-val">{screening_score}</div>
              <div class="card-lbl">Resume Screening Score</div>
            </div>
            <div class="card">
              <div class="card-val">{tech_score}</div>
              <div class="card-lbl">Technical Interview</div>
            </div>
            <div class="card">
              <div class="card-val">{hr_score}</div>
              <div class="card-lbl">HR / Cultural Interview</div>
            </div>
            <div class="card">
              <div class="card-val">{screening.recruiter_decision if screening else 'Pending'}</div>
              <div class="card-lbl">Hiring Decision</div>
            </div>
          </div>

          <div class="section">
            <div class="section-title">Candidate Profile & Contact</div>
            <p><strong>Email:</strong> {candidate.email or 'N/A'} &nbsp;|&nbsp; <strong>Phone:</strong> {candidate.phone or 'N/A'} &nbsp;|&nbsp; <strong>Experience:</strong> {candidate.years_experience:.1f} years</p>
          </div>

          <div class="section">
            <div class="section-title">Screening Competency & Evidence Verification</div>
            <p><strong>Matched Skills:</strong> {matched_skills_html or 'None identified'}</p>
            <p><strong>Missing Skills:</strong> {missing_skills_html or 'None'}</p>
            <table>
              <thead>
                <tr>
                  <th style="width: 25%;">Skill / Requirement</th>
                  <th>Extracted Resume Evidence Snippet</th>
                </tr>
              </thead>
              <tbody>
                {evidence_rows or '<tr><td colspan="2">No detailed excerpts available.</td></tr>'}
              </tbody>
            </table>
          </div>

          <div class="section">
            <div class="section-title">Technical Interview Questions & Rubric Scoring</div>
            {tech_q_html or '<p>No technical interview session recorded yet.</p>'}
          </div>

          <div class="section">
            <div class="section-title">HR & Behavioral Interview Evaluation (STAR Rubric)</div>
            {hr_q_html or '<p>No HR interview session recorded yet.</p>'}
          </div>

          <div class="footer">
            Hirexp Ai &bull; Evidence-Based Hiring &bull; Unbiased, Protected Characteristic-Free Evaluation
          </div>
        </body>
        </html>
        """
        return html

    @staticmethod
    def export_candidates_to_dataframe(candidate_data: list[dict[str, Any]]) -> pd.DataFrame:
        """Converts raw candidate screening rows into clean DataFrame for CSV/Excel export."""
        export_rows = []
        for c in candidate_data:
            export_rows.append({
                "Candidate ID": c.get("candidate_id"),
                "Candidate Name": c.get("candidate_name"),
                "Email": c.get("candidate_email"),
                "Phone": c.get("candidate_phone"),
                "Resume File": c.get("filename"),
                "Overall Score": c.get("overall_score"),
                "Keyword Coverage (%)": c.get("keyword_coverage"),
                "TF-IDF Similarity (%)": c.get("text_similarity"),
                "Experience Score": c.get("experience_score"),
                "Semantic Score": c.get("semantic_score"),
                "Mandatory Passed": c.get("mandatory_passed"),
                "Matched Skills": ", ".join(c.get("matched_skills", [])),
                "Missing Skills": ", ".join(c.get("missing_skills", [])),
                "Recommendation": c.get("recommendation"),
                "Recruiter Decision": c.get("recruiter_decision"),
                "Recruiter Notes": c.get("recruiter_notes"),
            })
        return pd.DataFrame(export_rows)

    @staticmethod
    def export_to_csv_bytes(df: pd.DataFrame) -> bytes:
        return df.to_csv(index=False).encode("utf-8")

    @staticmethod
    def export_to_excel_bytes(df: pd.DataFrame) -> bytes:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl" if "openpyxl" in globals() else None) as writer:
            df.to_excel(writer, index=False, sheet_name="Screening Results")
        return output.getvalue()
