from __future__ import annotations

import io
import uuid
from pathlib import Path

import openpyxl

from app.services.testcase_import import _build_row_payloads, _parse_csv_rows, _parse_xlsx_rows


def test_build_row_payloads_from_sample_csv() -> None:
    root = Path(__file__).resolve().parents[2]
    samples = sorted((root / "test_cases").glob("api_test_cases_*.csv"))
    if samples:
        content = samples[-1].read_bytes()
    else:
        content = (
            "test_case_id,feature,title,apiMethod,apiUrl,apiHeaders,apiParams,expected_status_code,expectedResult,test_type,priority,status,type,preconditions,postconditions,tags\n"
            ',认证,login,POST,/api/auth/login,{},{},200,"{\\"code\\":0}",generated,P1,DRAFT,API,,,"auth,login"\n'
        ).encode("utf-8")
    rows = _parse_csv_rows(content)
    project_id = str(uuid.uuid4())
    payloads, errors = _build_row_payloads(project_id=project_id, rows=rows[:5], mode="partial")
    assert errors == []
    assert len(payloads) == min(5, len(rows))
    assert payloads[0].payload.projectId == project_id
    assert payloads[0].payload.type == "API"


def test_build_row_payloads_rejects_invalid_json() -> None:
    project_id = str(uuid.uuid4())
    rows = [
        {
            "test_case_id": "TC001",
            "feature": "认证",
            "title": "login",
            "apimethod": "POST",
            "apiurl": "/api/auth/login",
            "apiheaders": "{bad}",
            "apiparams": "{}",
            "expected_status_code": "200",
            "expectedresult": '{"code":0}',
            "priority": "P0",
            "status": "DRAFT",
            "type": "API",
            "preconditions": "{}",
            "postconditions": "{}",
            "tags": "auth,login",
        }
    ]
    payloads, errors = _build_row_payloads(project_id=project_id, rows=rows, mode="partial")
    assert payloads == []
    assert len(errors) == 1
    assert errors[0].field == "apiHeaders"


def test_build_row_payloads_from_chinese_manual_case_xlsx() -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "cases"
    ws.append(["需求ID", "需求名称", "模块", "场景类型", "优先级", "用例ID", "用例标题", "前置条件", "测试步骤", "测试数据", "预期结果", "备注"])
    ws.append(["REQ-LIVE-001", "直播间贴纸", "直播互动", "边界", "P0", "TC_LIVE_002", "文字贴纸10字边界", "已在编辑页", "输入10字并保存", "10字文本", "保存成功", "历史沉淀"])
    ws.append(["REQ-AUTH-001", "登录鉴权", "账号安全", "异常", "P1", "", "", "登录页可用", "点击登录", "合法账号密码", "提示超时并可重试", "补充行"])
    content = io.BytesIO()
    wb.save(content)

    rows = _parse_xlsx_rows(content.getvalue())
    project_id = str(uuid.uuid4())
    payloads, errors = _build_row_payloads(project_id=project_id, rows=rows, mode="partial")

    assert errors == []
    assert len(payloads) == 2
    first = payloads[0].payload
    assert first.projectId == project_id
    assert first.testCaseId == "TC_LIVE_002"
    assert first.title == "文字贴纸10字边界"
    assert first.feature == "直播互动"
    assert first.type == "UI"
    assert first.priority == "P0"
    assert first.status == "DRAFT"
    assert first.apiMethod == "MANUAL"
    assert first.apiUrl == "/manual/TC_LIVE_002"
    assert first.preconditions == "已在编辑页"
    assert first.expectedResult == "保存成功"
    assert "测试步骤" in first.contentMd
    assert first.apiParams["requirementId"] == "REQ-LIVE-001"
    assert first.apiParams["scenarioType"] == "边界"
    assert first.tags == ["真实导入", "边界", "直播间贴纸"]

    second = payloads[1].payload
    assert second.testCaseId is not None
    assert second.title == "账号安全-点击登录"
