#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _wire_backend_imports() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    backend_root = repo_root / "ai-project-back-end"
    sys.path.insert(0, str(backend_root))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--doc", required=True, help="接口文档路径")
    parser.add_argument("--output", default="test_cases", help="输出目录")
    parser.add_argument("--case-gen-mode", default="AUTO", help="OFF/SUGGEST/AUTO")
    parser.add_argument("--llm-mode", default="OFF", help="OFF/SUGGEST/AUTO")
    parser.add_argument("--skill-id", default="api-doc-test-generator", help="skillId")
    parser.add_argument("--max-cases", default="200", help="最大用例数")
    parser.add_argument("--instruction", default="", help="生成指令/过滤关键词")
    args = parser.parse_args()

    _wire_backend_imports()
    from app.services.doc_ingest.case_generator import generate_testcase_rows, rows_to_csv_dicts
    from app.services.doc_ingest.csv_builder import build_csv_from_doc_parse, build_csv_from_rows
    from app.services.doc_ingest.llm_enhancer import apply_llm_enhancement
    from app.services.doc_ingest.parse_with_docling import parse_document

    doc_path = Path(args.doc)
    content = doc_path.read_bytes()
    result = parse_document(content, doc_path.name)
    result = apply_llm_enhancement(result, args.llm_mode)

    rows = generate_testcase_rows(
        result=result,
        instruction=str(args.instruction or "").strip(),
        skill_id=str(args.skill_id or "api-doc-test-generator").strip() or "api-doc-test-generator",
        max_cases=max(1, min(2000, int(args.max_cases))),
        mode=str(args.case_gen_mode or "OFF"),
    )

    if rows:
        fname, csv_text, _ = build_csv_from_rows(rows_to_csv_dicts(rows), fname_prefix="api_test_cases")
    else:
        fname, csv_text, _ = build_csv_from_doc_parse(result)

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / fname
    out_path.write_text(csv_text, encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
