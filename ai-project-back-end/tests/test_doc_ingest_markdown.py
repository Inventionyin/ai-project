from __future__ import annotations

from pathlib import Path

from app.services.doc_ingest.csv_builder import build_csv_from_doc_parse
from app.services.doc_ingest.parse_with_docling import parse_document
from app.services.testcase_import import _parse_csv_rows


def test_markdown_doc_ingest_generates_non_empty_csv_rows() -> None:
    root = Path(__file__).resolve().parents[2]
    doc = root / "docs" / "API.md"
    content = doc.read_bytes()
    result = parse_document(content, doc.name, job_id=None)
    assert len(result.apiCandidates) > 0

    _, csv_text, count = build_csv_from_doc_parse(result)
    assert count > 0
    rows = _parse_csv_rows(csv_text.encode("utf-8"))
    assert len(rows) == count
