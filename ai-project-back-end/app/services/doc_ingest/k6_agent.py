from __future__ import annotations

import json
import random
import re
from typing import Any, NotRequired, TypedDict

from app.schemas.doc_ingest import ApiCandidate
from app.services.llm.provider import LlmProvider


class K6AgentInput(TypedDict):
    apiCandidates: list[ApiCandidate]
    docText: str
    instruction: str
    baseUrl: str
    vus: int
    duration: str


class K6AgentOutput(TypedDict):
    scriptText: str
    llm: NotRequired[dict[str, Any]]


class _K6State(TypedDict, total=False):
    apiCandidates: list[ApiCandidate]
    docText: str
    instruction: str
    baseUrl: str
    vus: int
    duration: str
    prompt: str
    scriptText: str
    llm: dict[str, Any]
    attempts: int


def _strip_code_fences(text: str) -> str:
    t = (text or "").strip()
    # 移除 BOM
    if t.startswith("\ufeff"):
        t = t[1:]
    
    # 更加健壮的 Markdown 代码块提取
    # 寻找第一个 ``` 和最后一个 ```
    match = re.search(r"```(?:[a-zA-Z0-9_-]*)\s*(.*?)```", t, re.DOTALL)
    if match:
        return _sanitize_script(match.group(1).strip())
    
    return _sanitize_script(t)


def _sanitize_script(script_text: str) -> str:
    """清理脚本中的非法字符，如全角引号、全角空格、零宽空格等"""
    if not script_text:
        return ""
    
    # 替换常见的全角标点为半角（LLM 有时会混淆）
    s = script_text
    replacements = {
        "\u201c": "\"",  # “
        "\u201d": "\"",  # ”
        "\u2018": "'",   # ‘
        "\u2019": "'",   # ’
        "\uff0c": ",",   # ，
        "\uff1a": ":",   # ：
        "\uff1b": ";",   # ；
        "\uff08": "(",   # （
        "\uff09": ")",   # ）
        "\u3000": " ",   # 全角空格
        "\u00a0": " ",   # Non-breaking space
        "\u200b": "",    # Zero-width space
        "\ufeff": "",    # BOM
    }
    for old, new in replacements.items():
        s = s.replace(old, new)
    
    return s.strip()


def _is_plausible_k6_script(script_text: str) -> bool:
    t = (script_text or "").strip()
    if len(t) < 80:
        return False
    must_have = ["export default function", "http.", "import"]
    if not all(m in t for m in must_have):
        return False
    if "k6/http" not in t:
        return False
    return True


def _sample_candidates(items: list[ApiCandidate], *, max_items: int) -> list[ApiCandidate]:
    if len(items) <= max_items:
        return items
    copy = list(items)
    random.shuffle(copy)
    return copy[:max_items]


def _to_candidate_payload(items: list[ApiCandidate]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for c in items:
        out.append(
            {
                "id": c.id,
                "name": c.name,
                "feature": c.feature,
                "method": c.method,
                "url": c.url,
                "params": c.params,
                "headers": c.headers,
                "expectedStatusCode": c.expectedStatusCode,
                "expectedResult": c.expectedResult,
                "tags": c.tags,
            }
        )
    return out


def _build_system_prompt() -> str:
    return "\n".join(
        [
            "你是一个性能测试工程师，你的任务是把接口文档转换为可运行的 k6 性能测试脚本（JavaScript）。",
            "只输出脚本源码，不要输出解释文字，不要输出 Markdown，不要包含 ``` 代码块围栏。",
            "要求：",
            "1) 脚本必须使用：import http from 'k6/http'；并包含 export const options 与 export default function。",
            "2) BASE_URL 使用 __ENV.BASE_URL 优先，其次使用用户给的 baseUrl 作为默认值。",
            "3) VUS 与 DURATION 使用 __ENV.VUS 与 __ENV.DURATION 优先，其次使用用户给的 vus/duration 作为默认值。",
            "4) 核心要求：根据用户指令（instruction）筛选接口。如果指令提到了具体的接口名称、路径、功能或模块，则只生成对应接口的脚本；如果指令未明确指定或包含“全部”字样，则为所有提供的接口构造请求。",
            "5) 构造请求：",
            "   - GET：把 params 作为 query 参数（如果 params 里包含 path 参数，也要替换到 URL）。",
            "   - POST/PUT/PATCH：默认 JSON body，并自动添加 headers: {'Content-Type': 'application/json'}。",
            "   - headers：合并接口 headers。",
            "6) 处理接口依赖与参数化：",
            "   - 识别登录/认证接口（如 /login, /token 等），从其响应中提取 token（通常在 res.json().token 或 res.json().data.token）。",
            "   - 在后续需要鉴权的请求中，自动添加 headers: {'Authorization': `Bearer ${token}`}，使用提取到的变量。",
            "   - 如果无法提取到动态 token，则允许从 __ENV.TOKEN 注入。",
            "7) 对每次请求做 check：状态码为 2xx，或者候选的 expectedStatusCode。",
            "8) 使用 group() 对接口按 feature 或 name 组织；加入 sleep()。",
            "9) 尽量避免让脚本依赖外部库（只能使用 k6 内置模块）。",
        ]
    )


def _build_user_prompt(state: _K6State) -> str:
    payload = {
        "instruction": state.get("instruction") or "",
        "baseUrl": state.get("baseUrl") or "",
        "vus": int(state.get("vus") or 10),
        "duration": str(state.get("duration") or "30s"),
        "apiCandidates": _to_candidate_payload(_sample_candidates(state.get("apiCandidates") or [], max_items=30)),
        "docText": (state.get("docText") or "")[:12000],
    }
    return json.dumps(payload, ensure_ascii=False)


def _node_build_prompt(state: _K6State) -> _K6State:
    return {**state, "prompt": _build_user_prompt(state), "attempts": int(state.get("attempts") or 0)}


def _node_generate_script(state: _K6State, provider: LlmProvider) -> _K6State:
    system = _build_system_prompt()
    result = provider.chat(prompt=str(state.get("prompt") or ""), system=system, temperature=0.2, max_tokens=2500)
    content = str((result or {}).get("content") or "")
    script = _strip_code_fences(content)
    next_state: _K6State = {**state, "scriptText": script}
    if isinstance(result, dict):
        next_state["llm"] = result
    return next_state


def _node_repair_script(state: _K6State, provider: LlmProvider) -> _K6State:
    attempts = int(state.get("attempts") or 0) + 1
    prev = str(state.get("scriptText") or "")
    system = _build_system_prompt()
    prompt = "\n".join(
        [
            "下面是一段可能不符合要求的输出，请修复为可运行的 k6 脚本。",
            "仍然只输出脚本源码，不要输出解释文字。",
            "",
            "不符合点可能包括：缺少 import/export/options/default function；使用了外部库；包含 Markdown；语法错误。",
            "",
            "原始输出：",
            prev[:20000],
        ]
    )
    result = provider.chat(prompt=prompt, system=system, temperature=0.1, max_tokens=2500)
    content = str((result or {}).get("content") or "")
    script = _strip_code_fences(content)
    next_state: _K6State = {**state, "scriptText": script, "attempts": attempts}
    if isinstance(result, dict):
        next_state["llm"] = result
    return next_state


def generate_k6_script_with_langgraph(
    *,
    provider: LlmProvider,
    api_candidates: list[ApiCandidate],
    doc_text: str,
    instruction: str,
    base_url: str,
    vus: int,
    duration: str,
) -> K6AgentOutput:
    from langgraph.graph import END, StateGraph

    def generate_node(s: _K6State) -> _K6State:
        return _node_generate_script(s, provider)

    def repair_node(s: _K6State) -> _K6State:
        return _node_repair_script(s, provider)

    graph = StateGraph(_K6State)
    graph.add_node("build_prompt", _node_build_prompt)
    graph.add_node("generate", generate_node)
    graph.add_node("repair", repair_node)
    graph.set_entry_point("build_prompt")
    graph.add_edge("build_prompt", "generate")

    def route(s: _K6State) -> str:
        if _is_plausible_k6_script(str(s.get("scriptText") or "")):
            return "end"
        if int(s.get("attempts") or 0) >= 1:
            return "end"
        return "repair"

    graph.add_conditional_edges("generate", route, {"repair": "repair", "end": END})
    graph.add_edge("repair", END)

    app = graph.compile()
    final_state = app.invoke(
        {
            "apiCandidates": list(api_candidates or []),
            "docText": str(doc_text or ""),
            "instruction": str(instruction or ""),
            "baseUrl": str(base_url or ""),
            "vus": int(vus or 10),
            "duration": str(duration or "30s"),
        }
    )
    script_text = str((final_state or {}).get("scriptText") or "")
    output: K6AgentOutput = {"scriptText": script_text}
    llm = (final_state or {}).get("llm")
    if isinstance(llm, dict):
        output["llm"] = llm
    return output


def _infer_needs_auth(c: ApiCandidate) -> bool:
    headers = c.headers or {}
    if any(k.lower() == "authorization" for k in headers.keys()):
        return True
    tags = [str(t or "").lower() for t in (c.tags or [])]
    if any(t in {"auth", "token", "login", "oauth"} for t in tags):
        return True
    name = (c.name or "").lower()
    feature = (c.feature or "").lower()
    if any(w in (name + " " + feature) for w in ["登录", "鉴权", "认证", "token", "auth"]):
        return True
    return False


def generate_k6_script_heuristic(
    *,
    api_candidates: list[ApiCandidate],
    base_url: str,
    vus: int,
    duration: str,
) -> str:
    base_url_default = (base_url or "").strip() or "http://127.0.0.1:8000"
    candidates = [c for c in (api_candidates or []) if (c.method and c.url)]
    candidates = candidates[:20]
    endpoint_cases: list[str] = []

    # 辅助函数：判断是否为登录/认证类接口
    def _is_login_api(c: ApiCandidate) -> bool:
        name = (c.name or "").lower()
        url = (c.url or "").lower()
        tags = [str(t or "").lower() for t in (c.tags or [])]
        return any(w in (name + " " + url) for w in ["login", "signin", "auth", "token", "登录"]) or \
               any(t in {"auth", "login", "token"} for t in tags)

    for idx, c in enumerate(candidates, start=1):
        method = str(c.method or "GET").upper()
        url = str(c.url or "/").strip() or "/"
        expected = int(c.expectedStatusCode or 0)
        needs_auth = _infer_needs_auth(c)
        is_login = _is_login_api(c)
        group_name = (c.feature or c.name or f"api_{idx}").strip()[:60]
        headers_json = json.dumps({k: v for k, v in (c.headers or {}).items() if v is not None}, ensure_ascii=False)
        params_json = json.dumps(c.params or {}, ensure_ascii=False)
        
        case_lines = [
            f"  group({json.dumps(group_name, ensure_ascii=False)}, () => {{",
            f"    const method = {json.dumps(method)};",
            f"    const pathTemplate = {json.dumps(url)};",
            f"    const params = {params_json};",
            f"    const baseHeaders = {headers_json};",
            f"    const needsAuth = {str(needs_auth).lower()};",
            f"    const expectedStatus = {expected if expected else 'null'};",
            "    const request = buildRequest({ baseUrl: BASE_URL, method, pathTemplate, params, baseHeaders, needsAuth, token });",
            "    const res = http.request(request.method, request.url, request.body, { headers: request.headers, tags: request.tags });",
        ]
        
        if is_login:
            case_lines.append("    if (res.status >= 200 && res.status < 300) {")
            case_lines.append("      const body = res.json();")
            case_lines.append("      const newToken = body.token || (body.data && body.data.token) || body.access_token || (body.data && body.data.access_token);")
            case_lines.append("      if (newToken) { token = newToken; }")
            case_lines.append("    }")

        case_lines.extend([
            "    check(res, {",
            "      'status is expected': (r) => {",
            "        if (expectedStatus) return r.status === expectedStatus;",
            "        return r.status >= 200 && r.status < 300;",
            "      },",
            "    });",
            "    sleep(0.2);",
            "  });",
        ])
        endpoint_cases.append("\n".join(case_lines))

    script = "\n".join(
        [
            "import http from 'k6/http';",
            "import { check, group, sleep } from 'k6';",
            "",
            f"const DEFAULT_BASE_URL = {json.dumps(base_url_default)};",
            f"const DEFAULT_VUS = {int(vus or 10)};",
            f"const DEFAULT_DURATION = {json.dumps(str(duration or '30s'))};",
            "",
            "export const options = {",
            "  vus: __ENV.VUS ? parseInt(__ENV.VUS, 10) : DEFAULT_VUS,",
            "  duration: __ENV.DURATION || DEFAULT_DURATION,",
            "};",
            "",
            "const BASE_URL = (__ENV.BASE_URL || DEFAULT_BASE_URL).replace(/\\/+$/, '');",
            "",
            "function applyPathParams(pathTemplate, params) {",
            "  let path = String(pathTemplate || '/');",
            "  const used = new Set();",
            "  path = path.replace(/\\{([^}]+)\\}/g, (_, key) => {",
            "    const k = String(key);",
            "    used.add(k);",
            "    const v = params && Object.prototype.hasOwnProperty.call(params, k) ? params[k] : 1;",
            "    return encodeURIComponent(String(v));",
            "  });",
            "  return { path, used };",
            "}",
            "",
            "function buildQuery(params, used) {",
            "  const pairs = [];",
            "  if (!params || typeof params !== 'object') return '';",
            "  for (const k in params) {",
            "    if (!Object.prototype.hasOwnProperty.call(params, k)) continue;",
            "    if (used && used.has(k)) continue;",
            "    const v = params[k];",
            "    if (v === undefined || v === null) continue;",
            "    pairs.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);",
            "  }",
            "  return pairs.length ? `?${pairs.join('&')}` : '';",
            "}",
            "",
            "function buildRequest({ baseUrl, method, pathTemplate, params, baseHeaders, needsAuth, token }) {",
            "  const { path, used } = applyPathParams(pathTemplate, params || {});",
            "  const upper = String(method || 'GET').toUpperCase();",
            "  const qs = upper === 'GET' || upper === 'DELETE' ? buildQuery(params || {}, used) : '';",
            "  const url = `${baseUrl}${path}${qs}`;",
            "  const headers = Object.assign({}, baseHeaders || {});",
            "  if (needsAuth) {",
            "    const finalToken = token || __ENV.TOKEN || '';",
            "    if (finalToken && !headers.Authorization && !headers.authorization) {",
            "      headers.Authorization = `Bearer ${finalToken}`;",
            "    }",
            "  }",
            "  let body = null;",
            "  if (upper !== 'GET' && upper !== 'DELETE') {",
            "    if (!headers['Content-Type'] && !headers['content-type']) {",
            "      headers['Content-Type'] = 'application/json';",
            "    }",
            "    body = JSON.stringify(params || {});",
            "  }",
            "  return { method: upper, url, headers, body, tags: { name: pathTemplate } };",
            "}",
            "",
            "export default function () {",
            "  let token = '';",
            *endpoint_cases,
            "}",
            "",
        ]
    )
    return _sanitize_script(script)
