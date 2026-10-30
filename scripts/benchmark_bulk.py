import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import SYNTHETIC_DIR
from src.database.repository import get_db_session, init_db
from src.recruitment.campaign_service import CampaignService
from src.resume.batch_processor import BatchResumeProcessor


def run_benchmark(batch_size: int = 50, worker_count: int = 6):
    init_db()
    with get_db_session() as session:
        camp = CampaignService.create_campaign(
            session=session,
            company_name="Benchmark Enterprise",
            campaign_title=f"Benchmark Run (Workers={worker_count})",
            target_hires=15,
        )
        job = CampaignService.create_job(
            session=session,
            campaign_id=camp.id,
            title="Senior Benchmark Engineer",
            description="Python, FastAPI, Docker, Microservices, PostgreSQL, Kafka, Redis",
            required_skills=["Python", "FastAPI", "Docker", "PostgreSQL"],
            preferred_skills=["Kafka", "Redis"],
            mandatory_qualifications=["3+ years experience"],
            min_years_experience=3.0,
        )
        camp_id = camp.id
        job_id = job.id

    resume_files = list((SYNTHETIC_DIR / "resumes").glob("*.pdf"))[:batch_size]
    print("============================================================")
    print("       HIRESPHERE AI BULK PROCESSING BENCHMARK")
    print("============================================================")
    print(f"Batch Size: {len(resume_files)} resumes")
    print(f"Worker Concurrency: {worker_count} threads")
    print("Document Format: Native PyMuPDF Text Layer Extraction")

    files_data = []
    for f in resume_files:
        with open(f, "rb") as fp:
            files_data.append((f.name, fp.read()))

    processor = BatchResumeProcessor(max_workers=worker_count)

    t_start = time.time()
    batch_res = processor.process_batch(camp_id, job_id, files_data)
    total_time = time.time() - t_start

    summary = batch_res["summary"]
    avg_per_resume = total_time / max(len(resume_files), 1)

    print("\n--- BENCHMARK RESULTS ---")
    print(f"Total Time:                  {total_time:.2f} seconds")
    print(f"Average Time per Resume:     {avg_per_resume:.3f} seconds ({avg_per_resume*1000:.1f} ms)")
    print(f"Throughput:                  {summary['throughput']:.2f} resumes/second")
    print(f"Successfully Processed:      {summary['successful']} ({summary['successful']/len(resume_files)*100:.1f}%)")
    print(f"Duplicates Detected:         {summary['duplicates']} ({summary['duplicates']/len(resume_files)*100:.1f}%)")
    print(f"Failed Resumes:              {summary['failed']} ({summary['failed']/len(resume_files)*100:.1f}%)")
    print("============================================================\n")

    return summary


if __name__ == "__main__":
    run_benchmark(batch_size=50, worker_count=6)
