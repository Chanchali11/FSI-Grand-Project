from config import SYNTHETIC_DIR
from src.resume.pdf_parser import PDFParser


def test_pdf_parser_on_synthetic_pdf():
    resume_files = list((SYNTHETIC_DIR / "resumes").glob("*.pdf"))
    assert len(resume_files) > 0, "Synthetic resumes should exist"

    first_pdf = str(resume_files[0])
    res = PDFParser.extract_text_from_file(first_pdf)

    assert res["success"] is True
    assert res["page_count"] >= 1
    assert len(res["text"]) > 100
    assert "PROFESSIONAL EXPERIENCE" in res["text"] or "EXPERIENCE" in res["text"]


def test_pdf_parser_corrupted_and_empty():
    # Empty bytes
    res_empty = PDFParser.extract_text_from_bytes(b"", "empty.pdf")
    assert res_empty["success"] is False
    assert res_empty["is_corrupt"] is True

    # Random corrupt bytes
    res_corrupt = PDFParser.extract_text_from_bytes(b"NOT_A_VALID_PDF_HEADER_12345", "corrupt.pdf")
    assert res_corrupt["success"] is False
    assert res_corrupt["is_corrupt"] is True
