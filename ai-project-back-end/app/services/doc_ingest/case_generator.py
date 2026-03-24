from __future__ import annotations

import json
import re
from typing import Iterable

from app.schemas.doc_ingest import ApiCandidate, DocParseResult
from app.schemas.testcase_gen import GeneratedTestCaseRow
from app.services.llm.provider import get_provider


_DEFAULT_PRECONDITIONS_OBJ: dict = {
    "dependsOn": [],
    "requires": [],
    "bind": {},
}

_DEFAULT_POSTCONDITIONS_OBJ: dict = {
    "asserts": [],
    "exports": {},
}

_PLACEHOLDER_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_\.-]*)\}")
_URL_BRACE_PARAM_RE = re.compile(r"(?<!\$)\{([A-Za-z_][A-Za-z0-9_]*)\}")
_URL_COLON_PARAM_RE = re.compile(r"/:([A-Za-z_][A-Za-z0-9_]*)")


def _normalize_feature(v: str | None) -> str:
    if not v or not str(v).strip():
        return "DEFAULT"
    return str(v).strip()[:128]


def _normalize_title(c: ApiCandidate) -> str:
    if c.name and c.name.strip():
        return c.name.strip()[:100]
    m = (c.method or "GET").strip().upper() or "GET"
    u = (c.url or "/unknown").strip() or "/unknown"
    return f"{m} {u}"[:100]


def _normalize_method(v: str | None) -> str:
    return (v or "GET").strip().upper() or "GET"


def _normalize_url(v: str | None) -> str:
    return (v or "/unknown").strip() or "/unknown"


def _tags_text(tags: list[str] | None) -> str:
    tags = tags or []
    return ",".join([t for t in tags if str(t).strip()][:50])


def _coerce_json_obj(v: object) -> dict:
    if isinstance(v, dict):
        return v
    if isinstance(v, str):
        text = v.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except Exception:
            return {}
        if isinstance(parsed, dict):
            return parsed
    return {}


def _expected_result_text(status_code: int, value: str | None) -> str:
    text = str(value or "").strip()
    if text:
        return text
    if 200 <= status_code <= 299:
        return '"code":0'
    return '"code":40001'


def _coerce_status_code(v: object, default: int = 200) -> int:
    if isinstance(v, int):
        return v
    text = str(v or "").strip()
    if not text:
        return default
    try:
        return int(text)
    except Exception:
        return default


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


def _var_name_from_key(key: str) -> str:
    k = str(key or "").strip()
    if not k:
        return "var"
    if not re.match(r"^[A-Za-z_]", k):
        k = f"v_{k}"
    k = re.sub(r"[^A-Za-z0-9_\.-]", "_", k)
    return k


def _parameterize_url(url: str) -> tuple[str, list[str]]:
    text = _normalize_url(url)
    required: list[str] = []

    def _brace_repl(m: re.Match) -> str:
        name = m.group(1)
        required.append(name)
        return "${" + name + "}"

    text = _URL_BRACE_PARAM_RE.sub(_brace_repl, text)

    def _colon_repl(m: re.Match) -> str:
        name = m.group(1)
        required.append(name)
        return "/${" + name + "}"

    text = _URL_COLON_PARAM_RE.sub(_colon_repl, text)
    return text, required


def _parameterize_headers(headers: dict) -> tuple[dict, set[str]]:
    out = dict(headers or {})
    required: set[str] = set()
    for k, v in list(out.items()):
        kk = str(k or "").strip()
        if not kk:
            continue
        low = kk.lower()
        if low == "authorization":
            out[kk] = "Bearer ${token}"
            required.add("token")
            continue
        if low in {"x-api-key", "x_api_key", "apikey", "api_key"}:
            out[kk] = "${env.apiKey}"
            required.add("env.apiKey")
            continue
        required |= _collect_placeholders(v)
    return out, required


def _parameterize_params(params: dict) -> tuple[dict, set[str]]:
    out = dict(params or {})
    required: set[str] = set()
    for k, v in list(out.items()):
        kk = str(k or "").strip()
        if not kk:
            continue
        if kk.startswith("_"):
            required |= _collect_placeholders(v)
            out[k] = v
            continue
        low = kk.lower()
        if isinstance(v, dict):
            child, child_req = _parameterize_params(v)
            out[k] = child
            required |= child_req
            continue
        if isinstance(v, list):
            new_list = []
            for item in v:
                if isinstance(item, dict):
                    child, child_req = _parameterize_params(item)
                    new_list.append(child)
                    required |= child_req
                else:
                    required |= _collect_placeholders(item)
                    new_list.append(item)
            out[k] = new_list
            continue
        if isinstance(v, str) and _PLACEHOLDER_RE.search(v):
            required |= _collect_placeholders(v)
            continue
        if low in {"token", "accesstoken", "refreshToken", "refresh_token", "apikey", "api_key"}:
            out[k] = "${env." + _var_name_from_key(kk) + "}"
            required.add("env." + _var_name_from_key(kk))
            continue
        if low == "id" or low.endswith("_id") or low.endswith("id"):
            name = _var_name_from_key(kk)
            out[k] = "${" + name + "}"
            required.add(name)
            continue
    return out, required


def _ensure_preconditions(pre: dict | None, *, required_vars: Iterable[str]) -> dict:
    obj = dict(pre or {})
    obj.setdefault("dependsOn", [])
    obj.setdefault("requires", [])
    obj.setdefault("bind", {})
    req = obj.get("requires") or []
    if isinstance(req, str):
        req_list = [req]
    elif isinstance(req, list):
        req_list = req
    else:
        req_list = []
    merged = set([str(x).strip() for x in req_list if str(x).strip()])
    merged |= set([str(x).strip() for x in required_vars if str(x).strip()])
    obj["requires"] = sorted(merged)
    if not isinstance(obj.get("dependsOn"), list):
        obj["dependsOn"] = []
    if not isinstance(obj.get("bind"), dict):
        obj["bind"] = {}
    return obj


def _ensure_postconditions(post: dict | None) -> dict:
    obj = dict(post or {})
    obj.setdefault("asserts", [])
    obj.setdefault("exports", {})
    if not isinstance(obj.get("asserts"), list):
        if isinstance(obj.get("asserts"), dict):
            obj["asserts"] = [obj.get("asserts")]
        else:
            obj["asserts"] = []
    if not isinstance(obj.get("exports"), dict):
        obj["exports"] = {}
    return obj


def _parse_expected_json(text: str) -> object | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        pass
    first_obj = raw.find("{")
    last_obj = raw.rfind("}")
    if 0 <= first_obj < last_obj:
        snippet = raw[first_obj : last_obj + 1]
        try:
            return json.loads(snippet)
        except Exception:
            pass
    first_arr = raw.find("[")
    last_arr = raw.rfind("]")
    if 0 <= first_arr < last_arr:
        snippet = raw[first_arr : last_arr + 1]
        try:
            return json.loads(snippet)
        except Exception:
            pass
    if ":" in raw and not raw.lstrip().startswith(("{", "[")):
        try:
            return json.loads("{" + raw + "}")
        except Exception:
            return None
    return None


def _flatten_json_asserts(obj: object, *, max_items: int = 8) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []

    def _is_primitive(v: object) -> bool:
        return v is None or isinstance(v, (str, int, float, bool))

    def _add(path: str, value: object) -> None:
        if len(out) >= max_items:
            return
        out.append({"json": path, "op": "==", "value": value})

    if isinstance(obj, dict):
        for k, v in list(obj.items())[:max_items]:
            key = str(k or "").strip()
            if not key:
                continue
            if _is_primitive(v):
                _add(f"$.{key}", v)
            elif isinstance(v, dict):
                for k2, v2 in list(v.items())[: max_items - len(out)]:
                    key2 = str(k2 or "").strip()
                    if not key2:
                        continue
                    if _is_primitive(v2):
                        _add(f"$.{key}.{key2}", v2)
            if len(out) >= max_items:
                break
    return out


def _maybe_add_common_asserts(post: dict, expected_result: str) -> dict:
    if post.get("asserts"):
        return post
    text = str(expected_result or "")
    m = re.search(r"""['"]code['"]\s*:\s*(\d+)""", text)
    if m:
        try:
            code = int(m.group(1))
        except Exception:
            code = None
        if code is not None:
            post["asserts"] = [{"json": "$.code", "op": "==", "value": code}]
            return post
    parsed = _parse_expected_json(text)
    inferred = _flatten_json_asserts(parsed)
    if inferred:
        post["asserts"] = inferred
    return post


def _requires_auth_like(*, method: str, url: str, title: str) -> bool:
    m = _normalize_method(method)
    if m == "OPTIONS":
        return False
    u = str(url or "").strip().lower()
    if not u.startswith("/"):
        return False
    t = str(title or "").lower()
    if "/health" in u or u.startswith("/public/"):
        return False
    if "/auth/login" in u or u.endswith("/login") or "登录" in title or "login" in t:
        return False
    if "/auth/register" in u:
        return False
    return True


_JSON_METHODS_WITH_BODY = {"POST", "PUT", "PATCH"}


def _ensure_json_content_type(headers: dict, *, method: str, params: dict) -> dict:
    m = _normalize_method(method)
    if m not in _JSON_METHODS_WITH_BODY:
        return headers
    if not params:
        return headers
    has_ct = any(str(k).strip().lower() == "content-type" for k in (headers or {}).keys())
    if has_ct:
        return headers
    out = dict(headers or {})
    out["Content-Type"] = "application/json"
    return out


def _register_rows(*, api_seq: int, c: ApiCandidate) -> list[GeneratedTestCaseRow]:
    feature = _normalize_feature(c.feature) if (c.feature or "").strip() else "认证模块"
    method = "POST"
    url = "/api/auth/register"
    headers = {"Content-Type": "application/json"}
    base_tags = ",".join([s for s in [_tags_text(c.tags), "register", "auth"] if s])

    def _row(case_seq: int, *, title: str, params: dict, expected_result: str, test_type: str, priority: str, post: dict | None = None) -> GeneratedTestCaseRow:
        return _auto_parameterize_row(
            GeneratedTestCaseRow(
                test_case_id=_test_case_id(api_seq, case_seq),
                feature=feature,
                title=title[:100],
                apiMethod=method,
                apiUrl=url,
                apiHeaders=headers,
                apiParams=params,
                expected_status_code=200,
                expectedResult=expected_result,
                test_type=test_type,
                priority=priority,
                status="DRAFT",
                type="API",
                preconditions=dict(_DEFAULT_PRECONDITIONS_OBJ),
                postconditions=post or dict(_DEFAULT_POSTCONDITIONS_OBJ),
                tags=",".join([s for s in [base_tags, test_type] if s]),
            )
        )

    ok_post = {
        "asserts": [
            {"json": "$.code", "op": "==", "value": 0},
            {"json": "$.data.userId", "op": "!=", "value": None},
            {"json": "$.data.phone", "op": "==", "value": "${env.registerPhone}"},
            {"json": "$.data.username", "op": "==", "value": "${env.registerUsername}"},
        ],
        "exports": {
            "registerUserId": {"json": "$.data.userId"},
            "registerPhone": {"json": "$.data.phone"},
            "registerUsername": {"json": "$.data.username"},
        },
    }

    rows: list[GeneratedTestCaseRow] = []
    rows.append(
        _row(
            1,
            title="用户注册_成功_使用环境变量",
            params={
                "phone": "${env.registerPhone}",
                "username": "${env.registerUsername}",
                "password": "${env.registerPassword}",
                "confirmPassword": "${env.registerPassword}",
                "captcha": "123456",
            },
            expected_result='"code":0',
            test_type="positive",
            priority="P0",
            post=ok_post,
        )
    )
    rows.append(
        _row(
            2,
            title="用户注册_缺少phone",
            params={"username": "u_qa_001", "password": "ab123456", "confirmPassword": "ab123456", "captcha": "123456"},
            expected_result='"code":40001',
            test_type="negative",
            priority="P0",
        )
    )
    rows.append(
        _row(
            3,
            title="用户注册_缺少username",
            params={"phone": "13800000000", "password": "ab123456", "confirmPassword": "ab123456", "captcha": "123456"},
            expected_result='"code":40001',
            test_type="negative",
            priority="P0",
        )
    )
    rows.append(
        _row(
            4,
            title="用户注册_缺少password",
            params={"phone": "13800000000", "username": "u_qa_001", "confirmPassword": "ab123456", "captcha": "123456"},
            expected_result='"code":40001',
            test_type="negative",
            priority="P0",
        )
    )
    rows.append(
        _row(
            5,
            title="用户注册_缺少confirmPassword",
            params={"phone": "13800000000", "username": "u_qa_001", "password": "ab123456", "captcha": "123456"},
            expected_result='"code":40001',
            test_type="negative",
            priority="P0",
        )
    )
    rows.append(
        _row(
            6,
            title="用户注册_缺少captcha",
            params={"phone": "13800000000", "username": "u_qa_001", "password": "ab123456", "confirmPassword": "ab123456"},
            expected_result='"code":40001',
            test_type="negative",
            priority="P0",
        )
    )
    rows.append(
        _row(
            7,
            title="用户注册_phone格式非法_不满足手机号正则",
            params={"phone": "123456", "username": "u_qa_001", "password": "ab123456", "confirmPassword": "ab123456", "captcha": "123456"},
            expected_result='"code":40001',
            test_type="negative",
            priority="P1",
        )
    )
    rows.append(
        _row(
            8,
            title="用户注册_username过短_2位",
            params={"phone": "13800000000", "username": "ab", "password": "ab123456", "confirmPassword": "ab123456", "captcha": "123456"},
            expected_result='"code":40001',
            test_type="boundary",
            priority="P1",
        )
    )
    rows.append(
        _row(
            9,
            title="用户注册_username过长_65位",
            params={
                "phone": "13800000000",
                "username": "a" * 65,
                "password": "ab123456",
                "confirmPassword": "ab123456",
                "captcha": "123456",
            },
            expected_result='"code":40001',
            test_type="boundary",
            priority="P1",
        )
    )
    rows.append(
        _row(
            10,
            title="用户注册_password过短_7位",
            params={"phone": "13800000000", "username": "u_qa_001", "password": "ab12345", "confirmPassword": "ab12345", "captcha": "123456"},
            expected_result='"code":40001',
            test_type="boundary",
            priority="P1",
        )
    )
    rows.append(
        _row(
            11,
            title="用户注册_password过长_129位",
            params={
                "phone": "13800000000",
                "username": "u_qa_001",
                "password": ("a" * 128) + "1",
                "confirmPassword": ("a" * 128) + "1",
                "captcha": "123456",
            },
            expected_result='"code":40001',
            test_type="boundary",
            priority="P1",
        )
    )
    rows.append(
        _row(
            12,
            title="用户注册_confirmPassword不一致",
            params={"phone": "13800000000", "username": "u_qa_001", "password": "ab123456", "confirmPassword": "ab123457", "captcha": "123456"},
            expected_result='"code":40001',
            test_type="negative",
            priority="P0",
        )
    )
    rows.append(
        _row(
            13,
            title="用户注册_密码复杂度不足_仅数字",
            params={"phone": "13800000000", "username": "u_qa_001", "password": "12345678", "confirmPassword": "12345678", "captcha": "123456"},
            expected_result='"code":40001',
            test_type="negative",
            priority="P0",
        )
    )
    rows.append(
        _row(
            14,
            title="用户注册_密码复杂度不足_仅字母",
            params={"phone": "13800000000", "username": "u_qa_001", "password": "abcdefgh", "confirmPassword": "abcdefgh", "captcha": "123456"},
            expected_result='"code":40001',
            test_type="negative",
            priority="P0",
        )
    )
    rows.append(
        _row(
            15,
            title="用户注册_captcha错误",
            params={"phone": "13800000000", "username": "u_qa_001", "password": "ab123456", "confirmPassword": "ab123456", "captcha": "000000"},
            expected_result='"code":40001',
            test_type="negative",
            priority="P0",
        )
    )
    rows.append(
        _row(
            16,
            title="用户注册_请求体包含多余字段_extra_forbid",
            params={
                "phone": "13800000000",
                "username": "u_qa_001",
                "password": "ab123456",
                "confirmPassword": "ab123456",
                "captcha": "123456",
                "extra": "x",
            },
            expected_result='"code":40001',
            test_type="negative",
            priority="P1",
        )
    )
    rows.append(
        _row(
            17,
            title="用户注册_手机号已存在_依赖环境变量existingPhone",
            params={"phone": "${env.existingPhone}", "username": "conflict_phone_user_001", "password": "ab123456", "confirmPassword": "ab123456", "captcha": "123456"},
            expected_result='"code":40901',
            test_type="negative",
            priority="P0",
        )
    )
    rows.append(
        _row(
            18,
            title="用户注册_用户名已存在_依赖existingUsername与freshPhone",
            params={"phone": "${env.freshPhoneForConflictUsername}", "username": "${env.existingUsername}", "password": "ab123456", "confirmPassword": "ab123456", "captcha": "123456"},
            expected_result='"code":40901',
            test_type="negative",
            priority="P0",
        )
    )
    return rows


def _maybe_add_exports(post: dict, *, method: str, url: str, title: str, expected_result: str) -> dict:
    exports = post.get("exports") if isinstance(post.get("exports"), dict) else {}
    if exports:
        return post
    u = str(url or "").lower()
    t = str(title or "")
    er = str(expected_result or "").lower()
    if "/login" in u or "/auth/login" in u or "登录" in t:
        if "accesstoken" in er:
            path = "$.data.accessToken"
        elif "data" in er and "token" in er:
            path = "$.data.token"
        else:
            path = "$.token"
        post["exports"] = {"token": {"json": path}}
        return post
    if method == "POST" and ("id" in er or '"id"' in er):
        path = "$.data.id" if "data" in er else "$.id"
        post["exports"] = {"id": {"json": path}}
        return post
    return post


def _auto_parameterize_row(r: GeneratedTestCaseRow) -> GeneratedTestCaseRow:
    url, url_vars = _parameterize_url(str(r.apiUrl or ""))
    headers, header_vars = _parameterize_headers(_coerce_json_obj(r.apiHeaders))
    params, params_vars = _parameterize_params(_coerce_json_obj(r.apiParams))
    required = set(url_vars) | header_vars | params_vars | _collect_placeholders(url) | _collect_placeholders(headers) | _collect_placeholders(params)
    pre = _ensure_preconditions(_coerce_json_obj(r.preconditions), required_vars=required)
    post = _ensure_postconditions(_coerce_json_obj(r.postconditions))
    post = _maybe_add_common_asserts(post, str(r.expectedResult or ""))
    post = _maybe_add_exports(
        post,
        method=_normalize_method(r.apiMethod),
        url=url,
        title=str(r.title or ""),
        expected_result=str(r.expectedResult or ""),
    )
    if _requires_auth_like(method=_normalize_method(r.apiMethod), url=url, title=str(r.title or "")):
        bind = pre.get("bind") if isinstance(pre.get("bind"), dict) else {}
        headers_bind = bind.get("headers") if isinstance(bind.get("headers"), dict) else {}
        if not any(str(k).strip().lower() == "authorization" for k in headers_bind.keys()):
            headers_bind = dict(headers_bind)
            headers_bind["Authorization"] = "Bearer ${token}"
            bind = dict(bind)
            bind["headers"] = headers_bind
            pre["bind"] = bind
        if not any(str(k).strip().lower() == "authorization" for k in (headers or {}).keys()):
            headers = dict(headers or {})
            headers["Authorization"] = "Bearer ${token}"
        req = pre.get("requires")
        if not isinstance(req, list):
            req = []
        if "token" not in req:
            pre["requires"] = sorted(set([*req, "token"]))
    r.apiUrl = url
    r.apiHeaders = headers
    r.apiParams = params
    r.preconditions = pre
    r.postconditions = post
    return r


def _apply_login_dependency(rows: list[GeneratedTestCaseRow]) -> list[GeneratedTestCaseRow]:
    login_case_id: str | None = None
    for r in rows:
        url = str(r.apiUrl or "").lower()
        title = str(r.title or "")
        if "/auth/login" in url or url.endswith("/login") or "登录" in title or "login" in title.lower():
            if str(r.test_type or "").lower() == "positive":
                login_case_id = str(r.test_case_id or "").strip() or None
                break
    if not login_case_id:
        return rows
    for r in rows:
        if str(r.test_case_id or "").strip() == login_case_id:
            continue
        pre = _coerce_json_obj(r.preconditions)
        requires = pre.get("requires") or []
        if isinstance(requires, str):
            requires = [requires]
        if not isinstance(requires, list):
            continue
        if "token" not in [str(x).strip() for x in requires if str(x).strip()]:
            continue
        depends = pre.get("dependsOn") or []
        if isinstance(depends, str):
            depends = [depends]
        if not isinstance(depends, list):
            depends = []
        dep_list = [str(x).strip() for x in depends if str(x).strip()]
        if login_case_id not in dep_list:
            pre["dependsOn"] = [*dep_list, login_case_id]
            r.preconditions = pre
    return rows


def _test_case_id(api_seq: int, case_seq: int) -> str:
    return f"TC{api_seq:03d}{case_seq:03d}"


def _negative_params(params: dict) -> dict:
    if not params:
        return {"_invalid": True}
    out = dict(params)
    first_key = next((k for k in out.keys() if not str(k).startswith("_")), next(iter(out.keys())))
    out.pop(first_key, None)
    if not out:
        out["_invalid"] = True
    return out


def _boundary_params(params: dict) -> dict:
    if not params:
        return {"_boundary": "empty"}
    out = dict(params)
    first_key = next((k for k in out.keys() if not str(k).startswith("_")), next(iter(out.keys())))
    value = out.get(first_key)
    if isinstance(value, bool):
        out[first_key] = not value
    elif isinstance(value, int):
        out[first_key] = 0 if value != 0 else 2147483647
    elif isinstance(value, float):
        out[first_key] = 0.0 if value != 0.0 else 1e-09
    elif isinstance(value, str):
        out[first_key] = "A" * min(max(1, len(value) * 2), 256)
    elif isinstance(value, list):
        out[first_key] = []
    elif isinstance(value, dict):
        out[first_key] = {}
    else:
        out[first_key] = None
    return out


def _heuristic_rows(items: Iterable[ApiCandidate]) -> list[GeneratedTestCaseRow]:
    rows: list[GeneratedTestCaseRow] = []
    for idx, c in enumerate(items, start=1):
        method = _normalize_method(c.method)
        url_raw = _normalize_url(c.url)
        if url_raw.strip().lower() == "/api/auth/register":
            rows.extend(_register_rows(api_seq=idx, c=c))
            continue
        url, _ = _parameterize_url(url_raw)
        feature = _normalize_feature(c.feature)
        base_title = _normalize_title(c)
        base_headers, _ = _parameterize_headers(c.headers or {})
        base_params, _ = _parameterize_params(c.params or {})
        tags = _tags_text(c.tags)
        expected_status_code = _coerce_status_code(c.expectedStatusCode, default=200)
        expected_result = _expected_result_text(expected_status_code, c.expectedResult)
        base_headers = _ensure_json_content_type(base_headers, method=method, params=base_params)
        positive = GeneratedTestCaseRow(
            test_case_id=_test_case_id(idx, 1),
            feature=feature,
            title=f"{base_title}_正常流程"[:100],
            apiMethod=method,
            apiUrl=url,
            apiHeaders=base_headers,
            apiParams=base_params,
            expected_status_code=expected_status_code,
            expectedResult=expected_result,
            test_type="positive",
            priority="P0",
            status="DRAFT",
            type="API",
            preconditions=dict(_DEFAULT_PRECONDITIONS_OBJ),
            postconditions=dict(_DEFAULT_POSTCONDITIONS_OBJ),
            tags=",".join([s for s in [tags, "positive"] if s]),
        )
        negative = GeneratedTestCaseRow(
            test_case_id=_test_case_id(idx, 2),
            feature=feature,
            title=f"{base_title}_异常参数"[:100],
            apiMethod=method,
            apiUrl=url,
            apiHeaders=base_headers,
            apiParams=_negative_params(base_params),
            expected_status_code=expected_status_code,
            expectedResult='"code":40001',
            test_type="negative",
            priority="P1",
            status="DRAFT",
            type="API",
            preconditions=dict(_DEFAULT_PRECONDITIONS_OBJ),
            postconditions=dict(_DEFAULT_POSTCONDITIONS_OBJ),
            tags=",".join([s for s in [tags, "negative"] if s]),
        )
        boundary = GeneratedTestCaseRow(
            test_case_id=_test_case_id(idx, 3),
            feature=feature,
            title=f"{base_title}_边界值"[:100],
            apiMethod=method,
            apiUrl=url,
            apiHeaders=base_headers,
            apiParams=_boundary_params(base_params),
            expected_status_code=expected_status_code,
            expectedResult='"code":40001',
            test_type="boundary",
            priority="P1",
            status="DRAFT",
            type="API",
            preconditions=dict(_DEFAULT_PRECONDITIONS_OBJ),
            postconditions=dict(_DEFAULT_POSTCONDITIONS_OBJ),
            tags=",".join([s for s in [tags, "boundary"] if s]),
        )
        rows.extend([_auto_parameterize_row(positive), _auto_parameterize_row(negative), _auto_parameterize_row(boundary)])
    return rows


def generate_testcase_rows(
    *,
    result: DocParseResult,
    instruction: str | None,
    skill_id: str,
    max_cases: int,
    mode: str,
) -> list[GeneratedTestCaseRow]:
    m = (mode or "OFF").strip().upper()
    items = list(result.apiCandidates or [])
    if m == "OFF":
        return []

    provider = get_provider()
    rows = []
    if provider.is_configured:
        doc_text = ""
        if result.sections:
            chunks: list[str] = []
            for s in result.sections[:60]:
                title = str(getattr(s, "title", "") or "").strip()
                body = str(getattr(s, "text", "") or "").strip()
                if not body:
                    continue
                if title:
                    chunks.append(title)
                chunks.append(body)
            doc_text = "\n\n".join(chunks).strip()
        if not doc_text:
            raw = getattr(result, "raw", None)
            if raw is not None:
                doc_text = str(getattr(raw, "textDigest", "") or "")
        try:
            rows = provider.generate_testcases(
                skill_id=skill_id,
                instruction=str(instruction or "").strip(),
                api_candidates=items,
                doc_text=doc_text,
                max_cases=max_cases,
            )
        except Exception:
            rows = []

    if rows:
        normalized: list[GeneratedTestCaseRow] = []
        for r in rows[: max(1, max_cases)]:
            normalized.append(_auto_parameterize_row(r))
        return _apply_login_dependency(normalized)

    return _apply_login_dependency(_heuristic_rows(items)[: max(1, max_cases)])


def rows_to_csv_dicts(rows: list[GeneratedTestCaseRow], *, base_url: str = "") -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    base_url = str(base_url or "").strip()
    if base_url and base_url.endswith("/"):
        base_url = base_url[:-1]

    for r in rows:
        api_headers = _coerce_json_obj(r.apiHeaders)
        api_params = _coerce_json_obj(r.apiParams)
        pre = _coerce_json_obj(r.preconditions)
        post = _coerce_json_obj(r.postconditions)
        tags = r.tags
        if isinstance(tags, list):
            tags = ",".join([t for t in [str(x).strip() for x in tags] if t][:50])
        tags = str(tags or "")
        expected_result = str(r.expectedResult or "").strip()
        if not expected_result:
            expected_result = "{}"
        expected_status_code = _coerce_status_code(r.expected_status_code, default=200)

        url = _normalize_url(r.apiUrl)
        if base_url:
            if not url.startswith("/"):
                url = f"/{url}"
            url = f"{base_url}{url}"

        out.append(
            {
                "test_case_id": str(r.test_case_id or ""),
                "feature": _normalize_feature(r.feature),
                "title": str(r.title or "")[:100],
                "apiMethod": _normalize_method(r.apiMethod),
                "apiUrl": url,
                "apiHeaders": json.dumps(api_headers or {}, ensure_ascii=False),
                "apiParams": json.dumps(api_params or {}, ensure_ascii=False),
                "expected_status_code": str(expected_status_code),
                "expectedResult": expected_result,
                "test_type": str(r.test_type or "positive"),
                "priority": str(r.priority or "P1").strip().upper() or "P1",
                "status": str(r.status or "DRAFT").strip().upper() or "DRAFT",
                "type": str(r.type or "API").strip().upper() or "API",
                "preconditions": json.dumps(pre or {}, ensure_ascii=False),
                "postconditions": json.dumps(post or {}, ensure_ascii=False),
                "tags": tags,
            }
        )
    return out
