from __future__ import annotations
import csv
import io
import json
import re
from datetime import datetime
from typing import Any, Iterable

from app.schemas.doc_ingest import ApiCandidate, DocParseResult

_PLACEHOLDER_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_\.-]*)\}")

_CSV_FIELDNAMES: list[str] = [
    "test_case_id",
    "feature",
    "title",
    "apiMethod",
    "apiUrl",
    "apiHeaders",
    "apiParams",
    "expected_status_code",
    "expectedResult",
    "test_type",
    "priority",
    "status",
    "type",
    "preconditions",
    "postconditions",
    "tags",
]


def _normalize_method(v: str | None) -> str:
    if not v:
        return "GET"
    return str(v).strip().upper()

def _normalize_url(v: str | None) -> str:
    if not v or not str(v).strip():
        return "/unknown"
    return str(v).strip()

def _normalize_feature(v: str | None) -> str:
    if not v or not str(v).strip():
        return "DEFAULT"
    return str(v).strip()[:128]

def _normalize_title(c: ApiCandidate) -> str:
    if c.name and c.name.strip():
        return c.name.strip()[:100]
    m = _normalize_method(c.method)
    u = _normalize_url(c.url)
    return f"{m} {u}"[:100]


def _normalize_expected_result(v: str | None, status_code: int) -> str:
    if not v:
        return f'"code":{0 if 200 <= status_code <= 299 else 40001}'
    text = str(v).strip()
    if text:
        return text
    return f'"code":{0 if 200 <= status_code <= 299 else 40001}'


def _extract_expected_code(expected_result: str, fallback: int) -> int:
    try:
        obj = json.loads("{" + expected_result + "}")
        if isinstance(obj, dict) and isinstance(obj.get("code"), int):
            return int(obj["code"])
    except Exception:
        pass
    m = re.search(r'"code"\s*:\s*(\d+)', expected_result)
    if m:
        return int(m.group(1))
    return fallback

def _json_obj_text(obj: dict | None) -> str:
    return json.dumps(obj or {}, ensure_ascii=False, indent=None)

def _tags_text(tags: list[str] | None) -> str:
    tags = tags or []
    return ",".join([t for t in tags if t.strip()][:50])

def _collect_placeholders(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, str):
        for m in _PLACEHOLDER_RE.finditer(value):
            found.add(m.group(1))
        return found
    if isinstance(value, dict):
        for v in value.values():
            found |= _collect_placeholders(v)
        return found
    if isinstance(value, list):
        for v in value:
            found |= _collect_placeholders(v)
        return found
    return found


def _is_login_candidate(c: ApiCandidate, *, title: str, url: str) -> bool:
    t = title.lower()
    u = url.lower()
    tags = ",".join(c.tags or []).lower()
    return "登录" in title or "login" in t or "/auth/login" in u or "/login" in u or "login" in tags


def _is_me_candidate(c: ApiCandidate, *, title: str, url: str) -> bool:
    t = title.lower()
    u = url.lower()
    return "当前用户" in title or "/auth/me" in u or u.endswith("/me") or " profile" in t


def _requires_auth(*, is_login: bool, method: str, url: str) -> bool:
    if is_login:
        return False
    u = url.lower()
    if not u.startswith("/"):
        return False
    if u.startswith("/public/") or u.startswith("/health"):
        return False
    if "/auth/register" in u:
        return False
    if method == "OPTIONS":
        return False
    return True


def _build_postconditions(
    *,
    is_login: bool,
    is_me: bool,
    method: str,
    expected_result: str,
    expected_status_code: int,
) -> dict:
    expected_code = _extract_expected_code(expected_result, 0 if 200 <= expected_status_code <= 299 else 40001)
    postconditions = {"asserts": [{"json": "$.code", "op": "==", "value": expected_code}], "exports": {}}
    if expected_code != 0:
        return postconditions
    if is_login:
        postconditions["asserts"].extend(
            [
                {"json": "$.data.accessToken", "op": "!=", "value": None},
                {"json": "$.data.expiresIn", "op": "!=", "value": None},
            ]
        )
        postconditions["exports"] = {
            "accessToken": {"json": "$.data.accessToken"},
            "userId": {"json": "$.data.userId"},
            "tenantId": {"json": "$.data.tenantId"},
        }
        return postconditions
    if is_me:
        postconditions["asserts"].extend(
            [
                {"json": "$.data.userId", "op": "!=", "value": None},
                {"json": "$.data.tenantId", "op": "!=", "value": None},
            ]
        )
        postconditions["exports"] = {
            "userId": {"json": "$.data.userId"},
            "tenantId": {"json": "$.data.tenantId"},
        }
        return postconditions
    if method == "POST":
        postconditions["exports"] = {"id": {"json": "$.data.id"}}
    return postconditions

def _build_api_params(c: ApiCandidate) -> str:
    if c.params and c.params != {}:
        return _json_obj_text(c.params)

    title = _normalize_title(c).lower()
    feature = _normalize_feature(c.feature).lower()
    if "login" in title or "register" in title or "登录" in _normalize_title(c):
        params = {"username": "${adminUser}", "password": "${adminPwd}"}
    elif "project" in feature or "项目" in _normalize_title(c):
        params = {"name": "Demo Project", "description": "demo desc", "ownerId": "${userId}"}
    elif "order" in title:
        params = {"orderNo": "${orderNo}", "productId": "${productId}"}
    elif _normalize_method(c.method) in ("POST", "PUT", "PATCH") and ("create" in title or "update" in title):
        params = {"name": "示例名称", "description": "示例描述"}
    else:
        params = {}
    return _json_obj_text(params)


def _build_preconditions(
    *,
    case_id: str,
    method: str,
    url: str,
    headers: dict[str, Any],
    params: dict[str, Any],
    is_login: bool,
    is_me: bool,
    ctx: dict[str, str],
) -> dict:
    preconditions: dict[str, Any] = {"dependsOn": [], "requires": [], "bind": {}}
    required = _collect_placeholders(url) | _collect_placeholders(headers) | _collect_placeholders(params)

    if _requires_auth(is_login=is_login, method=method, url=url):
        required.add("accessToken")
        preconditions["bind"] = {"headers": {"Authorization": "Bearer ${accessToken}"}}
        login_case_id = ctx.get("login_case_id")
        if login_case_id and login_case_id != case_id:
            preconditions["dependsOn"].append(login_case_id)

    if is_me:
        required.add("accessToken")
        preconditions["bind"] = {"headers": {"Authorization": "Bearer ${accessToken}"}}
        login_case_id = ctx.get("login_case_id")
        if login_case_id and login_case_id != case_id and login_case_id not in preconditions["dependsOn"]:
            preconditions["dependsOn"].append(login_case_id)

    me_case_id = ctx.get("me_case_id")
    if me_case_id and me_case_id != case_id:
        if ("userId" in required or "tenantId" in required) and me_case_id not in preconditions["dependsOn"]:
            preconditions["dependsOn"].append(me_case_id)

    preconditions["requires"] = sorted([x for x in required if x])
    return preconditions


def _row_from_candidate(c: ApiCandidate, idx: int, ctx: dict[str, str]) -> dict[str, str]:
    case_id = f"TC{idx:03d}"
    title = _normalize_title(c)
    method = _normalize_method(c.method)
    url = _normalize_url(c.url)
    is_login = _is_login_candidate(c, title=title, url=url)
    is_me = _is_me_candidate(c, title=title, url=url)
    expected_status_code = c.expectedStatusCode if c.expectedStatusCode is not None else 200
    expected_result = _normalize_expected_result(c.expectedResult, expected_status_code)
    headers = dict(c.headers or {})
    api_params_text = _build_api_params(c)
    try:
        params_obj = json.loads(api_params_text) if api_params_text else {}
    except Exception:
        params_obj = {}
    if method in {"POST", "PUT", "PATCH"} and params_obj:
        has_ct = any(str(k).strip().lower() == "content-type" for k in headers.keys())
        if not has_ct:
            headers["Content-Type"] = "application/json"
    postconditions = _build_postconditions(
        is_login=is_login,
        is_me=is_me,
        method=method,
        expected_result=expected_result,
        expected_status_code=expected_status_code,
    )
    preconditions = _build_preconditions(
        case_id=case_id,
        method=method,
        url=url,
        headers=headers,
        params=params_obj,
        is_login=is_login,
        is_me=is_me,
        ctx=ctx,
    )

    expected_code = _extract_expected_code(expected_result, 0 if 200 <= expected_status_code <= 299 else 40001)
    if expected_code == 0:
        if is_login and not ctx.get("login_case_id"):
            ctx["login_case_id"] = case_id
        if is_me and not ctx.get("me_case_id"):
            ctx["me_case_id"] = case_id

    row: dict[str, str] = {
        "test_case_id": case_id,
        "feature": _normalize_feature(c.feature),
        "title": title,
        "apiMethod": method,
        "apiUrl": url,
        "apiHeaders": _json_obj_text(headers),
        "apiParams": _json_obj_text(params_obj),
        "expected_status_code": str(expected_status_code),
        "expectedResult": expected_result,
        "test_type": "positive",
        "priority": "P0",
        "status": "DRAFT",
        "type": "API",
        "preconditions": _json_obj_text(preconditions),
        "postconditions": _json_obj_text(postconditions),
        "tags": _tags_text(c.tags),
    }
    return row


def build_csv_from_rows(rows: list[dict[str, str]], *, fname_prefix: str = "api_test_cases") -> tuple[str, str, int]:
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    fname = f"{fname_prefix}_{ts}.csv"
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_CSV_FIELDNAMES)
    writer.writeheader()
    if rows:
        writer.writerows(rows)
    buf.seek(0)
    return fname, buf.getvalue(), len(rows)


def build_csv_from_doc_parse(result: DocParseResult) -> tuple[str, str, int]:
    items: Iterable[ApiCandidate] = result.apiCandidates or []
    ctx: dict[str, str] = {}
    rows = [_row_from_candidate(c, idx, ctx) for idx, c in enumerate(items, start=1)]
    return build_csv_from_rows(rows, fname_prefix="api_test_cases")
