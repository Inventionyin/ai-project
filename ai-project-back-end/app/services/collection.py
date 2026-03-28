from __future__ import annotations

import asyncio
import base64
import json
import time
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from fastapi import HTTPException
from sqlalchemy import delete, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.models.api import ApiCollection, ApiCollectionGroup, ApiRequest
from app.models.environment import Environment
from app.models.enums import ProjectRole
from app.models.project import Project, ProjectMember


def _is_admin(user: CurrentUser) -> bool:
    return "Admin" in user.roles or "ADMIN" in user.roles


async def _get_project(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> Project:
    project = await db.scalar(select(Project).where(Project.id == project_id, Project.tenant_id == user.tenant_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _get_member_role(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> ProjectRole | None:
    return (
        await db.execute(
            select(ProjectMember.role).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user.id,
                ProjectMember.tenant_id == user.tenant_id,
            )
        )
    ).scalar_one_or_none()


async def _require_project_read(db: AsyncSession, *, user: CurrentUser, project: Project) -> None:
    if _is_admin(user) or project.owner_id == user.id:
        return
    role = await _get_member_role(db, user=user, project_id=project.id)
    if role in (ProjectRole.ADMIN, ProjectRole.OWNER, ProjectRole.EDITOR, ProjectRole.VIEWER):
        return
    raise HTTPException(status_code=403, detail="No access to this project")


async def _require_project_write(db: AsyncSession, *, user: CurrentUser, project: Project) -> None:
    if _is_admin(user) or project.owner_id == user.id:
        return
    role = await _get_member_role(db, user=user, project_id=project.id)
    if role in (ProjectRole.ADMIN, ProjectRole.OWNER, ProjectRole.EDITOR):
        return
    raise HTTPException(status_code=403, detail="Only Owner/Editor can modify this project")


async def list_collections(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    page: int,
    page_size: int,
) -> tuple[int, list[tuple[ApiCollection, int]]]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)

    base_stmt = select(ApiCollection).where(
        ApiCollection.tenant_id == user.tenant_id,
        ApiCollection.project_id == project_id,
    )
    total = int((await db.execute(select(func.count()).select_from(base_stmt.subquery()))).scalar_one() or 0)

    req_cnt_sq = (
        select(ApiRequest.collection_id.label("collection_id"), func.count(ApiRequest.id).label("cnt"))
        .where(ApiRequest.tenant_id == user.tenant_id)
        .group_by(ApiRequest.collection_id)
        .subquery()
    )

    stmt = (
        select(ApiCollection, func.coalesce(req_cnt_sq.c.cnt, 0))
        .select_from(ApiCollection)
        .outerjoin(req_cnt_sq, req_cnt_sq.c.collection_id == ApiCollection.id)
        .where(ApiCollection.tenant_id == user.tenant_id, ApiCollection.project_id == project_id)
        .order_by(desc(ApiCollection.updated_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).all()
    return total, [(c, int(cnt)) for c, cnt in rows]


async def create_collection(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    name: str,
    variables: dict[str, Any] | None,
) -> ApiCollection:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    collection = ApiCollection(
        tenant_id=user.tenant_id,
        project_id=project_id,
        name=name,
        variables_json=dict(variables or {}),
    )
    db.add(collection)
    await db.flush()
    return collection


async def get_collection(
    db: AsyncSession,
    *,
    user: CurrentUser,
    collection_id: uuid.UUID,
) -> ApiCollection:
    collection = await db.scalar(
        select(ApiCollection).where(ApiCollection.id == collection_id, ApiCollection.tenant_id == user.tenant_id)
    )
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")

    project = await _get_project(db, user=user, project_id=collection.project_id)
    await _require_project_read(db, user=user, project=project)
    return collection


async def update_collection(
    db: AsyncSession,
    *,
    user: CurrentUser,
    collection_id: uuid.UUID,
    name: str | None,
    variables: dict[str, Any] | None,
    variables_is_set: bool,
) -> ApiCollection:
    collection = await get_collection(db, user=user, collection_id=collection_id)
    project = await _get_project(db, user=user, project_id=collection.project_id)
    await _require_project_write(db, user=user, project=project)

    if name is not None:
        collection.name = name
    if variables_is_set:
        collection.variables_json = dict(variables or {})
    await db.flush()
    return collection


async def delete_collection(
    db: AsyncSession,
    *,
    user: CurrentUser,
    collection_id: uuid.UUID,
) -> None:
    collection = await get_collection(db, user=user, collection_id=collection_id)
    project = await _get_project(db, user=user, project_id=collection.project_id)
    await _require_project_write(db, user=user, project=project)

    await db.execute(
        delete(ApiRequest).where(ApiRequest.tenant_id == user.tenant_id, ApiRequest.collection_id == collection.id)
    )
    await db.execute(
        delete(ApiCollectionGroup).where(
            ApiCollectionGroup.tenant_id == user.tenant_id, ApiCollectionGroup.collection_id == collection.id
        )
    )
    await db.delete(collection)


async def list_groups_and_requests(
    db: AsyncSession,
    *,
    user: CurrentUser,
    collection_id: uuid.UUID,
) -> tuple[list[ApiCollectionGroup], list[ApiRequest]]:
    collection = await get_collection(db, user=user, collection_id=collection_id)
    groups = (
        (
            await db.execute(
                select(ApiCollectionGroup)
                .where(
                    ApiCollectionGroup.tenant_id == user.tenant_id,
                    ApiCollectionGroup.collection_id == collection.id,
                )
                .order_by(ApiCollectionGroup.order.asc(), ApiCollectionGroup.updated_at.desc())
            )
        )
        .scalars()
        .all()
    )
    reqs = (
        (
            await db.execute(
                select(ApiRequest)
                .where(ApiRequest.tenant_id == user.tenant_id, ApiRequest.collection_id == collection.id)
                .order_by(ApiRequest.updated_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return groups, reqs


async def create_group(
    db: AsyncSession,
    *,
    user: CurrentUser,
    collection_id: uuid.UUID,
    name: str,
) -> ApiCollectionGroup:
    collection = await get_collection(db, user=user, collection_id=collection_id)
    project = await _get_project(db, user=user, project_id=collection.project_id)
    await _require_project_write(db, user=user, project=project)

    max_order = (
        await db.execute(
            select(func.coalesce(func.max(ApiCollectionGroup.order), 0)).where(
                ApiCollectionGroup.tenant_id == user.tenant_id,
                ApiCollectionGroup.collection_id == collection.id,
            )
        )
    ).scalar_one()
    order_no = int(max_order or 0) + 1

    group = ApiCollectionGroup(
        tenant_id=user.tenant_id,
        collection_id=collection.id,
        name=name,
        order=order_no,
    )
    db.add(group)
    await db.flush()
    return group


async def update_group(
    db: AsyncSession,
    *,
    user: CurrentUser,
    collection_id: uuid.UUID,
    group_id: uuid.UUID,
    name: str,
) -> ApiCollectionGroup:
    collection = await get_collection(db, user=user, collection_id=collection_id)
    project = await _get_project(db, user=user, project_id=collection.project_id)
    await _require_project_write(db, user=user, project=project)

    group = await db.scalar(
        select(ApiCollectionGroup).where(
            ApiCollectionGroup.id == group_id,
            ApiCollectionGroup.tenant_id == user.tenant_id,
            ApiCollectionGroup.collection_id == collection.id,
        )
    )
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    group.name = name
    await db.flush()
    return group


async def reorder_groups(
    db: AsyncSession,
    *,
    user: CurrentUser,
    collection_id: uuid.UUID,
    items: list[tuple[uuid.UUID, int]],
) -> None:
    collection = await get_collection(db, user=user, collection_id=collection_id)
    project = await _get_project(db, user=user, project_id=collection.project_id)
    await _require_project_write(db, user=user, project=project)

    group_ids = [gid for gid, _ in items]
    if len(group_ids) != len(set(group_ids)):
        raise HTTPException(status_code=400, detail="groupId duplicated")

    orders = [int(order) for _, order in items]
    if len(orders) != len(set(orders)):
        raise HTTPException(status_code=400, detail="order duplicated")

    exists = (
        await db.execute(
            select(ApiCollectionGroup.id).where(
                ApiCollectionGroup.tenant_id == user.tenant_id,
                ApiCollectionGroup.collection_id == collection.id,
                ApiCollectionGroup.id.in_(group_ids),
            )
        )
    ).scalars().all()
    if len(exists) != len(group_ids):
        raise HTTPException(status_code=404, detail="Group not found")

    for group_id, order in items:
        await db.execute(
            update(ApiCollectionGroup)
            .where(
                ApiCollectionGroup.tenant_id == user.tenant_id,
                ApiCollectionGroup.collection_id == collection.id,
                ApiCollectionGroup.id == group_id,
            )
            .values(order=int(order))
        )

    await db.flush()


async def delete_group(
    db: AsyncSession,
    *,
    user: CurrentUser,
    collection_id: uuid.UUID,
    group_id: uuid.UUID,
) -> None:
    collection = await get_collection(db, user=user, collection_id=collection_id)
    project = await _get_project(db, user=user, project_id=collection.project_id)
    await _require_project_write(db, user=user, project=project)

    group = await db.scalar(
        select(ApiCollectionGroup).where(
            ApiCollectionGroup.id == group_id,
            ApiCollectionGroup.tenant_id == user.tenant_id,
            ApiCollectionGroup.collection_id == collection.id,
        )
    )
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")

    await db.execute(delete(ApiRequest).where(ApiRequest.tenant_id == user.tenant_id, ApiRequest.group_id == group.id))
    await db.delete(group)


async def create_request(
    db: AsyncSession,
    *,
    user: CurrentUser,
    collection_id: uuid.UUID,
    group_id: uuid.UUID | None,
    name: str,
    method: str,
    url: str,
    headers: dict[str, Any] | None,
    auth: dict[str, Any] | None,
    body: dict[str, Any] | None,
    asserts: dict[str, Any] | None,
) -> ApiRequest:
    collection = await get_collection(db, user=user, collection_id=collection_id)
    project = await _get_project(db, user=user, project_id=collection.project_id)
    await _require_project_write(db, user=user, project=project)

    group_uuid: uuid.UUID | None = None
    if group_id is not None:
        group_uuid = group_id
        exists = await db.scalar(
            select(ApiCollectionGroup.id).where(
                ApiCollectionGroup.id == group_uuid,
                ApiCollectionGroup.tenant_id == user.tenant_id,
                ApiCollectionGroup.collection_id == collection.id,
            )
        )
        if exists is None:
            raise HTTPException(status_code=404, detail="Group not found")

    req = ApiRequest(
        tenant_id=user.tenant_id,
        collection_id=collection.id,
        group_id=group_uuid,
        name=name,
        method=method.upper(),
        url=url,
        headers_json=dict(headers or {}),
        auth_json=dict(auth or {}),
        body_json=dict(body or {}),
        asserts_json=dict(asserts or {}),
    )
    db.add(req)
    await db.flush()
    return req


async def get_request(
    db: AsyncSession,
    *,
    user: CurrentUser,
    collection_id: uuid.UUID,
    request_id: uuid.UUID,
) -> tuple[ApiCollection, ApiRequest]:
    collection = await get_collection(db, user=user, collection_id=collection_id)

    req = await db.scalar(select(ApiRequest).where(ApiRequest.id == request_id, ApiRequest.tenant_id == user.tenant_id))
    if req is None or req.collection_id != collection.id:
        raise HTTPException(status_code=404, detail="Request not found")
    return collection, req


async def update_request(
    db: AsyncSession,
    *,
    user: CurrentUser,
    collection_id: uuid.UUID,
    request_id: uuid.UUID,
    group_id: uuid.UUID | None,
    name: str,
    method: str,
    url: str,
    headers: dict[str, Any] | None,
    auth: dict[str, Any] | None,
    body: dict[str, Any] | None,
    asserts: dict[str, Any] | None,
) -> ApiRequest:
    collection, req = await get_request(db, user=user, collection_id=collection_id, request_id=request_id)
    project = await _get_project(db, user=user, project_id=collection.project_id)
    await _require_project_write(db, user=user, project=project)

    group_uuid: uuid.UUID | None = None
    if group_id is not None:
        group_uuid = group_id
        exists = await db.scalar(
            select(ApiCollectionGroup.id).where(
                ApiCollectionGroup.id == group_uuid,
                ApiCollectionGroup.tenant_id == user.tenant_id,
                ApiCollectionGroup.collection_id == collection.id,
            )
        )
        if exists is None:
            raise HTTPException(status_code=404, detail="Group not found")

    req.group_id = group_uuid
    req.name = name
    req.method = method.upper()
    req.url = url
    req.headers_json = dict(headers or {})
    req.auth_json = dict(auth or {})
    req.body_json = dict(body or {})
    req.asserts_json = dict(asserts or {})
    await db.flush()
    return req


async def delete_request(
    db: AsyncSession,
    *,
    user: CurrentUser,
    collection_id: uuid.UUID,
    request_id: uuid.UUID,
) -> None:
    collection, req = await get_request(db, user=user, collection_id=collection_id, request_id=request_id)
    project = await _get_project(db, user=user, project_id=collection.project_id)
    await _require_project_write(db, user=user, project=project)
    await db.delete(req)


def _parse_json_content(content: str) -> Any:
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid content") from exc


def _postman_url_to_raw(url_obj: Any) -> str:
    if isinstance(url_obj, str):
        return url_obj
    if isinstance(url_obj, dict):
        raw = url_obj.get("raw")
        if isinstance(raw, str) and raw.strip():
            return raw
        host = url_obj.get("host")
        path = url_obj.get("path")
        if isinstance(host, list):
            host_s = ".".join(str(x) for x in host if str(x))
        else:
            host_s = str(host) if host else ""
        if isinstance(path, list):
            path_s = "/".join(str(x) for x in path if str(x))
        else:
            path_s = str(path) if path else ""
        protocol = url_obj.get("protocol") or "http"
        if host_s and path_s:
            return f"{protocol}://{host_s}/{path_s}"
        if host_s:
            return f"{protocol}://{host_s}"
    return ""


def _postman_headers_to_dict(headers: Any) -> dict[str, str]:
    if isinstance(headers, dict):
        return {str(k): str(v) for k, v in headers.items()}
    if isinstance(headers, list):
        out: dict[str, str] = {}
        for h in headers:
            if not isinstance(h, dict):
                continue
            key = h.get("key")
            value = h.get("value")
            if isinstance(key, str) and key.strip():
                out[key] = str(value) if value is not None else ""
        return out
    return {}


def _parse_postman_items(
    items: list[Any],
    *,
    group_path: str | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    root_reqs: list[dict[str, Any]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        if "item" in it and isinstance(it.get("item"), list):
            folder_name = str(it.get("name") or "").strip() or "Group"
            next_path = folder_name if not group_path else f"{group_path}/{folder_name}"
            g, r = _parse_postman_items(it.get("item") or [], group_path=next_path)
            for k, v in g.items():
                groups.setdefault(k, []).extend(v)
            root_reqs.extend(r)
            continue

        req_obj = it.get("request")
        if not isinstance(req_obj, dict):
            continue
        name = str(it.get("name") or "").strip() or str(req_obj.get("name") or "").strip() or "Request"
        method = str(req_obj.get("method") or "GET").upper()
        url = _postman_url_to_raw(req_obj.get("url"))
        headers = _postman_headers_to_dict(req_obj.get("header"))
        auth = req_obj.get("auth") if isinstance(req_obj.get("auth"), dict) else {}
        body_obj = req_obj.get("body")
        body: dict[str, Any] = {}
        if isinstance(body_obj, dict):
            body = dict(body_obj)

        payload = {
            "name": name,
            "method": method,
            "url": url,
            "headers": headers,
            "auth": auth,
            "body": body,
            "asserts": {},
        }
        if group_path:
            groups.setdefault(group_path, []).append(payload)
        else:
            root_reqs.append(payload)
    return groups, root_reqs


async def import_collection(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    format: str,
    content: str,
) -> ApiCollection:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)

    fmt = format.strip().lower()
    if fmt not in ("postman", "swagger"):
        raise HTTPException(status_code=400, detail="Invalid format")

    parsed = _parse_json_content(content)
    collection_name = "Imported Collection"
    variables: dict[str, Any] = {}
    groups: dict[str, list[dict[str, Any]]] = {}
    root_reqs: list[dict[str, Any]] = []

    if fmt == "postman":
        if not isinstance(parsed, dict):
            raise HTTPException(status_code=400, detail="Invalid content")
        info = parsed.get("info") if isinstance(parsed.get("info"), dict) else {}
        collection_name = str(info.get("name") or "Imported Postman").strip() or "Imported Postman"
        vars_obj = parsed.get("variable")
        if isinstance(vars_obj, list):
            for v in vars_obj:
                if not isinstance(v, dict):
                    continue
                k = v.get("key")
                val = v.get("value")
                if isinstance(k, str) and k.strip():
                    variables[k] = val
        item_list = parsed.get("item")
        if not isinstance(item_list, list):
            raise HTTPException(status_code=400, detail="Invalid content")
        groups, root_reqs = _parse_postman_items(item_list)

    if fmt == "swagger":
        if not isinstance(parsed, dict):
            raise HTTPException(status_code=400, detail="Invalid content")
        if "openapi" in parsed:
            collection_name = str((parsed.get("info") or {}).get("title") or "Imported OpenAPI").strip() or "Imported OpenAPI"
            paths = parsed.get("paths")
            if not isinstance(paths, dict):
                raise HTTPException(status_code=400, detail="Invalid content")
            for path, ops in paths.items():
                if not isinstance(ops, dict):
                    continue
                for method, op in ops.items():
                    if method.lower() not in ("get", "post", "put", "patch", "delete", "head", "options"):
                        continue
                    if not isinstance(op, dict):
                        continue
                    tags = op.get("tags")
                    group_name = "default"
                    if isinstance(tags, list) and tags:
                        group_name = str(tags[0] or "default")
                    name = str(op.get("summary") or op.get("operationId") or f"{method.upper()} {path}")
                    groups.setdefault(group_name, []).append(
                        {
                            "name": name,
                            "method": method.upper(),
                            "url": str(path),
                            "headers": {},
                            "auth": {},
                            "body": {},
                            "asserts": {},
                        }
                    )
        else:
            raise HTTPException(status_code=400, detail="Invalid content")

    collection = ApiCollection(
        tenant_id=user.tenant_id,
        project_id=project_id,
        name=collection_name,
        variables_json=variables,
    )
    db.add(collection)
    await db.flush()

    group_id_by_name: dict[str, uuid.UUID] = {}
    order_no = 0
    for gname in sorted(groups.keys()):
        order_no += 1
        g = ApiCollectionGroup(
            tenant_id=user.tenant_id,
            collection_id=collection.id,
            name=gname,
            order=order_no,
        )
        db.add(g)
        await db.flush()
        group_id_by_name[gname] = g.id

    for req in root_reqs:
        db.add(
            ApiRequest(
                tenant_id=user.tenant_id,
                collection_id=collection.id,
                group_id=None,
                name=str(req.get("name") or "Request"),
                method=str(req.get("method") or "GET").upper(),
                url=str(req.get("url") or ""),
                headers_json=dict(req.get("headers") or {}),
                auth_json=dict(req.get("auth") or {}),
                body_json=dict(req.get("body") or {}),
                asserts_json=dict(req.get("asserts") or {}),
            )
        )

    for gname, reqs in groups.items():
        gid = group_id_by_name[gname]
        for req in reqs:
            db.add(
                ApiRequest(
                    tenant_id=user.tenant_id,
                    collection_id=collection.id,
                    group_id=gid,
                    name=str(req.get("name") or "Request"),
                    method=str(req.get("method") or "GET").upper(),
                    url=str(req.get("url") or ""),
                    headers_json=dict(req.get("headers") or {}),
                    auth_json=dict(req.get("auth") or {}),
                    body_json=dict(req.get("body") or {}),
                    asserts_json=dict(req.get("asserts") or {}),
                )
            )

    await db.flush()
    return collection


def export_collection_postman(
    *,
    collection: ApiCollection,
    groups: list[ApiCollectionGroup],
    requests: list[ApiRequest],
) -> str:
    reqs_by_group: dict[str, list[ApiRequest]] = {}
    for r in requests:
        gid = str(r.group_id) if r.group_id else ""
        reqs_by_group.setdefault(gid, []).append(r)

    def _req_to_item(r: ApiRequest) -> dict[str, Any]:
        headers = [{"key": k, "value": v} for k, v in (r.headers_json or {}).items()]
        return {
            "name": r.name,
            "request": {
                "method": r.method,
                "header": headers,
                "url": r.url,
                "auth": dict(r.auth_json or {}),
                "body": dict(r.body_json or {}),
            },
        }

    items: list[dict[str, Any]] = []
    for g in sorted(groups, key=lambda x: (int(x.order), x.name)):
        g_items = [_req_to_item(r) for r in reqs_by_group.get(str(g.id), [])]
        items.append({"name": g.name, "item": g_items})
    for r in reqs_by_group.get("", []):
        items.append(_req_to_item(r))

    out = {
        "info": {"name": collection.name, "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
        "item": items,
        "variable": [{"key": k, "value": v} for k, v in (collection.variables_json or {}).items()],
    }
    return json.dumps(out, ensure_ascii=False, separators=(",", ":"), indent=2)


def export_collection_openapi(
    *,
    collection: ApiCollection,
    groups: list[ApiCollectionGroup],
    requests: list[ApiRequest],
) -> str:
    paths: dict[str, Any] = {}
    for r in requests:
        p = r.url if r.url.startswith("/") else f"/{r.url}"
        methods = paths.setdefault(p, {})
        methods[r.method.lower()] = {"summary": r.name, "responses": {"200": {"description": "OK"}}}
    out = {
        "openapi": "3.0.0",
        "info": {"title": collection.name, "version": "1.0.0"},
        "paths": paths,
    }
    return json.dumps(out, ensure_ascii=False, separators=(",", ":"), indent=2)


def export_collection_curl(
    *,
    collection: ApiCollection,
    groups: list[ApiCollectionGroup],
    requests: list[ApiRequest],
) -> str:
    lines: list[str] = []
    for r in requests:
        cmd = ["curl", "-X", r.method.upper(), f"'{r.url}'"]
        for k, v in (r.headers_json or {}).items():
            cmd.extend(["-H", f"'{k}: {v}'"])
        if r.body_json:
            raw = json.dumps(r.body_json, ensure_ascii=False, separators=(",", ":"))
            cmd.extend(["--data", f"'{raw}'"])
        lines.append(" ".join(cmd))
    return "\n".join(lines)


def _apply_vars(value: str, vars_map: dict[str, Any]) -> str:
    out = value
    for k, v in vars_map.items():
        key = str(k)
        out = out.replace(f"{{{{{key}}}}}", str(v))
    return out


@dataclass(frozen=True)
class _ExecResult:
    status: int | None
    elapsed_ms: int
    headers: dict[str, str]
    body: str
    error: str | None


def _execute_http(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    body_bytes: bytes | None,
    timeout_sec: float,
) -> _ExecResult:
    start = time.perf_counter()
    try:
        req = Request(url=url, method=method.upper(), headers=headers, data=body_bytes)
        with urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read(50_000)
            try:
                body = raw.decode("utf-8", errors="replace")
            except Exception:
                body = base64.b64encode(raw).decode("ascii")
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            resp_headers = {k: v for k, v in resp.headers.items()}
            return _ExecResult(status=int(resp.status), elapsed_ms=elapsed_ms, headers=resp_headers, body=body, error=None)
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return _ExecResult(status=None, elapsed_ms=elapsed_ms, headers={}, body="", error=str(exc))


def _build_full_url(base_url: str, req_url: str) -> str:
    if req_url.startswith("http://") or req_url.startswith("https://"):
        return req_url
    if not base_url:
        return req_url
    if req_url.startswith("/"):
        return urljoin(base_url.rstrip("/") + "/", req_url.lstrip("/"))
    return urljoin(base_url.rstrip("/") + "/", req_url)


def _auth_to_headers(auth: dict[str, Any]) -> dict[str, str]:
    if not auth:
        return {}
    auth_type = str(auth.get("type") or "").lower()
    if auth_type == "bearer":
        bearer_list = auth.get("bearer")
        token: str | None = None
        if isinstance(bearer_list, list):
            for it in bearer_list:
                if isinstance(it, dict) and it.get("key") == "token":
                    token = str(it.get("value") or "")
                    break
        if isinstance(auth.get("token"), str):
            token = auth.get("token")
        if token:
            return {"Authorization": f"Bearer {token}"}
    if auth_type == "basic":
        u = auth.get("username") or ""
        p = auth.get("password") or ""
        raw = f"{u}:{p}".encode("utf-8")
        return {"Authorization": f"Basic {base64.b64encode(raw).decode('ascii')}"}
    return {}


async def run_request_quick(
    db: AsyncSession,
    *,
    user: CurrentUser,
    collection_id: uuid.UUID,
    request_id: uuid.UUID,
    env_id: uuid.UUID | None,
) -> dict[str, Any]:
    collection, req = await get_request(db, user=user, collection_id=collection_id, request_id=request_id)
    project = await _get_project(db, user=user, project_id=collection.project_id)
    await _require_project_write(db, user=user, project=project)

    env: Environment | None = None
    if env_id is not None:
        env = await db.scalar(select(Environment).where(Environment.id == env_id, Environment.tenant_id == user.tenant_id))
        if env is None or env.project_id != collection.project_id:
            raise HTTPException(status_code=404, detail="Environment not found")

    vars_map: dict[str, Any] = dict(collection.variables_json or {})
    if env is not None:
        vars_map.update(dict(env.variables_json or {}))

    full_url = _apply_vars(_build_full_url(env.base_url if env else "", req.url), vars_map)
    headers = {str(k): _apply_vars(str(v), vars_map) for k, v in (req.headers_json or {}).items()}
    headers.update({k: _apply_vars(v, vars_map) for k, v in _auth_to_headers(dict(req.auth_json or {})).items()})

    body_bytes: bytes | None = None
    if req.body_json:
        raw = req.body_json.get("raw") if isinstance(req.body_json, dict) else None
        if isinstance(raw, str):
            body_bytes = _apply_vars(raw, vars_map).encode("utf-8")
        else:
            body_bytes = _apply_vars(json.dumps(req.body_json, ensure_ascii=False, separators=(",", ":")), vars_map).encode(
                "utf-8"
            )
        if "Content-Type" not in headers and "content-type" not in {k.lower() for k in headers.keys()}:
            headers["Content-Type"] = "application/json"

    result = await asyncio.to_thread(
        _execute_http,
        method=req.method,
        url=full_url,
        headers=headers,
        body_bytes=body_bytes,
        timeout_sec=30.0,
    )

    ok = result.error is None and (result.status is not None and 200 <= result.status < 400)
    expected_status = None
    if isinstance(req.asserts_json, dict):
        expected_status = req.asserts_json.get("statusCode")
        if isinstance(expected_status, int) and result.status is not None:
            ok = ok and result.status == expected_status

    return {
        "collectionId": str(collection.id),
        "requestId": str(req.id),
        "envId": str(env.id) if env else None,
        "ok": ok,
        "status": result.status,
        "elapsedMs": result.elapsed_ms,
        "error": result.error,
        "response": {"headers": result.headers, "body": result.body},
    }


async def run_collection_quick(
    db: AsyncSession,
    *,
    user: CurrentUser,
    collection_id: uuid.UUID,
    env_id: uuid.UUID | None,
    concurrency: int,
    iterations: int,
) -> dict[str, Any]:
    collection = await get_collection(db, user=user, collection_id=collection_id)
    project = await _get_project(db, user=user, project_id=collection.project_id)
    await _require_project_write(db, user=user, project=project)

    env: Environment | None = None
    if env_id is not None:
        env = await db.scalar(select(Environment).where(Environment.id == env_id, Environment.tenant_id == user.tenant_id))
        if env is None or env.project_id != collection.project_id:
            raise HTTPException(status_code=404, detail="Environment not found")

    groups, reqs = await list_groups_and_requests(db, user=user, collection_id=collection.id)
    req_order: list[ApiRequest] = []
    group_order = [g.id for g in sorted(groups, key=lambda x: (int(x.order), x.name))]
    reqs_by_group: dict[uuid.UUID | None, list[ApiRequest]] = {}
    for r in reqs:
        reqs_by_group.setdefault(r.group_id, []).append(r)
    for gid in group_order:
        req_order.extend(reqs_by_group.get(gid, []))
    req_order.extend(reqs_by_group.get(None, []))

    sem = asyncio.Semaphore(max(1, int(concurrency)))
    results: list[dict[str, Any]] = []

    async def _run_one(r: ApiRequest) -> dict[str, Any]:
        async with sem:
            return await run_request_quick(
                db,
                user=user,
                collection_id=collection.id,
                request_id=r.id,
                env_id=env.id if env else None,
            )

    for _ in range(max(1, int(iterations))):
        batch = await asyncio.gather(*[_run_one(r) for r in req_order])
        results.extend(batch)

    passed = sum(1 for r in results if r.get("ok"))
    return {
        "collectionId": str(collection.id),
        "envId": str(env.id) if env else None,
        "concurrency": int(concurrency),
        "iterations": int(iterations),
        "summary": {"total": len(results), "passed": passed, "failed": len(results) - passed},
        "results": results,
    }


async def export_collection(
    db: AsyncSession,
    *,
    user: CurrentUser,
    collection_id: uuid.UUID,
    format: str,
) -> str:
    collection = await get_collection(db, user=user, collection_id=collection_id)
    project = await _get_project(db, user=user, project_id=collection.project_id)
    await _require_project_read(db, user=user, project=project)

    groups, requests = await list_groups_and_requests(db, user=user, collection_id=collection.id)
    fmt = format.strip().lower()
    if fmt == "postman":
        return export_collection_postman(collection=collection, groups=groups, requests=requests)
    if fmt == "swagger":
        return export_collection_openapi(collection=collection, groups=groups, requests=requests)
    if fmt == "curl":
        return export_collection_curl(collection=collection, groups=groups, requests=requests)
    raise HTTPException(status_code=400, detail="Invalid format")
