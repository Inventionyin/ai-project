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


def _first_value(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(_normalize_header(key), "")
        if value.strip():
            return value.strip()
    return ""


def _truncate_text(value: str, max_length: int) -> str:
    text = (value or "").strip()
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"


def _safe_test_case_id(value: str, *, row_number: int) -> str:
    text = (value or "").strip()
    if not text:
        return f"TC_IMPORT_{row_number:05d}"
    return _truncate_text(text, 64)


def _looks_like_chinese_manual_case(row: dict[str, str]) -> bool:
    keys = set(row.keys())
    return bool({"用例标题", "测试步骤", "预期结果"} & keys) and bool({"模块", "需求名称", "场景类型"} & keys)


def _map_case_type(value: str) -> str:
    text = (value or "").strip().upper()
    if text in {"API", "UI", "PERF", "MIX"}:
        return text
    if any(word in text for word in ["性能", "并发", "压测", "PERF"]):
        return "PERF"
    if any(word in text for word in ["接口", "API"]):
        return "API"
    return "UI"


def _map_priority(value: str) -> str:
    text = (value or "").strip().upper()
    if text in {"P0", "P1", "P2", "P3"}:
        return text
    if text in {"高", "紧急", "最高", "CRITICAL"}:
        return "P0"
    if text in {"中", "重要", "HIGH"}:
        return "P1"
    if text in {"低", "一般", "MEDIUM"}:
        return "P2"
    return "P2"


def _map_status(value: str) -> str:
    text = (value or "").strip().upper()
    if text in {"DRAFT", "REVIEWED", "DEPRECATED"}:
        return text
    if text in {"已评审", "已通过", "已完成", "完成", "通过"}:
        return "REVIEWED"
    if text in {"废弃", "失效", "停用"}:
        return "DEPRECATED"
    return "DRAFT"


def _build_content_md_from_chinese_case(
    *,
    requirement_id: str,
    requirement_name: str,
    scenario_type: str,
    preconditions: str,
    steps: str,
    test_data: str,
    expected_result: str,
    remark: str,
) -> str:
    sections: list[str] = []
    if requirement_id or requirement_name:
        req = " / ".join(v for v in [requirement_id, requirement_name] if v)
        sections.append(f"### 关联需求\n{req}")
    if scenario_type:
        sections.append(f"### 场景类型\n{scenario_type}")
    if preconditions:
        sections.append(f"### 前置条件\n{preconditions}")
    if steps:
        sections.append(f"### 测试步骤\n{steps}")
    if test_data:
        sections.append(f"### 测试数据\n{test_data}")
    if expected_result:
        sections.append(f"### 预期结果\n{expected_result}")
    if remark:
        sections.append(f"### 备注\n{remark}")
    return "\n\n".join(sections)


def _build_chinese_manual_payload_dict(*, project_id: str, row: dict[str, str], row_number: int) -> dict:
    requirement_id = _first_value(row, "需求ID", "需求编号", "req_id", "requirement_id")
    requirement_name = _first_value(row, "需求名称", "需求标题", "requirement_name")
    feature = _truncate_text(_first_value(row, "模块", "所属模块", "功能模块") or requirement_name or "未分组", 128)
    scenario_type = _first_value(row, "场景类型", "用例类型", "测试类型", "类型")
    priority = _map_priority(_first_value(row, "优先级", "priority"))
    status = _map_status(_first_value(row, "状态", "status"))
    raw_test_case_id = _first_value(row, "用例ID", "用例编号", "test_case_id", "testCaseId")
    test_case_id = _safe_test_case_id(raw_test_case_id, row_number=row_number)
    title = _first_value(row, "用例标题", "标题", "title")
    preconditions = _first_value(row, "前置条件", "前置", "preconditions")
    steps = _first_value(row, "测试步骤", "步骤", "操作步骤")
    test_data = _first_value(row, "测试数据", "数据", "入参")
    expected_result = _first_value(row, "预期结果", "期望结果", "expectedResult")
    remark = _first_value(row, "备注", "说明", "remark")

    if not title:
        title_parts = [feature, steps or expected_result or requirement_name or f"第{row_number}行用例"]
        title = "-".join(v for v in title_parts if v)
    title = _truncate_text(title, 100)
    expected_result = _truncate_text(expected_result or "按测试步骤执行并符合需求预期", 5000)
    preconditions = _truncate_text(preconditions, 5000) or None

    tags = ["真实导入"]
    if scenario_type:
        tags.append(_truncate_text(scenario_type, 64))
    if requirement_name and requirement_name != feature:
        tags.append(_truncate_text(requirement_name, 64))

    return {
        "projectId": project_id,
        "testCaseId": test_case_id,
        "feature": feature,
        "title": title,
        "type": _map_case_type(scenario_type),
        "priority": priority,
        "status": status,
        "apiMethod": "MANUAL",
        "apiUrl": f"/manual/{test_case_id}",
        "apiHeaders": {},
        "apiParams": {
            "requirementId": requirement_id,
            "requirementName": requirement_name,
            "scenarioType": scenario_type,
            "testData": test_data,
            "sourceRow": row_number,
            "sourceHadCaseId": bool(raw_test_case_id),
            "sourceTestCaseId": raw_test_case_id,
        },
        "expectedStatusCode": None,
        "expectedResult": expected_result,
        "preconditions": preconditions,
        "postconditions": None,
        "contentMd": _build_content_md_from_chinese_case(
            requirement_id=requirement_id,
            requirement_name=requirement_name,
            scenario_type=scenario_type,
            preconditions=preconditions or "",
            steps=steps,
            test_data=test_data,
            expected_result=expected_result,
            remark=remark,
        ),
        "tags": list(dict.fromkeys(tags))[:50],
    }


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
        if _looks_like_chinese_manual_case(row):
            payload_dict = _build_chinese_manual_payload_dict(project_id=project_id, row=row, row_number=idx)
            test_case_id = payload_dict["testCaseId"]
        else:
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

            payload_dict = {
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
