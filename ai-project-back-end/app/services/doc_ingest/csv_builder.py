from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime
from typing import Iterable, Dict, Any

# 注意：若项目中存在app.schemas.doc_ingest，需保留原导入；否则注释以下行
# from app.schemas.doc_ingest import ApiCandidate, DocParseResult

# 为方便测试，提供模拟的ApiCandidate和DocParseResult类（实际使用时替换为项目真实类）
class MockApiCandidate:
    def __init__(self, name=None, method=None, url=None, params=None, headers=None, 
                 expectedStatusCode=None, expectedResult=None, feature=None, tags=None):
        self.name = name
        self.method = method
        self.url = url
        self.params = params or {}
        self.headers = headers or {}
        self.expectedStatusCode = expectedStatusCode
        self.expectedResult = expectedResult
        self.feature = feature
        self.tags = tags or []

class MockDocParseResult:
    def __init__(self, apiCandidates=None):
        self.apiCandidates = apiCandidates or []

# ===================== 核心配置（严格遵循规则）=====================
# 1. 前置条件默认值：仅包含dependsOn/bind/vars三节点，无requires字段
_DEFAULT_PRECONDITIONS_OBJ: dict = {
    "dependsOn": [],  # 依赖用例ID数组（空数组表示无依赖）
    "bind": {},       # 绑定参数（headers/params，无绑定则为空对象）
    "vars": {}        # 自定义变量（无变量则为空对象，必填）
}

# 2. 后置条件默认值：包含asserts/exports两节点
_DEFAULT_POSTCONDITIONS_OBJ: dict = {
    "asserts": [
        {"json": "$.code", "op": "==", "value": 0},  # 默认断言响应码为0
        {"json": "$.success", "op": "==", "value": True}  # 补充通用断言
    ],
    "exports": {}  # 无导出参数则为空对象
}

# 3. CSV固定字段名（包含所有必要字段）
_CSV_FIELDNAMES: list[str] = [
    "test_case_id", "feature", "title", "apiUrl", "apiMethod",
    "apiHeaders", "apiParams", "expected_status_code", "expectedResult",
    "test_type", "priority", "status", "type", "preconditions",
    "postconditions", "tags"
]

# ===================== 工具函数 =====================
def _normalize_method(v: str | None) -> str:
    """标准化HTTP方法（GET/POST/PUT/DELETE），默认GET"""
    return str(v).strip().upper() if (v and str(v).strip()) else "GET"

def _normalize_url(v: str | None) -> str:
    """标准化URL，默认/unknown"""
    return str(v).strip() if (v and str(v).strip()) else "/unknown"

def _normalize_feature(v: str | None) -> str:
    """标准化功能模块名，默认DEFAULT，最大长度128"""
    feature = str(v).strip() if (v and str(v).strip()) else "DEFAULT"
    return feature[:128]

def _normalize_title(c: MockApiCandidate) -> str:
    """标准化用例标题（接口名/方法+URL），最大长度100"""
    if c.name and c.name.strip():
        return c.name.strip()[:100]
    return f"{_normalize_method(c.method)} {_normalize_url(c.url)}"[:100]

def _json_to_str(obj: dict | None) -> str:
    """JSON对象转字符串（无缩进，避免中文转义）"""
    return json.dumps(obj or {}, ensure_ascii=False, indent=None)

def _extract_url_vars(url: str) -> list[str]:
    """从URL中提取${变量名}格式的占位符（如${id} -> id）"""
    return re.findall(r"\$\{(\w+)\}", url)

# ===================== 核心逻辑函数 =====================
def _build_preconditions(c: MockApiCandidate) -> dict:
    """
    构建符合规则的前置条件：
    1. dependsOn：从tags提取依赖用例（如tags含"depends=TC001"）
    2. bind：登录接口自动绑定Authorization头和userId参数
    3. vars：URL中的变量自动填充到vars（如URL含${id} -> vars.id=123）
    """
    precond = _DEFAULT_PRECONDITIONS_OBJ.copy()
    
    # 1. 处理依赖用例（示例逻辑：从tags提取depends=TCxxx）
    depends_tag = next((t for t in c.tags if t.startswith("depends=")), None)
    if depends_tag:
        precond["dependsOn"] = [depends_tag.split("=")[1]]
    
    # 2. 处理参数绑定（示例逻辑：登录接口绑定token和userId）
    if "login" in _normalize_title(c).lower():
        precond["bind"] = {
            "headers": {"Authorization": "Bearer ${accessToken}"},  # 绑定请求头
            "params": {"userId": "$.data.userId"}                   # params值为JSONPath
        }
    
    # 3. 处理URL变量（提取${变量名}并设置默认值）
    url_vars = _extract_url_vars(c.url or "")
    if url_vars:
        precond["vars"] = {
            var: 123 if var == "id" else  # id默认123
            "ORD20250101" if var == "orderNo" else  # 订单号默认值
            "" for var in url_vars  # 其他变量默认空字符串
        }
    
    return precond

def _build_postconditions(c: MockApiCandidate) -> dict:
    """
    构建符合规则的后置条件：
    1. asserts：根据状态码调整断言（2xx -> 断言code=0；非2xx -> 断言code!=0）
    2. exports：登录接口导出accessToken和userId（供其他用例绑定）
    """
    postcond = _DEFAULT_POSTCONDITIONS_OBJ.copy()
    expected_code = c.expectedStatusCode or 200
    
    # 1. 调整断言规则（非2xx状态码修改断言逻辑）
    if not (200 <= expected_code <= 299):
        postcond["asserts"] = [{"json": "$.code", "op": "!=", "value": 0}]
    
    # 2. 处理参数导出（登录接口导出token和userId）
    if "login" in _normalize_title(c).lower():
        postcond["exports"] = {
            "accessToken": {"json": "$.data.accessToken"},
            "userId": {"json": "$.data.userId"}
        }
    
    return postcond

def _build_api_params(c: MockApiCandidate) -> str:
    """
    构建符合规则的请求参数：
    - 支持${变量名}占位符（如{"ownerId": "${userId}"}）
    - 变量来源：依赖用例导出参数 > 自定义变量（vars）
    """
    params = c.params.copy()
    
    # 示例：用户接口自动添加${userId}占位符
    if "user" in _normalize_feature(c.feature).lower() and "userId" not in params:
        params["userId"] = "${userId}"
    
    # 示例：登录接口固定使用${adminUser}/${adminPwd}变量
    if "login" in _normalize_title(c).lower():
        params = {"username": "${adminUser}", "password": "${adminPwd}"}
    
    return _json_to_str(params)

def _build_csv_row(c: MockApiCandidate, case_id_prefix: str = "TC") -> dict:
    """将ApiCandidate转换为CSV行数据（所有字段符合规则）"""
    # 处理请求头（POST/PUT自动添加Content-Type）
    headers = c.headers.copy()
    method = _normalize_method(c.method)
    if method in ["POST", "PUT", "PATCH"] and c.params:
        headers.setdefault("Content-Type", "application/json")
    
    # 生成用例ID（示例格式：TC+模块编码+序号，可自定义）
    feature_code = _normalize_feature(c.feature)[:2].upper()
    case_id = f"{case_id_prefix}{feature_code}{str(hash(c.url))[-4:]}"
    
    return {
        "test_case_id": case_id,
        "feature": _normalize_feature(c.feature),
        "title": _normalize_title(c),
        "apiUrl": _normalize_url(c.url),
        "apiMethod": method,
        "apiHeaders": _json_to_str(headers),
        "apiParams": _build_api_params(c),
        "expected_status_code": str(c.expectedStatusCode or 200),
        "expectedResult": _json_to_str(c.expectedResult) if c.expectedResult else '{"code":0}',
        "test_type": "positive" if 200 <= (c.expectedStatusCode or 200) <= 299 else "negative",
        "priority": "P0" if "login" in _normalize_title(c).lower() else "P1",
        "status": "DRAFT",
        "type": "API",
        "preconditions": _json_to_str(_build_preconditions(c)),  # 合规前置条件
        "postconditions": _json_to_str(_build_postconditions(c)),  # 合规后置条件
        "tags": ",".join(c.tags[:5])  # 最多保留5个标签
    }

def build_csv_from_candidates(candidates: Iterable[MockApiCandidate], 
                             prefix: str = "api_test_cases") -> tuple[str, str, int]:
    """从ApiCandidate列表生成CSV文件（返回：文件名、CSV内容、行数）"""
    # 生成CSV行数据
    rows = [_build_csv_row(c) for c in candidates]
    # 生成文件名（含时间戳）
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{prefix}_{timestamp}.csv"
    
    # 写入CSV
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_CSV_FIELDNAMES, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows(rows)
    
    return filename, buf.getvalue(), len(rows)

def build_csv_from_doc_parse(result: MockDocParseResult) -> tuple[str, str, int]:
    """从文档解析结果生成CSV（项目中主要调用此函数）"""
    return build_csv_from_candidates(result.apiCandidates or [])