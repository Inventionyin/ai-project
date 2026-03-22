from __future__ import annotations

import json
import platform
import re
import subprocess
import tempfile
import time
import zipfile
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from app.core.config import get_settings
from app.models.enums import ArtifactType, CaseRunStatus, JobStatus
from app.schemas.run import ArtifactIndex, CaseRunMetrics, CaseRunResult
from app.schemas.worker import JobPayload

_SENSITIVE_HEADER_KEYS = {
    "authorization",
    "proxy-authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "x-auth-token",
}


def _mask_sensitive_headers(headers: dict[str, str]) -> dict[str, str]:
    masked: dict[str, str] = {}
    for key, value in headers.items():
        if str(key).strip().lower() in _SENSITIVE_HEADER_KEYS:
            masked[str(key)] = "******"
        else:
            masked[str(key)] = str(value)
    return masked


def _default_runner_root() -> Path:
    settings = get_settings()
    configured = str(settings.runner_workspace_root or "").strip()
    if configured:
        return Path(configured).expanduser()
    if platform.system().strip().lower().startswith("win"):
        return Path("D:/ai-test-platform-runners")
    return Path(tempfile.gettempdir()) / "ai-test-platform-runners"


def _resolve_allure_runs_root() -> Path:
    settings = get_settings()
    configured = str(settings.runner_allure_runs_root or "").strip()
    if configured:
        return Path(configured).expanduser()
    return _default_runner_root() / "allure-data" / "runs"


def _job_item_key(item: object) -> str:
    test_case_id = getattr(item, "testCaseId", None)
    if isinstance(test_case_id, str) and test_case_id.strip():
        return test_case_id.strip()
    testcase_id = getattr(item, "testcaseId", None)
    if isinstance(testcase_id, str) and testcase_id.strip():
        return testcase_id.strip()
    case_run_id = getattr(item, "caseRunId", None)
    if isinstance(case_run_id, str) and case_run_id.strip():
        return case_run_id.strip()
    raise ValueError("job_item_key_empty")


def _parse_condition_json(text: str | None, *, field_name: str, case_key: str) -> dict[str, object] | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if parsed is None:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _extract_depends_on(preconditions: dict[str, object] | None) -> list[str]:
    if not preconditions:
        return []
    value = preconditions.get("dependsOn")
    if value is None:
        return []
    if isinstance(value, str):
        deps = [value.strip()] if value.strip() else []
    elif isinstance(value, list):
        deps = [str(v).strip() for v in value if str(v).strip()]
    else:
        return []
    deduped: list[str] = []
    seen: set[str] = set()
    for dep in deps:
        if dep in seen:
            continue
        seen.add(dep)
        deduped.append(dep)
    return deduped


def _order_job_items(items: Sequence[object]) -> list[object]:
    nodes: dict[str, object] = {}
    original_order: dict[str, int] = {}
    for index, item in enumerate(items):
        key = _job_item_key(item)
        if key in nodes:
            raise ValueError(f"duplicate_case_key:{key}")
        nodes[key] = item
        original_order[key] = index

    deps_map: dict[str, list[str]] = {}
    for key, item in nodes.items():
        pre = _parse_condition_json(getattr(item, "preconditions", None), field_name="preconditions", case_key=key)
        deps = _extract_depends_on(pre)
        deps_map[key] = deps

    in_degree: dict[str, int] = {k: 0 for k in nodes.keys()}
    outgoing: dict[str, list[str]] = defaultdict(list)
    for key, deps in deps_map.items():
        for dep in deps:
            if dep not in nodes:
                continue
            outgoing[dep].append(key)
            in_degree[key] += 1

    def _order_no(k: str) -> tuple[int, int]:
        item = nodes[k]
        raw = getattr(item, "orderNo", None)
        try:
            return int(raw), original_order.get(k, 0)
        except Exception:
            return 0, original_order.get(k, 0)

    ready = deque(sorted([k for k, d in in_degree.items() if d == 0], key=_order_no))
    ordered: list[str] = []
    while ready:
        k = ready.popleft()
        ordered.append(k)
        for nxt in sorted(outgoing.get(k, []), key=_order_no):
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                ready.append(nxt)

    if len(ordered) != len(nodes):
        remaining = sorted([k for k, d in in_degree.items() if d > 0], key=_order_no)
        ordered.extend([k for k in remaining if k not in ordered])

    return [nodes[k] for k in ordered]


@dataclass(frozen=True, slots=True)
class PytestAllureExecutionOutput:
    job_status: JobStatus
    results: list[CaseRunResult]
    workspace: Path


@dataclass(frozen=True, slots=True)
class _GeneratedCase:
    case_run_id: str
    case_key: str
    test_file: Path


@dataclass(frozen=True, slots=True)
class _CaseExecutionOutput:
    case_run_id: str
    status: CaseRunStatus
    start_ts: int
    end_ts: int
    return_code: int
    stdout: str
    stderr: str
    error_message: str


@dataclass(frozen=True, slots=True)
class AllureGenerateOutput:
    report_dir: Path | None
    stdout: str
    stderr: str
    error_code: str | None


def resolve_run_allure_paths(run_id: str) -> tuple[Path, Path]:
    run_key = str(run_id).strip()
    if not run_key:
        raise ValueError("run_id_empty")
    run_root = _resolve_allure_runs_root() / run_key
    return run_root / "allure-results", run_root / "allure-report"


class PytestAllureRunnerService:
    def __init__(
        self,
        *,
        workspace_root: Path | None = None,
        python_executable: str = "python",
        allure_command: str = "allure",
    ) -> None:
        self._workspace_root = workspace_root
        self._python_executable = python_executable
        self._allure_command = allure_command

    def execute(self, job: JobPayload) -> PytestAllureExecutionOutput:
        workspace, generated_cases = self._prepare_workspace(job)
        allure_results_dir, allure_report_dir = resolve_run_allure_paths(job.runId)
        self._prepare_allure_metadata(job=job, allure_results_dir=allure_results_dir)
        execution_log = workspace / "execution.log"
        timeout_sec = max(int(job.suiteConfig.timeoutSec), 1)
        logs: list[str] = []
        case_outputs = self._run_pytest_once(
            workspace=workspace,
            generated_cases=generated_cases,
            allure_results_dir=allure_results_dir,
            timeout_sec=timeout_sec,
        )
        logs.append(self._format_pytest_execution_log(case_outputs=case_outputs))
        report_output = self._generate_allure_report(
            allure_results_dir=allure_results_dir,
            report_dir=allure_report_dir,
            timeout_sec=timeout_sec,
        )
        if report_output.error_code:
            logs.append(
                "\n".join(
                    [
                        f"[allureGenerate] errorCode={report_output.error_code}",
                        report_output.stdout,
                        report_output.stderr,
                    ]
                ).strip()
            )
        execution_log.write_text("\n\n".join(logs).strip(), encoding="utf-8")
        allure_zip = self._zip_allure_results(allure_results_dir)
        allure_report_zip = self._zip_allure_report(report_output.report_dir)
        artifacts = self._build_artifacts(execution_log, allure_zip, allure_report_zip)
        results = self._build_case_results(case_outputs=case_outputs, artifacts=artifacts)
        job_status = JobStatus.DONE if all(item.status != CaseRunStatus.FAILED for item in case_outputs) else JobStatus.FAILED
        return PytestAllureExecutionOutput(job_status=job_status, results=results, workspace=workspace)

    def generate_report_for_run(self, run_id: str, *, timeout_sec: int) -> AllureGenerateOutput:
        allure_results_dir, allure_report_dir = resolve_run_allure_paths(run_id)
        return self._generate_allure_report(
            allure_results_dir=allure_results_dir,
            report_dir=allure_report_dir,
            timeout_sec=max(int(timeout_sec), 1),
        )

    def _prepare_workspace(self, job: JobPayload) -> tuple[Path, list[_GeneratedCase]]:
        root = self._workspace_root
        if root is None:
            if platform.system().strip().lower().startswith("win"):
                root = Path("D:/ai-test-platform-runners")
            else:
                root = Path(tempfile.gettempdir()) / "ai-test-platform-runners"
        root.mkdir(parents=True, exist_ok=True)
        workspace = Path(tempfile.mkdtemp(prefix=f"job-{job.jobId}-", dir=root))
        tests_dir = workspace / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        ordered_items = _order_job_items(job.items)
        params_path = workspace / "job-params.json"
        params_path.write_text(
            json.dumps(
                {
                    "jobId": job.jobId,
                    "runId": job.runId,
                    "env": job.env.model_dump(mode="json"),
                    "items": [item.model_dump(mode="json") for item in ordered_items],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        generated_cases: list[_GeneratedCase] = []
        for index, item in enumerate(ordered_items, start=1):
            test_file = tests_dir / f"test_case_{index:04d}_{item.caseRunId.replace('-', '_')}.py"
            method = str(item.apiMethod or "GET").strip().upper() or "GET"
            api_url = str(item.apiUrl or "").strip()
            headers = {str(k): str(v) for k, v in dict(item.headers or {}).items()}
            masked_headers = _mask_sensitive_headers(headers)
            case_key = _job_item_key(item)
            test_file.write_text(
                "\n".join(
                    [
                        "import json",
                        "import re",
                        "from pathlib import Path",
                        "from urllib.parse import urljoin",
                        "import allure",
                        "import pytest",
                        "import requests",
                        "",
                        f"CASE_KEY = {json.dumps(case_key, ensure_ascii=False)}",
                        f"PRECONDITIONS_RAW = {json.dumps(str(item.preconditions or '').strip(), ensure_ascii=False)}",
                        f"POSTCONDITIONS_RAW = {json.dumps(str(item.postconditions or '').strip(), ensure_ascii=False)}",
                        f"ENV_VARS = {json.dumps(dict(job.env.variables or {}), ensure_ascii=False)}",
                        "CTX_PATH = Path(__file__).resolve().parent.parent / 'context.json'",
                        "VAR_RE = re.compile(r'\\$\\{([A-Za-z_][A-Za-z0-9_\\.-]*)\\}')",
                        "SENSITIVE_HEADER_KEYS = {'authorization','proxy-authorization','cookie','set-cookie','x-api-key','x-auth-token'}",
                        "",
                        "def _mask_headers(headers):",
                        "    masked = {}",
                        "    for k, v in dict(headers or {}).items():",
                        "        kk = str(k).strip()",
                        "        if kk.lower() in SENSITIVE_HEADER_KEYS:",
                        "            masked[kk] = '******'",
                        "        else:",
                        "            masked[kk] = '' if v is None else str(v)",
                        "    return masked",
                        "",
                        "def _load_ctx():",
                        "    if not CTX_PATH.exists():",
                        "        return {'vars': {}, 'status': {}}",
                        "    try:",
                        "        data = json.loads(CTX_PATH.read_text(encoding='utf-8') or '{}')",
                        "    except Exception:",
                        "        data = {}",
                        "    if not isinstance(data, dict):",
                        "        data = {}",
                        "    data.setdefault('vars', {})",
                        "    data.setdefault('status', {})",
                        "    if not isinstance(data['vars'], dict):",
                        "        data['vars'] = {}",
                        "    if not isinstance(data['status'], dict):",
                        "        data['status'] = {}",
                        "    return data",
                        "",
                        "def _save_ctx(ctx):",
                        "    CTX_PATH.write_text(json.dumps(ctx, ensure_ascii=False, indent=2), encoding='utf-8')",
                        "",
                        "def _parse_obj(raw, name):",
                        "    text = str(raw or '').strip()",
                        "    if not text:",
                        "        return {}",
                        "    try:",
                        "        val = json.loads(text)",
                        "    except Exception:",
                        "        return {}",
                        "    if val is None:",
                        "        return {}",
                        "    if not isinstance(val, dict):",
                        "        return {}",
                        "    return val",
                        "",
                        "def _collect_vars(value):",
                        "    found = set()",
                        "    if isinstance(value, str):",
                        "        for m in VAR_RE.finditer(value):",
                        "            found.add(m.group(1))",
                        "        return found",
                        "    if isinstance(value, dict):",
                        "        for v in value.values():",
                        "            found |= _collect_vars(v)",
                        "        return found",
                        "    if isinstance(value, list):",
                        "        for v in value:",
                        "            found |= _collect_vars(v)",
                        "        return found",
                        "    return found",
                        "",
                        "def _lookup(name, ctx):",
                        "    if str(name).startswith('env.'):",
                        "        return ENV_VARS.get(str(name)[4:])",
                        "    return ctx['vars'].get(str(name))",
                        "",
                        "def _render(value, ctx):",
                        "    if isinstance(value, str):",
                        "        m = VAR_RE.fullmatch(value)",
                        "        if m:",
                        "            return _lookup(m.group(1), ctx)",
                        "        def _repl(mm):",
                        "            v = _lookup(mm.group(1), ctx)",
                        "            return '' if v is None else str(v)",
                        "        return VAR_RE.sub(_repl, value)",
                        "    if isinstance(value, dict):",
                        "        return {k: _render(v, ctx) for k, v in value.items()}",
                        "    if isinstance(value, list):",
                        "        return [_render(v, ctx) for v in value]",
                        "    return value",
                        "",
                        "def _json_get(obj, path):",
                        "    p = str(path or '').strip()",
                        "    if p in ('$', ''):",
                        "        return obj",
                        "    if not p.startswith('$.'):",
                        "        raise AssertionError('JSON_PATH_INVALID')",
                        "    cur = obj",
                        "    for part in p[2:].split('.'):",
                        "        if not part:",
                        "            continue",
                        "        key = part",
                        "        idx = None",
                        "        if '[' in part and part.endswith(']'):",
                        "            key, idx_s = part[:-1].split('[', 1)",
                        "            idx = int(idx_s)",
                        "        if key:",
                        "            if not isinstance(cur, dict) or key not in cur:",
                        "                return None",
                        "            cur = cur.get(key)",
                        "        if idx is not None:",
                        "            if not isinstance(cur, list) or idx < 0 or idx >= len(cur):",
                        "                return None",
                        "            cur = cur[idx]",
                        "    return cur",
                        "",
                        "def _assert_op(left, op, right):",
                        "    o = str(op or '').strip().lower()",
                        "    if o in ('==', 'eq'):",
                        "        assert left == right, f'ASSERT_EQ_FAIL:{left}!={right}'",
                        "    elif o in ('!=', 'ne'):",
                        "        assert left != right, f'ASSERT_NE_FAIL:{left}=={right}'",
                        "    elif o == 'contains':",
                        "        assert right in left, 'ASSERT_CONTAINS_FAIL'",
                        "    else:",
                        "        raise AssertionError(f'ASSERT_OP_UNSUPPORTED:{op}')",
                        "",
                        f"@allure.title('Case {item.caseRunId}')",
                        f"def test_case_{index:04d}():",
                        "    ctx = _load_ctx()",
                        "    pre = _parse_obj(PRECONDITIONS_RAW, 'PRECONDITIONS')",
                        "    post = _parse_obj(POSTCONDITIONS_RAW, 'POSTCONDITIONS')",
                        f"    method = {json.dumps(method, ensure_ascii=False)}",
                        f"    api_url = {json.dumps(api_url, ensure_ascii=False)}",
                        f"    base_url = {json.dumps(str(job.env.baseUrl or ''), ensure_ascii=False)}",
                        f"    params = {json.dumps(dict(item.params or {}), ensure_ascii=False)}",
                        f"    headers = {json.dumps(headers, ensure_ascii=False)}",
                        f"    expected_result = {json.dumps(str(item.expectedResult or '').strip(), ensure_ascii=False)}",
                        f"    expected_status_code = {json.dumps(int(item.expectedStatusCode) if item.expectedStatusCode is not None else None, ensure_ascii=False)}",
                        "    try:",
                        "        assert api_url",
                        "        depends = pre.get('dependsOn') or []",
                        "        if isinstance(depends, str):",
                        "            depends = [depends]",
                        "        if not isinstance(depends, list):",
                        "            raise AssertionError('PRECONDITIONS_DEPENDS_ON_INVALID')",
                        "        for dep in [str(x).strip() for x in depends if str(x).strip()]:",
                        "            dep_status = ctx['status'].get(dep)",
                        "            if dep_status is None:",
                        "                ctx['status'][CASE_KEY] = 'SKIPPED'",
                        "                _save_ctx(ctx)",
                        "                pytest.skip(f'DEP_NOT_FOUND:{dep}')",
                        "            if str(dep_status or '').upper() != 'PASSED':",
                        "                ctx['status'][CASE_KEY] = 'SKIPPED'",
                        "                _save_ctx(ctx)",
                        "                pytest.skip(f'BLOCKED_BY:{dep}')",
                        "        requires = pre.get('requires') or []",
                        "        if isinstance(requires, str):",
                        "            requires = [requires]",
                        "        if not isinstance(requires, list):",
                        "            raise AssertionError('PRECONDITIONS_REQUIRES_INVALID')",
                        "        for name in [str(x).strip() for x in requires if str(x).strip()]:",
                        "            if _lookup(name, ctx) is None:",
                        "                ctx['status'][CASE_KEY] = 'SKIPPED'",
                        "                _save_ctx(ctx)",
                        "                pytest.skip(f'MISSING_VAR:{name}')",
                        "        bind = pre.get('bind') or {}",
                        "        if bind and not isinstance(bind, dict):",
                        "            raise AssertionError('PRECONDITIONS_BIND_INVALID')",
                        "        params_final = dict(params or {})",
                        "        headers_final = dict(headers or {})",
                        "        if isinstance(bind.get('params'), dict):",
                        "            params_final.update(bind.get('params') or {})",
                        "        if isinstance(bind.get('headers'), dict):",
                        "            headers_final.update(bind.get('headers') or {})",
                        "        used_vars = _collect_vars(api_url) | _collect_vars(params_final) | _collect_vars(headers_final)",
                        "        missing_vars = [v for v in sorted(used_vars) if _lookup(v, ctx) is None]",
                        "        if missing_vars:",
                        "            ctx['status'][CASE_KEY] = 'SKIPPED'",
                        "            _save_ctx(ctx)",
                        "            pytest.skip('MISSING_VAR:' + ','.join(missing_vars[:20]))",
                        "        api_url_rendered = _render(api_url, ctx)",
                        "        api_url_rendered = '' if api_url_rendered is None else str(api_url_rendered)",
                        "        params_final = _render(params_final, ctx)",
                        "        headers_final = _render(headers_final, ctx)",
                        "        full_url = api_url_rendered if api_url_rendered.startswith(('http://', 'https://')) else urljoin(base_url.rstrip('/') + '/', api_url_rendered.lstrip('/'))",
                        "        allure.attach(json.dumps({'method': method, 'url': full_url, 'params': params_final, 'headers': _mask_headers(headers_final)}, ensure_ascii=False, indent=2), 'request', allure.attachment_type.JSON)",
                        "        try:",
                        "            if method in ('GET', 'DELETE', 'HEAD', 'OPTIONS'):",
                        "                response = requests.request(method=method, url=full_url, params=params_final, headers=headers_final, timeout=30)",
                        "            else:",
                        "                response = requests.request(method=method, url=full_url, json=params_final, headers=headers_final, timeout=30)",
                        "        except requests.exceptions.Timeout as exc:",
                        "            allure.attach(str(exc), 'request_error', allure.attachment_type.TEXT)",
                        "            raise AssertionError('REQUEST_TIMEOUT') from exc",
                        "        except requests.exceptions.ConnectionError as exc:",
                        "            allure.attach(str(exc), 'request_error', allure.attachment_type.TEXT)",
                        "            raise AssertionError('REQUEST_CONNECTION_ERROR') from exc",
                        "        except requests.exceptions.RequestException as exc:",
                        "            allure.attach(str(exc), 'request_error', allure.attachment_type.TEXT)",
                        "            raise AssertionError('REQUEST_ERROR') from exc",
                        "        allure.attach(str(response.status_code), 'response_status', allure.attachment_type.TEXT)",
                        "        allure.attach(response.text[:20000], 'response_body', allure.attachment_type.TEXT)",
                        "        if expected_status_code is not None:",
                        "            assert int(response.status_code) == int(expected_status_code), f'HTTP_ASSERT_FAIL:{response.status_code}'",
                        "        else:",
                        "            assert 200 <= int(response.status_code) < 400, f'HTTP_ASSERT_FAIL:{response.status_code}'",
                        "        if expected_result:",
                        "            assert expected_result in response.text, 'EXPECTED_RESULT_NOT_FOUND'",
                        "        try:",
                        "            response_json = response.json()",
                        "        except Exception:",
                        "            response_json = None",
                        "        asserts = post.get('asserts') or []",
                        "        if isinstance(asserts, dict):",
                        "            asserts = [asserts]",
                        "        if asserts and not isinstance(asserts, list):",
                        "            raise AssertionError('POSTCONDITIONS_ASSERTS_INVALID')",
                        "        for a in asserts:",
                        "            if not isinstance(a, dict):",
                        "                raise AssertionError('POSTCONDITIONS_ASSERT_ITEM_INVALID')",
                        "            left = _json_get(response_json, a.get('json')) if a.get('json') else None",
                        "            right = _render(a.get('value'), ctx)",
                        "            _assert_op(left, a.get('op'), right)",
                        "        exports = post.get('exports') or {}",
                        "        if exports and not isinstance(exports, dict):",
                        "            raise AssertionError('POSTCONDITIONS_EXPORTS_INVALID')",
                        "        for name, rule in exports.items():",
                        "            if not str(name).strip():",
                        "                continue",
                        "            if isinstance(rule, str):",
                        "                rule = {'json': rule}",
                        "            if not isinstance(rule, dict):",
                        "                raise AssertionError('POSTCONDITIONS_EXPORT_ITEM_INVALID')",
                        "            if rule.get('json'):",
                        "                ctx['vars'][str(name)] = _json_get(response_json, rule.get('json'))",
                        "        ctx['status'][CASE_KEY] = 'PASSED'",
                        "        _save_ctx(ctx)",
                        "    except pytest.skip.Exception:",
                        "        raise",
                        "    except Exception:",
                        "        ctx['status'][CASE_KEY] = 'FAILED'",
                        "        _save_ctx(ctx)",
                        "        raise",
                    ]
                ),
                encoding="utf-8",
            )
            generated_cases.append(_GeneratedCase(case_run_id=item.caseRunId, case_key=case_key, test_file=test_file))
        return workspace, generated_cases

    def _run_pytest_once(
        self,
        *,
        workspace: Path,
        generated_cases: list[_GeneratedCase],
        allure_results_dir: Path,
        timeout_sec: int,
    ) -> list[_CaseExecutionOutput]:
        run_start = int(time.time())
        pytest_cmd: Sequence[str] = (
            self._python_executable,
            "-m",
            "pytest",
            "tests",
            f"--alluredir={allure_results_dir}",
            "-q",
        )
        error_message = ""
        total_timeout_sec = max(int(timeout_sec), 1) * max(len(generated_cases), 1)
        try:
            completed = subprocess.run(
                pytest_cmd,
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=total_timeout_sec,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            completed = subprocess.CompletedProcess(
                args=pytest_cmd,
                returncode=1,
                stdout=(exc.stdout or ""),
                stderr=(exc.stderr or ""),
            )
            error_message = "pytest_timeout"
        except FileNotFoundError:
            completed = subprocess.CompletedProcess(
                args=pytest_cmd,
                returncode=1,
                stdout="",
                stderr=f"{self._python_executable} not found",
            )
            error_message = "pytest_cli_not_found"
        run_end = int(time.time())

        ctx_status_map = self._load_ctx_status_map(workspace)
        allure_map = self._load_allure_case_results(allure_results_dir)
        suite_stdout = str(completed.stdout or "")
        suite_stderr = str(completed.stderr or "")
        fallback_message = (suite_stderr or suite_stdout).strip()[:2000]

        case_outputs: list[_CaseExecutionOutput] = []
        for generated in generated_cases:
            status = self._resolve_case_status(
                case_key=generated.case_key,
                case_run_id=generated.case_run_id,
                ctx_status_map=ctx_status_map,
                allure_map=allure_map,
            )
            start_ts, end_ts = self._resolve_case_timestamps(
                case_run_id=generated.case_run_id,
                allure_map=allure_map,
                fallback_start_ts=run_start,
                fallback_end_ts=run_end,
            )
            details_message = ""
            if status in (CaseRunStatus.FAILED, CaseRunStatus.SKIPPED):
                details_message = self._resolve_case_error_message(
                    case_run_id=generated.case_run_id,
                    allure_map=allure_map,
                    fallback_message=fallback_message if status == CaseRunStatus.FAILED else "",
                )
            case_error_message = error_message or details_message if status == CaseRunStatus.FAILED else ""
            case_outputs.append(
                _CaseExecutionOutput(
                    case_run_id=generated.case_run_id,
                    status=status,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    return_code=0 if status != CaseRunStatus.FAILED else 1,
                    stdout="",
                    stderr=details_message,
                    error_message=case_error_message,
                )
            )

        if any(item.status == CaseRunStatus.FAILED and not item.error_message for item in case_outputs) and fallback_message:
            case_outputs = [
                _CaseExecutionOutput(
                    case_run_id=item.case_run_id,
                    status=item.status,
                    start_ts=item.start_ts,
                    end_ts=item.end_ts,
                    return_code=item.return_code,
                    stdout=item.stdout,
                    stderr=item.stderr,
                    error_message=fallback_message if item.status == CaseRunStatus.FAILED else item.error_message,
                )
                for item in case_outputs
            ]

        return case_outputs

    def _format_pytest_execution_log(self, *, case_outputs: list[_CaseExecutionOutput]) -> str:
        total = len(case_outputs)
        passed = sum(1 for item in case_outputs if item.status == CaseRunStatus.PASSED)
        failed = sum(1 for item in case_outputs if item.status == CaseRunStatus.FAILED)
        skipped = sum(1 for item in case_outputs if item.status == CaseRunStatus.SKIPPED)
        return f"[pytest] total={total} passed={passed} failed={failed} skipped={skipped}"

    def _load_ctx_status_map(self, workspace: Path) -> dict[str, str]:
        path = workspace / "context.json"
        if not path.exists():
            return {}
        try:
            raw = json.loads(path.read_text(encoding="utf-8") or "{}")
        except Exception:
            return {}
        if not isinstance(raw, dict):
            return {}
        status = raw.get("status")
        if not isinstance(status, dict):
            return {}
        return {str(k): str(v) for k, v in status.items() if str(k).strip()}

    def _load_allure_case_results(self, allure_results_dir: Path) -> dict[str, dict[str, object]]:
        if not allure_results_dir.exists():
            return {}
        out: dict[str, dict[str, object]] = {}
        uuid_re = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
        uuid_u_re = re.compile(r"\b[0-9a-f]{8}_[0-9a-f]{4}_[0-9a-f]{4}_[0-9a-f]{4}_[0-9a-f]{12}\b", re.I)
        for child in allure_results_dir.glob("*-result.json"):
            if not child.is_file():
                continue
            try:
                data = json.loads(child.read_text(encoding="utf-8") or "{}")
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            name = str(data.get("name") or "")
            full_name = str(data.get("fullName") or "")
            combined = f"{name}\n{full_name}"
            case_run_id = ""
            m = uuid_re.search(combined)
            if m:
                case_run_id = m.group(0)
            if not case_run_id:
                m2 = uuid_u_re.search(combined)
                if m2:
                    candidate = m2.group(0).replace("_", "-")
                    if uuid_re.fullmatch(candidate):
                        case_run_id = candidate
            if not case_run_id:
                continue
            out[case_run_id] = data
        return out

    def _resolve_case_status(
        self,
        *,
        case_key: str,
        case_run_id: str,
        ctx_status_map: dict[str, str],
        allure_map: dict[str, dict[str, object]],
    ) -> CaseRunStatus:
        raw = str(ctx_status_map.get(case_key) or "").strip().upper()
        if raw == "PASSED":
            return CaseRunStatus.PASSED
        if raw == "FAILED":
            return CaseRunStatus.FAILED
        if raw == "SKIPPED":
            return CaseRunStatus.SKIPPED
        allure_row = allure_map.get(case_run_id) or {}
        allure_status = str(allure_row.get("status") or "").strip().lower()
        if allure_status == "passed":
            return CaseRunStatus.PASSED
        if allure_status in ("skipped", "canceled"):
            return CaseRunStatus.SKIPPED
        if allure_status in ("failed", "broken"):
            return CaseRunStatus.FAILED
        return CaseRunStatus.FAILED

    def _resolve_case_timestamps(
        self,
        *,
        case_run_id: str,
        allure_map: dict[str, dict[str, object]],
        fallback_start_ts: int,
        fallback_end_ts: int,
    ) -> tuple[int, int]:
        row = allure_map.get(case_run_id) or {}
        start = row.get("start")
        stop = row.get("stop")
        start_s = self._normalize_epoch_ts(start, fallback=fallback_start_ts)
        stop_s = self._normalize_epoch_ts(stop, fallback=fallback_end_ts)
        if stop_s < start_s:
            stop_s = start_s
        return start_s, stop_s

    def _normalize_epoch_ts(self, value: object, *, fallback: int) -> int:
        try:
            ts = int(value)  # type: ignore[arg-type]
        except Exception:
            return int(fallback)
        if ts <= 0:
            return int(fallback)
        if ts > 1_000_000_000_000:
            return int(ts // 1000)
        return int(ts)

    def _resolve_case_error_message(
        self,
        *,
        case_run_id: str,
        allure_map: dict[str, dict[str, object]],
        fallback_message: str,
    ) -> str:
        row = allure_map.get(case_run_id) or {}
        details = row.get("statusDetails")
        if isinstance(details, dict):
            message = str(details.get("message") or "").strip()
            trace = str(details.get("trace") or "").strip()
            combined = "\n".join([x for x in [message, trace] if x]).strip()
            if combined:
                return combined[:2000]
        return (fallback_message or "").strip()[:2000]

    def _prepare_allure_metadata(self, *, job: JobPayload, allure_results_dir: Path) -> None:
        allure_results_dir.mkdir(parents=True, exist_ok=True)
        env_lines = [
            f"baseUrl={job.env.baseUrl}",
            f"runId={job.runId}",
            f"jobId={job.jobId}",
            f"timeoutSec={int(job.suiteConfig.timeoutSec)}",
            f"retryCount={int(job.suiteConfig.retryCount)}",
            f"host={platform.node() or 'unknown'}",
            f"os={platform.system()} {platform.release()}".strip(),
            f"python={platform.python_version()}",
        ]
        for key in sorted(job.env.variables.keys()):
            env_lines.append(f"env.{key}={job.env.variables[key]}")
        (allure_results_dir / "environment.properties").write_text("\n".join(env_lines) + "\n", encoding="utf-8")
        executor_payload = {
            "name": "AI Testing Platform",
            "type": "pytest",
            "buildName": f"Run {job.runId}",
            "buildOrder": int(time.time()),
            "reportName": f"Allure Report - {job.runId}",
        }
        (allure_results_dir / "executor.json").write_text(
            json.dumps(executor_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _zip_allure_results(self, allure_results_dir: Path) -> Path | None:
        if not allure_results_dir.exists():
            return None
        zip_path = allure_results_dir.parent / "allure-results.zip"
        with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for child in allure_results_dir.rglob("*"):
                if child.is_file():
                    zf.write(child, child.relative_to(allure_results_dir.parent))
        return zip_path

    def _zip_allure_report(self, report_dir: Path | None) -> Path | None:
        if report_dir is None or not report_dir.exists():
            return None
        zip_path = report_dir.parent / "allure-report.zip"
        with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for child in report_dir.rglob("*"):
                if child.is_file():
                    zf.write(child, child.relative_to(report_dir.parent))
        return zip_path

    def _generate_allure_report(
        self,
        *,
        allure_results_dir: Path,
        report_dir: Path,
        timeout_sec: int,
    ) -> AllureGenerateOutput:
        if not allure_results_dir.exists():
            return AllureGenerateOutput(report_dir=None, stdout="", stderr="", error_code="allure_results_not_found")
        report_dir.parent.mkdir(parents=True, exist_ok=True)
        try:
            completed = subprocess.run(
                [
                    self._allure_command,
                    "generate",
                    str(allure_results_dir),
                    "-o",
                    str(report_dir),
                    "--clean",
                ],
                cwd=report_dir.parent,
                capture_output=True,
                text=True,
                timeout=max(timeout_sec, 1),
                check=False,
            )
        except FileNotFoundError:
            return AllureGenerateOutput(
                report_dir=None,
                stdout="",
                stderr=f"{self._allure_command} not found",
                error_code="allure_cli_not_found",
            )
        except subprocess.TimeoutExpired as exc:
            return AllureGenerateOutput(
                report_dir=None,
                stdout=str(exc.stdout or ""),
                stderr=str(exc.stderr or ""),
                error_code="allure_generate_timeout",
            )
        if int(completed.returncode) != 0:
            return AllureGenerateOutput(
                report_dir=None,
                stdout=str(completed.stdout or ""),
                stderr=str(completed.stderr or ""),
                error_code="allure_generate_failed",
            )
        if not report_dir.exists():
            return AllureGenerateOutput(
                report_dir=None,
                stdout=str(completed.stdout or ""),
                stderr=str(completed.stderr or ""),
                error_code="allure_report_not_found",
            )
        return AllureGenerateOutput(
            report_dir=report_dir,
            stdout=str(completed.stdout or ""),
            stderr=str(completed.stderr or ""),
            error_code=None,
        )

    def _build_artifacts(
        self, execution_log: Path, allure_zip: Path | None, allure_report_zip: Path | None
    ) -> list[ArtifactIndex]:
        artifacts: list[ArtifactIndex] = []
        if execution_log.exists():
            artifacts.append(
                ArtifactIndex(
                    type=ArtifactType.LOG_BUNDLE,
                    storageKey=str(execution_log),
                    meta={"name": "execution.log", "kind": "EXECUTION_LOG", "size": execution_log.stat().st_size},
                )
            )
        if allure_zip is not None and allure_zip.exists():
            artifacts.append(
                ArtifactIndex(
                    type=ArtifactType.LOG_BUNDLE,
                    storageKey=str(allure_zip),
                    meta={"name": "allure-results.zip", "kind": "ALLURE_RESULTS", "size": allure_zip.stat().st_size},
                )
            )
        if allure_report_zip is not None and allure_report_zip.exists():
            artifacts.append(
                ArtifactIndex(
                    type=ArtifactType.LOG_BUNDLE,
                    storageKey=str(allure_report_zip),
                    meta={"name": "allure-report.zip", "kind": "ALLURE_REPORT", "size": allure_report_zip.stat().st_size},
                )
            )
        return artifacts

    def _build_case_results(
        self,
        *,
        case_outputs: list[_CaseExecutionOutput],
        artifacts: list[ArtifactIndex],
    ) -> list[CaseRunResult]:
        results: list[CaseRunResult] = []
        for item in case_outputs:
            status = item.status
            duration_ms = max((item.end_ts - item.start_ts) * 1000, 0)
            error_message = item.error_message or (item.stderr or "").strip()
            error_message = error_message[:2000] if error_message else None
            logs = [line for line in f"{item.stdout}\n{item.stderr}".splitlines() if line][:200]
            results.append(
                CaseRunResult(
                    caseRunId=item.case_run_id,
                    status=status,
                    startAt=item.start_ts,
                    endAt=item.end_ts,
                    errorType="RUNNER_ERROR" if status == CaseRunStatus.FAILED else None,
                    errorMessage=error_message,
                    logs=logs,
                    artifacts=artifacts,
                    metrics=CaseRunMetrics(durationMs=duration_ms),
                )
            )
        return results


def execute_pytest_allure_job(job: JobPayload) -> PytestAllureExecutionOutput:
    settings = get_settings()
    workspace_root = Path(settings.runner_workspace_root) if settings.runner_workspace_root else None
    return PytestAllureRunnerService(
        workspace_root=workspace_root,
        python_executable=settings.runner_python_executable,
        allure_command=settings.runner_allure_command,
    ).execute(job)


def generate_allure_report_for_run(run_id: str, *, timeout_sec: int) -> AllureGenerateOutput:
    settings = get_settings()
    workspace_root = Path(settings.runner_workspace_root) if settings.runner_workspace_root else None
    return PytestAllureRunnerService(
        workspace_root=workspace_root,
        python_executable=settings.runner_python_executable,
        allure_command=settings.runner_allure_command,
    ).generate_report_for_run(run_id, timeout_sec=timeout_sec)
