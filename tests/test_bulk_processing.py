import time

from config import SYNTHETIC_DIR
from src.database.repository import get_db_session, init_db
from src.recruitment.campaign_service import CampaignService
from src.resume.batch_processor import BatchResumeProcessor


def test_batch_resume_processing_and_deduplication():
    init_db()
    with get_db_session() as session:
        camp = CampaignService.create_campaign(
            session=session,
            company_name="Batch Benchmark Corp",
            campaign_title="Bulk Ingestion Benchmark",
            target_hires=10,
        )
        job = CampaignService.create_job(
            session=session,
            campaign_id=camp.id,
            title="Senior Backend Scale Engineer",
            description="Python, Docker, FastAPI, PostgreSQL",
            required_skills=["Python", "Docker", "FastAPI"],
            min_years_experience=3.0,
        )
        camp_id = camp.id
        job_id = job.id

    # Grab 10 synthetic files including duplicates
    resume_files = list((SYNTHETIC_DIR / "resumes").glob("*.pdf"))[:10]
    assert len(resume_files) >= 5

    files_data = []
    for f in resume_files:
        with open(f, "rb") as fp:
            files_data.append((f.name, fp.read()))

    processor = BatchResumeProcessor(max_workers=4)

    t0 = time.time()
    batch_res = processor.process_batch(camp_id, job_id, files_data)
    elapsed = time.time() - t0
    assert elapsed >= 0.0


    summary = batch_res["summary"]
    assert summary["total"] == len(files_data)
    assert summary["processed"] == len(files_data)
    assert summary["successful"] > 0
    assert summary["throughput"] > 0.0

    # Test Re-uploading exact same files to verify SHA-256 duplicate detection
    dup_res = processor.process_batch(camp_id, job_id, files_data)
    dup_summary = dup_res["summary"]
    assert dup_summary["duplicates"] == len(files_data)
