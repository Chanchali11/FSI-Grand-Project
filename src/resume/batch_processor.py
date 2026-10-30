import logging
import os
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from config import UPLOAD_DIR, settings
from src.database.models import ProcessingStatus, ResumeDocument
from src.database.repository import get_db_session
from src.resume.pdf_parser import PDFParser
from src.resume.screening_engine import ScreeningEngine
from src.security.authentication import calculate_file_sha256

logger = logging.getLogger(__name__)


class BatchProgressTracker:
    """Thread-safe batch progress statistics tracker."""

    def __init__(self, total_files: int):
        self.total = total_files
        self.processed = 0
        self.successful = 0
        self.failed = 0
        self.duplicates = 0
        self.start_time = time.time()
        self.errors: list[dict[str, str]] = []

    def update(self, success: bool, is_duplicate: bool = False, filename: str = "", error: str = ""):
        self.processed += 1
        if is_duplicate:
            self.duplicates += 1
        elif success:
            self.successful += 1
        else:
            self.failed += 1
            if error:
                self.errors.append({"filename": filename, "error": error})

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time

    @property
    def throughput_per_second(self) -> float:
        if self.elapsed_seconds <= 0:
            return 0.0
        return round(self.processed / self.elapsed_seconds, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "processed": self.processed,
            "successful": self.successful,
            "failed": self.failed,
            "duplicates": self.duplicates,
            "percent": round((self.processed / max(self.total, 1)) * 100, 1),
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "throughput": self.throughput_per_second,
            "errors": self.errors,
        }


class BatchResumeProcessor:
    """Bounded-concurrency bulk resume processor for high-volume recruitment."""

    def __init__(self, max_workers: int = 6):
        self.max_workers = max_workers
        self.screening_engine = ScreeningEngine()

    def process_single_upload(
        self,
        campaign_id: str,
        job_id: str,
        filename: str,
        file_bytes: bytes,
    ) -> dict[str, Any]:
        """Process one resume: validate, deduplicate, parse, and screen in an isolated DB transaction."""
        result = {
            "filename": filename,
            "success": False,
            "is_duplicate": False,
            "resume_id": None,
            "candidate_name": None,
            "score": None,
            "status": ProcessingStatus.FAILED.value,
            "error": None,
        }

        # 1. Basic validation
        if not filename.lower().endswith(".pdf"):
            result["error"] = "Unsupported file type. Only PDF files are accepted."
            return result

        if len(file_bytes) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            result["error"] = f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB}MB."
            return result

        file_hash = calculate_file_sha256(file_bytes)

        with get_db_session() as session:
            # Check for duplicate in this campaign
            existing_doc = (
                session.query(ResumeDocument)
                .filter(
                    ResumeDocument.campaign_id == campaign_id,
                    ResumeDocument.sha256_hash == file_hash,
                )
                .first()
            )

            if existing_doc:
                result["is_duplicate"] = True
                result["resume_id"] = existing_doc.id
                result["status"] = ProcessingStatus.DUPLICATE.value
                result["error"] = f"Duplicate document detected (matches resume ID: {existing_doc.id[:8]})."
                return result

            # 2. Extract PDF Text & Assess Document Health
            parsed_doc = PDFParser.extract_text_from_bytes(file_bytes, filename=filename)

            # Save file to disk
            campaign_dir = UPLOAD_DIR / campaign_id
            campaign_dir.mkdir(parents=True, exist_ok=True)
            safe_name = f"{file_hash[:16]}_{os.path.basename(filename)}"
            storage_path = str(campaign_dir / safe_name)
            try:
                with open(storage_path, "wb") as f:
                    f.write(file_bytes)
            except Exception:
                storage_path = "memory://temp"

            resume_doc = ResumeDocument(
                campaign_id=campaign_id,
                job_id=job_id,
                original_filename=filename,
                storage_path=storage_path,
                file_size_bytes=len(file_bytes),
                sha256_hash=file_hash,
                page_count=parsed_doc.get("page_count", 1),
                is_scanned=parsed_doc.get("is_scanned", False),
                is_encrypted=parsed_doc.get("is_encrypted", False),
                is_corrupt=parsed_doc.get("is_corrupt", False),
                is_duplicate=False,
                raw_text=parsed_doc.get("text", ""),
                processing_status=ProcessingStatus.QUEUED.value,
            )

            if not parsed_doc["success"]:
                resume_doc.processing_status = ProcessingStatus.FAILED.value
                resume_doc.error_message = parsed_doc.get("error", "Failed to extract text.")
                session.add(resume_doc)
                session.commit()
                result["error"] = resume_doc.error_message
                return result

            session.add(resume_doc)
            session.flush()

            # 3. Perform Parsing & Screening
            try:
                screening = self.screening_engine.process_and_screen_resume(session, resume_doc.id)
                session.commit()

                result["success"] = True
                result["resume_id"] = resume_doc.id
                result["status"] = resume_doc.processing_status
                if screening:
                    result["score"] = screening.overall_score
                    if resume_doc.candidate:
                        result["candidate_name"] = resume_doc.candidate.name
            except Exception as e:
                session.rollback()
                logger.error(f"Error screening resume {filename}: {e}")
                with get_db_session() as s2:
                    doc = s2.query(ResumeDocument).filter(ResumeDocument.id == resume_doc.id).first()
                    if doc:
                        doc.processing_status = ProcessingStatus.FAILED.value
                        doc.error_message = f"Screening error: {e!s}"
                        s2.commit()
                result["error"] = str(e)

        return result

    def process_batch(
        self,
        campaign_id: str,
        job_id: str,
        files_data: list[tuple[str, bytes]],
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """
        Process a list of (filename, bytes) using bounded thread pool.
        Executes progress_callback after each file completion.
        """
        tracker = BatchProgressTracker(len(files_data))
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {
                executor.submit(self.process_single_upload, campaign_id, job_id, fname, fbytes): fname
                for fname, fbytes in files_data
            }

            for future in as_completed(future_to_file):
                filename = future_to_file[future]
                try:
                    res = future.result()
                    tracker.update(
                        success=res["success"],
                        is_duplicate=res.get("is_duplicate", False),
                        filename=filename,
                        error=res.get("error") or "",
                    )
                    results.append(res)
                except Exception as exc:
                    tracker.update(success=False, filename=filename, error=str(exc))
                    results.append({"filename": filename, "success": False, "error": str(exc)})

                if progress_callback:
                    progress_callback(tracker.to_dict())

        return {
            "summary": tracker.to_dict(),
            "results": results,
        }

    def retry_failed_resumes(self, campaign_id: str, job_id: str) -> dict[str, Any]:
        """Retry processing all failed resumes in a campaign/job."""
        files_to_retry = []
        with get_db_session() as session:
            failed_docs = (
                session.query(ResumeDocument)
                .filter(
                    ResumeDocument.campaign_id == campaign_id,
                    ResumeDocument.job_id == job_id,
                    ResumeDocument.processing_status == ProcessingStatus.FAILED.value,
                )
                .all()
            )
            for doc in failed_docs:
                if doc.storage_path and os.path.exists(doc.storage_path):
                    with open(doc.storage_path, "rb") as f:
                        files_to_retry.append((doc.original_filename, f.read()))

        if not files_to_retry:
            return {"message": "No failed resumes available for retry.", "count": 0}

        return self.process_batch(campaign_id, job_id, files_to_retry)
