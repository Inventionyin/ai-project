from __future__ import annotations

import csv
import io
import json
import uuid
from dataclasses import dataclass

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.schemas.testcase import TestCaseCreateRequest
from app.schemas.testcase_import import TestCaseImportData, TestCaseImportErrorItem
from app.services.testcase import create_testcase

_MAX_IMPORT_FILE_SIZE = 10 * 1024 * 1024


@dataclass(frozen=True)
class _RowPayload:
    row_number: int
    test_case_id: str | None
    payload: TestCaseCreateRequest


def _normalize_header(value: str) -> str:
    return str(value or "").strip().lstrip("\ufeff").lower()


def _normalize_cell(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _parse_json_dict(value: str, *, field: str, row_number: int, errors: list[TestCaseImportErrorItem]) -> dict | None:
    text = (value or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        errors.append(
            TestCaseImportErrorItem(
                rowNumber=row_number,
                testCaseId=None,
                field=field,
                message=f"{field} 不是合法 JSON",
            )
        )
        return None
    if not isinstance(parsed, dict):
        errors.append(
            TestCaseImportErrorItem(
                rowNumber=row_number,
                testCaseId=None,
                field=field,
                message=f"{field} 必须是 JSON 对象",
            )
        )
        return None
    return parsed


def _parse_tags(value: str) -> list[str]:
    text = (value or "").strip()
    if not text:
        return []
    items = [s.strip() for s in text.split(",")]
    return [s for s in items if s]


def _parse_csv_rows(file_bytes: bytes) -> list[dict[str, str]]:
    text = file_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []
    normalized_fieldnames = [_normalize_header(name) for name in reader.fieldnames]
    reader.fieldnames = normalized_fieldnames
    rows: list[dict[str, str]] = []
    for row in reader:
        normalized_row: dict[str, str] = {}
        for key, value in row.items():
            normalized_row[_normalize_header(key)] = _normalize_cell(value)
        if not any(v for v in normalized_row.values()):
            continue
        rows.append(normalized_row)
    return rows


def _parse_xlsx_rows(file_bytes: bytes) -> list[dict[str, str]]:
    try:
        import openpyxl
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"XLSX 解析依赖缺失：{e}") from e

    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.worksheets[0] if wb.worksheets else None
    if ws is None:
        return []

    rows_iter = ws.iter_rows(values_only=True)
    try:
        header_row = next(rows_iter)
    except StopIteration:
        return []
    headers = [_normalize_header(c) for c in header_row]
    if not any(headers):
        return []

    rows: list[dict[str, str]] = []
    for r in rows_iter:
        row_dict: dict[str, str] = {}
        for idx, key in enumerate(headers):
            if not key:
                continue
            value = r[idx] if idx < len(r) else None
            row_dict[key] = _normalize_cell(value)
        if not any(v for v in row_dict.values()):
            continue
        rows.append(row_dict)
    return rows


def _build_row_payloads(
    *,
    project_id: str,
    rows: list[dict[str, str]],
    mode: str,
) -> tuple[list[_RowPayload], list[TestCaseImportErrorItem]]:
    errors: list[TestCaseImportErrorItem] = []
    payloads: list[_RowPayload] = []

    for idx, row in enumerate(rows, start=2):
        test_case_id = row.get("test_case_id") or row.get("testcaseid") or row.get("test_caseid") or row.get("testcase_id")
        test_case_id = (test_case_id or "").strip() or None

        api_headers_text = row.get("apiheaders", "")
        api_params_text = row.get("apiparams", "")
        pre_text = row.get("preconditions", "")
        post_text = row.get("postconditions", "")

        api_headers = _parse_json_dict(api_headers_text, field="apiHeaders", row_number=idx, errors=errors)
        if api_headers is None:
            continue
        api_params = _parse_json_dict(api_params_text, field="apiParams", row_number=idx, errors=errors)
        if api_params is None:
            continue
        pre_obj = _parse_json_dict(pre_text, field="preconditions", row_number=idx, errors=errors)
        if pre_obj is None:
            continue
        post_obj = _parse_json_dict(post_text, field="postconditions", row_number=idx, errors=errors)
        if post_obj is None:
            continue

        expected_status_code: int | None = None
        esc = row.get("expected_status_code") or row.get("expectedstatuscode") or row.get("expected_statuscode")
        if esc is not None and str(esc).strip() != "":
            try:
                expected_status_code = int(str(esc).strip())
            except Exception:
                errors.append(
                    TestCaseImportErrorItem(
                        rowNumber=idx,
                        testCaseId=test_case_id,
                        field="expected_status_code",
                        message="expected_status_code 必须是整数",
                    )
                )
                continue

        payload_dict: dict = {
            "projectId": project_id,
            "testCaseId": test_case_id,
            "feature": (row.get("feature") or "").strip(),
            "title": (row.get("title") or "").strip(),
            "type": (row.get("type") or "").strip().upper(),
            "priority": (row.get("priority") or "").strip().upper(),
            "status": (row.get("status") or "").strip().upper(),
            "apiMethod": (row.get("apimethod") or "").strip().upper(),
            "apiUrl": (row.get("apiurl") or "").strip(),
            "apiHeaders": api_headers,
            "apiParams": api_params,
            "expectedStatusCode": expected_status_code,
            "expectedResult": (row.get("expectedresult") or "").strip(),
            "preconditions": json.dumps(pre_obj, ensure_ascii=False) if pre_text.strip() else None,
            "postconditions": json.dumps(post_obj, ensure_ascii=False) if post_text.strip() else None,
            "tags": _parse_tags(row.get("tags", "")),
        }

        try:
            payload = TestCaseCreateRequest.model_validate(payload_dict)
        except ValidationError as e:
            first = e.errors()[0] if e.errors() else None
            field = None
            if first and isinstance(first.get("loc"), (list, tuple)) and first["loc"]:
                field = str(first["loc"][-1])
            message = first.get("msg") if isinstance(first, dict) else None
            errors.append(
                TestCaseImportErrorItem(
                    rowNumber=idx,
                    testCaseId=test_case_id,
                    field=field,
                    message=message or "行数据校验失败",
                )
            )
            continue

        payloads.append(_RowPayload(row_number=idx, test_case_id=test_case_id, payload=payload))

    if mode not in {"partial", "atomic"}:
        raise HTTPException(status_code=400, detail="mode 必须是 partial 或 atomic")

    return payloads, errors


async def import_testcases_from_file(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    filename: str,
    file_bytes: bytes,
    mode: str,
) -> TestCaseImportData:
    if file_bytes is None or len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="文件为空")
    if len(file_bytes) > _MAX_IMPORT_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件过大")

    name = (filename or "").strip()
    lower = name.lower()
    if lower.endswith(".csv"):
        rows = _parse_csv_rows(file_bytes)
    elif lower.endswith(".xlsx"):
        rows = _parse_xlsx_rows(file_bytes)
    else:
        raise HTTPException(status_code=400, detail="仅支持 CSV/XLSX 文件")

    if not rows:
        raise HTTPException(status_code=400, detail="未读取到有效数据行")

    payloads, build_errors = _build_row_payloads(project_id=str(project_id), rows=rows, mode=mode)
    if mode == "atomic" and build_errors:
        return TestCaseImportData(importedCount=0, failedCount=len(build_errors), errors=build_errors[:200])

    imported = 0
    errors: list[TestCaseImportErrorItem] = list(build_errors)

    if mode == "atomic":
        for row_payload in payloads:
            try:
                await create_testcase(db, user=user, payload=row_payload.payload)
            except HTTPException as e:
                await db.rollback()
                return TestCaseImportData(
                    importedCount=0,
                    failedCount=1,
                    errors=[
                        TestCaseImportErrorItem(
                            rowNumber=row_payload.row_number,
                            testCaseId=row_payload.test_case_id,
                            field=None,
                            message=str(e.detail),
                        )
                    ],
                )
            except Exception:
                await db.rollback()
                return TestCaseImportData(
                    importedCount=0,
                    failedCount=1,
                    errors=[
                        TestCaseImportErrorItem(
                            rowNumber=row_payload.row_number,
                            testCaseId=row_payload.test_case_id,
                            field=None,
                            message="导入失败",
                        )
                    ],
                )

        return TestCaseImportData(importedCount=len(payloads), failedCount=0, errors=[])

    for row_payload in payloads:
        try:
            async with db.begin_nested():
                await create_testcase(db, user=user, payload=row_payload.payload)
            imported += 1
        except HTTPException as e:
            errors.append(
                TestCaseImportErrorItem(
                    rowNumber=row_payload.row_number,
                    testCaseId=row_payload.test_case_id,
                    field=None,
                    message=str(e.detail),
                )
            )
        except Exception:
            errors.append(
                TestCaseImportErrorItem(
                    rowNumber=row_payload.row_number,
                    testCaseId=row_payload.test_case_id,
                    field=None,
                    message="导入失败",
                )
            )

    return TestCaseImportData(importedCount=imported, failedCount=len(errors), errors=errors[:200])
