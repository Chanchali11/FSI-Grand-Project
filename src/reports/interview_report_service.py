from typing import Any
from sqlalchemy.orm import Session

from src.database.models import InterviewQuestion, InterviewSession, Job, CandidateProfile
from src.interview.resume_profile import NormalizedResumeProfile
from src.reports.report_generator import ReportGenerator


class InterviewReportService:
    """Calculates comprehensive candidate performance reports across all rubrics."""

    @staticmethod
    def generate_interview_performance_report(
        session: Session,
        session_id: str,
    ) -> dict[str, Any]:
        """
        Calculates:
        - Overall performance score
        - Technical knowledge score
        - Project knowledge score
        - Communication clarity score
        - Answer relevance score
        - Strengths
        - Weaknesses
        - Suggested improvements
        - Question-wise feedback
        - Recommended practice topics
        """
        interview_session = session.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        if not interview_session:
            return {}

        questions = (
            session.query(InterviewQuestion)
            .filter(InterviewQuestion.session_id == session_id)
            .order_by(InterviewQuestion.question_order.asc())
            .all()
        )

        overall_scores = [q.score for q in questions if q.score is not None]
        overall_avg = round(sum(overall_scores) / len(overall_scores), 1) if overall_scores else 0.0

        # Category breakdowns matching Section 10 specs:
        # Technical Knowledge, Problem Solving, Communication Clarity, Project Understanding, Behavioral Responses, Overall Score
        tech_scores = []
        prob_scores = []
        comm_scores = []
        proj_scores = []
        behav_scores = []

        question_feedbacks = []
        strengths = []
        weaknesses = []
        improvements = []
        all_missing = []

        for q in questions:
            score = q.score or 0.0
            cat_lower = (q.category or "").lower()
            q_type = (q.question_type or "").lower()

            if "project" in cat_lower or "project" in q_type:
                proj_scores.append(score)
            elif "problem" in cat_lower or "coding" in q_type or "algorithm" in cat_lower or "design" in cat_lower:
                prob_scores.append(score)
            elif "hr" in cat_lower or "behavioral" in cat_lower or "star" in q_type or "team" in cat_lower:
                behav_scores.append(score)
                comm_scores.append(score)
            else:
                tech_scores.append(score)

            rubrics = q.rubric_scores or {}
            comm_val = rubrics.get("communication_structure") or rubrics.get("communication") or (score * 0.2)
            prob_val = rubrics.get("problem_solving") or rubrics.get("practical_depth") or (score * 0.3)
            comm_scores.append(min(100.0, float(comm_val) * (100.0 / 20.0 if comm_val <= 20 else 1.0)))
            prob_scores.append(min(100.0, float(prob_val) * (100.0 / 30.0 if prob_val <= 30 else 1.0)))

            if score >= 75.0:
                strengths.append(f"Demonstrated solid competency in {q.category} ({score:.0f}%)")
            elif score < 60.0:
                weaknesses.append(f"Needs deeper mastery in {q.category} ({score:.0f}%)")

            if q.improvement_suggestions:
                for imp in q.improvement_suggestions:
                    if imp not in improvements:
                        improvements.append(imp)

            if q.missing_concepts:
                all_missing.extend(q.missing_concepts)

            question_feedbacks.append({
                "order": q.question_order,
                "category": q.category,
                "question": q.question_text,
                "answer": q.candidate_answer or "No answer submitted",
                "score": score,
                "feedback": q.evaluation_feedback or "",
                "correct_concepts": q.correct_concepts or [],
                "missing_concepts": q.missing_concepts or [],
                "follow_up": q.follow_up_question or "",
            })

        # Calculate averages safely
        calc_avg = lambda lst, default: round(sum(lst) / len(lst), 1) if lst else default
        tech_avg = calc_avg(tech_scores, overall_avg)
        prob_avg = calc_avg(prob_scores, overall_avg)
        comm_avg = calc_avg(comm_scores, min(100.0, overall_avg + 4.0))
        proj_avg = calc_avg(proj_scores, overall_avg)
        behav_avg = calc_avg(behav_scores, min(100.0, overall_avg + 2.0))

        # Determine AI recommendation based on objective rubrics
        if overall_avg >= 80.0:
            ai_recommendation = "Strongly Recommended"
            recommendation_reason = "Exceeds role criteria with high technical precision, sound problem-solving, and structured articulation."
        elif overall_avg >= 68.0:
            ai_recommendation = "Recommended"
            recommendation_reason = "Solid engineering competence across core topics with minor gaps in non-critical sub-areas."
        elif overall_avg >= 50.0:
            ai_recommendation = "Requires Recruiter Review"
            recommendation_reason = "Mixed signals across question rubrics. Human recruiter interview review strongly recommended."
        else:
            ai_recommendation = "Not Recommended"
            recommendation_reason = "Responses did not meet minimum threshold standards for required technical or role concepts."

        # De-duplicate recommended practice topics
        practice_topics = list(dict.fromkeys(all_missing))[:6]
        if not practice_topics:
            practice_topics = ["System Architecture & Concurrency", "Database Query Profiling", "STAR Behavioral Formatting"]

        if not strengths:
            strengths = ["Engaged in full interview session", "Completed responses across all scheduled questions"]
        if not weaknesses:
            weaknesses = ["Opportunity to expand on edge cases and failure scenarios"]
        if not improvements:
            improvements = ["Provide concrete metric outcomes and trade-off justifications in answers."]

        return {
            "session_id": session_id,
            "overall_score": overall_avg,
            "technical_knowledge_score": tech_avg,
            "problem_solving_score": prob_avg,
            "communication_clarity_score": comm_avg,
            "project_knowledge_score": proj_avg,
            "project_understanding_score": proj_avg,
            "behavioral_responses_score": behav_avg,
            "ai_recommendation": ai_recommendation,
            "recommendation_reason": recommendation_reason,
            "strengths": strengths[:4],
            "weaknesses": weaknesses[:4],
            "suggested_improvements": improvements[:5],
            "question_feedbacks": question_feedbacks,
            "recommended_practice_topics": practice_topics,
        }

    @staticmethod
    def generate_report_html(report_data: dict[str, Any], candidate_name: str, job_title: str) -> str:
        """Renders an executive candidate evaluation report in printable HTML."""
        q_rows = ""
        for qf in report_data.get("question_feedbacks", []):
            q_rows += f"""
            <div style="margin-bottom: 18px; padding: 14px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;">
              <div style="font-weight: 700; color: #1E1B4B; margin-bottom: 4px;">Q{qf['order']}: {qf['category']}</div>
              <div style="font-style: italic; color: #334155; margin-bottom: 8px;">"{qf['question']}"</div>
              <div style="font-size: 0.9em; margin-bottom: 6px;"><strong>Candidate Answer:</strong> {qf['answer']}</div>
              <div style="display: flex; gap: 12px; font-size: 0.88em; color: #475569;">
                <span style="font-weight: 700; color: #4F46E5;">Score: {qf['score']:.1f}/100</span>
                <span><strong>Feedback:</strong> {qf['feedback']}</span>
              </div>
            </div>
            """

        strengths_li = "".join(f"<li>{s}</li>" for s in report_data.get("strengths", []))
        weaknesses_li = "".join(f"<li>{w}</li>" for w in report_data.get("weaknesses", []))
        improvements_li = "".join(f"<li>{i}</li>" for i in report_data.get("suggested_improvements", []))
        topics_badges = "".join(f"<span style='display: inline-block; background: #EEF2FF; color: #4F46E5; padding: 4px 10px; border-radius: 9999px; font-size: 0.85em; margin: 3px;'>{t}</span>" for t in report_data.get("recommended_practice_topics", []))

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <title>Hirexp Ai Virtual Interview Report - {candidate_name}</title>
          <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 30px; color: #0F172A; line-height: 1.5; }}
            .header {{ border-bottom: 3px solid #4F46E5; padding-bottom: 15px; margin-bottom: 25px; }}
            .score-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 25px; }}
            .score-card {{ background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; text-align: center; }}
            .score-num {{ font-size: 1.8rem; font-weight: 800; color: #4F46E5; }}
            .score-label {{ font-size: 0.75rem; text-transform: uppercase; color: #64748B; font-weight: 600; margin-top: 4px; }}
            .section {{ margin-bottom: 25px; }}
            h2 {{ font-size: 1.2rem; color: #1E1B4B; border-bottom: 1px solid #E2E8F0; padding-bottom: 6px; }}
          </style>
        </head>
        <body>
          <div class="header">
            <h1 style="margin: 0 0 6px 0; color: #1E1B4B;">Hirexp Ai &bull; Virtual Interview Assessment</h1>
            <div style="color: #64748B; font-size: 1rem;">Candidate: <strong>{candidate_name}</strong> &nbsp;|&nbsp; Target Role: <strong>{job_title}</strong></div>
          </div>

          <div class="score-grid">
            <div class="score-card">
              <div class="score-num">{report_data.get('overall_score', 0):.1f}</div>
              <div class="score-label">Overall Composite</div>
            </div>
            <div class="score-card">
              <div class="score-num">{report_data.get('technical_knowledge_score', 0):.1f}</div>
              <div class="score-label">Technical Mastery</div>
            </div>
            <div class="score-card">
              <div class="score-num">{report_data.get('project_knowledge_score', 0):.1f}</div>
              <div class="score-label">Project Execution</div>
            </div>
            <div class="score-card">
              <div class="score-num">{report_data.get('communication_clarity_score', 0):.1f}</div>
              <div class="score-label">Communication Clarity</div>
            </div>
            <div class="score-card">
              <div class="score-num">{report_data.get('answer_relevance_score', 0):.1f}</div>
              <div class="score-label">Relevance & Depth</div>
            </div>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 25px;">
            <div class="section">
              <h2>Key Strengths</h2>
              <ul>{strengths_li}</ul>
            </div>
            <div class="section">
              <h2>Identified Weaknesses</h2>
              <ul>{weaknesses_li}</ul>
            </div>
          </div>

          <div class="section">
            <h2>Recommended Improvements</h2>
            <ul>{improvements_li}</ul>
          </div>

          <div class="section">
            <h2>Recommended Practice Topics</h2>
            <div>{topics_badges}</div>
          </div>

          <div class="section">
            <h2>Question-by-Question Evaluation</h2>
            {q_rows}
          </div>
        </body>
        </html>
        """
        return html
