from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id, to_unix_ts
from app.core.database import get_db
from app.schemas.collection import (
    ApiCollectionDetail,
    ApiCollectionGroupPublic,
    ApiCollectionGroupWithRequests,
    ApiRequestCreateRequest,
    ApiRequestPublic,
    CollectionCreateRequest,
    CollectionListItem,
    CollectionUpdateRequest,
    ExportCollectionData,
    GroupCreateRequest,
    GroupUpdateByIdRequest,
    GroupUpdateRequest,
    GroupsReorderRequest,
    ImportCollectionRequest,
    RunApiRequestRequest,
    RunCollectionRequest,
)
from app.schemas.ai_import import (
    ApiImportCreateJobRequest,
    ApiImportCreateJobData,
    ApiImportJobDetail,
    ApiImportCommitRequest,
)
from app.schemas.common import ApiResponse, PageData
from app.services.collection import (
    create_collection,
    create_group,
    create_request,
    delete_collection,
    delete_group,
    delete_request,
    export_collection,
    get_collection,
    get_request,
    import_collection,
    list_collections,
    list_groups_and_requests,
    reorder_groups,
    run_collection_quick,
    run_request_quick,
    update_collection,
    update_group,
    update_request,
)
from app.services.ai_import import (
    create_api_import_job,
    upload_api_import_file,
    get_api_import_job,
    commit_api_import_job,
    parse_api_collection_async,
)

router = APIRouter(prefix="/collections")


def _to_request_public(r) -> ApiRequestPublic:
    return ApiRequestPublic(
        id=str(r.id),
        collectionId=str(r.collection_id),
        groupId=str(r.group_id) if r.group_id else None,
        name=r.name,
        method=r.method,
        url=r.url,
        headers=dict(r.headers_json or {}),
        auth=dict(r.auth_json or {}),
        body=dict(r.body_json or {}),
        asserts=dict(r.asserts_json or {}),
        updatedAt=to_unix_ts(r.updated_at),
    )


def _to_group_public(g) -> ApiCollectionGroupPublic:
    return ApiCollectionGroupPublic(
        id=str(g.id),
        collectionId=str(g.collection_id),
        name=g.name,
        order=int(g.order),
    )


@router.get("", response_model=ApiResponse[PageData[CollectionListItem]])
async def list_(
    projectId: str = Query(...),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[CollectionListItem]]:
    total, rows = await list_collections(
        db,
        user=user,
        project_id=uuid.UUID(projectId),
        page=page,
        page_size=pageSize,
    )
    items = [
        CollectionListItem(
            id=str(c.id),
            projectId=str(c.project_id),
            name=c.name,
            requestCount=req_cnt,
            updatedAt=to_unix_ts(c.updated_at),
        )
        for c, req_cnt in rows
    ]
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=items), requestId=request_id)


@router.post("", response_model=ApiResponse[ApiCollectionDetail])
async def create(
    payload: CollectionCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ApiCollectionDetail]:
    try:
        collection = await create_collection(
            db,
            user=user,
            project_id=uuid.UUID(payload.projectId),
            name=payload.name,
            variables=dict(payload.variables or {}),
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    groups, reqs = await list_groups_and_requests(db, user=user, collection_id=collection.id)
    detail = await _build_detail(db, user=user, collection_id=collection.id, groups=groups, reqs=reqs)
    return ApiResponse(data=detail, requestId=request_id)


async def _build_detail(
    db: AsyncSession,
    *,
    user: CurrentUser,
    collection_id: uuid.UUID,
    groups,
    reqs,
) -> ApiCollectionDetail:
    collection = await get_collection(db, user=user, collection_id=collection_id)
    reqs_by_group: dict[str, list] = {}
    for r in reqs:
        k = str(r.group_id) if r.group_id else ""
        reqs_by_group.setdefault(k, []).append(r)

    group_items: list[ApiCollectionGroupWithRequests] = []
    for g in groups:
        group_items.append(
            ApiCollectionGroupWithRequests(
                **_to_group_public(g).model_dump(),
                requests=[_to_request_public(r) for r in reqs_by_group.get(str(g.id), [])],
            )
        )

    ungrouped = [_to_request_public(r) for r in reqs_by_group.get("", [])]

    return ApiCollectionDetail(
        id=str(collection.id),
        projectId=str(collection.project_id),
        name=collection.name,
        variables=dict(collection.variables_json or {}),
        groups=group_items,
        requests=ungrouped,
        updatedAt=to_unix_ts(collection.updated_at),
    )


@router.get("/{collectionId}", response_model=ApiResponse[ApiCollectionDetail])
async def get_(
    collectionId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ApiCollectionDetail]:
    groups, reqs = await list_groups_and_requests(db, user=user, collection_id=collectionId)
    detail = await _build_detail(db, user=user, collection_id=collectionId, groups=groups, reqs=reqs)
    return ApiResponse(data=detail, requestId=request_id)


@router.put("/{collectionId}", response_model=ApiResponse[ApiCollectionDetail])
async def update(
    collectionId: uuid.UUID,
    payload: CollectionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ApiCollectionDetail]:
    fields_set = payload.model_fields_set
    variables_is_set = "variables" in fields_set
    try:
        collection = await update_collection(
            db,
            user=user,
            collection_id=collectionId,
            name=payload.name if "name" in fields_set else None,
            variables=payload.variables,
            variables_is_set=variables_is_set,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    groups, reqs = await list_groups_and_requests(db, user=user, collection_id=collection.id)
    detail = await _build_detail(db, user=user, collection_id=collection.id, groups=groups, reqs=reqs)
    return ApiResponse(data=detail, requestId=request_id)


@router.delete("/{collectionId}", response_model=ApiResponse[dict])
async def delete_(
    collectionId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[dict]:
    try:
        await delete_collection(db, user=user, collection_id=collectionId)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data={}, requestId=request_id)


@router.post("/{collectionId}/groups", response_model=ApiResponse[ApiCollectionGroupPublic])
async def create_group_(
    collectionId: uuid.UUID,
    payload: GroupCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ApiCollectionGroupPublic]:
    try:
        group = await create_group(db, user=user, collection_id=collectionId, name=payload.name)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=_to_group_public(group), requestId=request_id)


@router.put("/{collectionId}/groups", response_model=ApiResponse[list[ApiCollectionGroupPublic]])
async def put_groups_(
    collectionId: uuid.UUID,
    payload: GroupsReorderRequest | GroupUpdateByIdRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[ApiCollectionGroupPublic]]:
    try:
        if isinstance(payload, GroupsReorderRequest):
            items = [(uuid.UUID(i.id), int(i.order)) for i in payload.items]
            await reorder_groups(db, user=user, collection_id=collectionId, items=items)
        else:
            group_id = uuid.UUID(payload.groupId)
            await update_group(db, user=user, collection_id=collectionId, group_id=group_id, name=payload.name)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    groups, _ = await list_groups_and_requests(db, user=user, collection_id=collectionId)
    return ApiResponse(data=[_to_group_public(g) for g in groups], requestId=request_id)


@router.put("/{collectionId}/groups/{groupId}", response_model=ApiResponse[ApiCollectionGroupPublic])
async def update_group_(
    collectionId: uuid.UUID,
    groupId: uuid.UUID,
    payload: GroupUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ApiCollectionGroupPublic]:
    try:
        group = await update_group(db, user=user, collection_id=collectionId, group_id=groupId, name=payload.name)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=_to_group_public(group), requestId=request_id)


@router.delete("/{collectionId}/groups/{groupId}", response_model=ApiResponse[dict])
async def delete_group_(
    collectionId: uuid.UUID,
    groupId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[dict]:
    try:
        await delete_group(db, user=user, collection_id=collectionId, group_id=groupId)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data={}, requestId=request_id)


@router.post("/{collectionId}/requests", response_model=ApiResponse[ApiRequestPublic])
async def create_request_(
    collectionId: uuid.UUID,
    payload: ApiRequestCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ApiRequestPublic]:
    group_uuid = uuid.UUID(payload.groupId) if payload.groupId else None
    try:
        req = await create_request(
            db,
            user=user,
            collection_id=collectionId,
            group_id=group_uuid,
            name=payload.name,
            method=payload.method,
            url=payload.url,
            headers=dict(payload.headers or {}),
            auth=dict(payload.auth or {}),
            body=dict(payload.body or {}),
            asserts=dict(payload.asserts or {}),
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=_to_request_public(req), requestId=request_id)


@router.get("/{collectionId}/requests/{requestId}", response_model=ApiResponse[ApiRequestPublic])
async def get_request_(
    collectionId: uuid.UUID,
    requestId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ApiRequestPublic]:
    _, req = await get_request(db, user=user, collection_id=collectionId, request_id=requestId)
    return ApiResponse(data=_to_request_public(req), requestId=request_id)


@router.put("/{collectionId}/requests/{requestId}", response_model=ApiResponse[ApiRequestPublic])
async def update_request_(
    collectionId: uuid.UUID,
    requestId: uuid.UUID,
    payload: ApiRequestCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ApiRequestPublic]:
    group_uuid = uuid.UUID(payload.groupId) if payload.groupId else None
    try:
        req = await update_request(
            db,
            user=user,
            collection_id=collectionId,
            request_id=requestId,
            group_id=group_uuid,
            name=payload.name,
            method=payload.method,
            url=payload.url,
            headers=dict(payload.headers or {}),
            auth=dict(payload.auth or {}),
            body=dict(payload.body or {}),
            asserts=dict(payload.asserts or {}),
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=_to_request_public(req), requestId=request_id)


@router.delete("/{collectionId}/requests/{requestId}", response_model=ApiResponse[dict])
async def delete_request_(
    collectionId: uuid.UUID,
    requestId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[dict]:
    try:
        await delete_request(db, user=user, collection_id=collectionId, request_id=requestId)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data={}, requestId=request_id)


@router.post("/import", response_model=ApiResponse[ApiCollectionDetail])
async def import_(
    payload: ImportCollectionRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ApiCollectionDetail]:
    try:
        collection = await import_collection(
            db,
            user=user,
            project_id=uuid.UUID(payload.projectId),
            format=payload.format,
            content=payload.content,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    groups, reqs = await list_groups_and_requests(db, user=user, collection_id=collection.id)
    detail = await _build_detail(db, user=user, collection_id=collection.id, groups=groups, reqs=reqs)
    return ApiResponse(data=detail, requestId=request_id)


@router.post("/import-jobs", response_model=ApiResponse[ApiImportCreateJobData])
async def create_import_job_(
    payload: ApiImportCreateJobRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ApiImportCreateJobData]:
    try:
        job = await create_api_import_job(db, user=user, project_id=uuid.UUID(payload.projectId))
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(
        data=ApiImportCreateJobData(
            jobId=str(job.id),
            projectId=str(job.project_id),
            status=job.status,
            createdAt=to_unix_ts(job.created_at),
        ),
        requestId=request_id,
    )


@router.post("/import-jobs/{jobId}/file", response_model=ApiResponse[dict])
async def upload_import_job_file_(
    jobId: uuid.UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[dict]:
    try:
        await upload_api_import_file(db, user=user, job_id=jobId, file=file)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    background_tasks.add_task(parse_api_collection_async, jobId)
    return ApiResponse(data={}, requestId=request_id)


@router.get("/import-jobs/{jobId}", response_model=ApiResponse[ApiImportJobDetail])
async def get_import_job_(
    jobId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ApiImportJobDetail]:
    job = await get_api_import_job(db, user=user, job_id=jobId)
    return ApiResponse(
        data=ApiImportJobDetail(
            jobId=str(job.id),
            projectId=str(job.project_id),
            status=job.status,
            warnings=job.warnings_json,
            previewData=job.preview_data_json if job.preview_data_json else None,
            createdAt=to_unix_ts(job.created_at),
            updatedAt=to_unix_ts(job.updated_at),
        ),
        requestId=request_id,
    )


@router.post("/import-jobs/{jobId}/commit", response_model=ApiResponse[dict])
async def commit_import_job_(
    jobId: uuid.UUID,
    payload: ApiImportCommitRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[dict]:
    try:
        await commit_api_import_job(
            db, 
            user=user, 
            job_id=jobId, 
            selected_requests=[r.model_dump() for r in payload.selectedRequests],
            override_existing=payload.overrideExisting,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data={}, requestId=request_id)


@router.get("/{collectionId}/export", response_model=ApiResponse[ExportCollectionData])
async def export_(
    collectionId: uuid.UUID,
    format: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ExportCollectionData]:
    content = await export_collection(db, user=user, collection_id=collectionId, format=format)
    return ApiResponse(data=ExportCollectionData(format=format, content=content), requestId=request_id)


@router.post("/{collectionId}/run", response_model=ApiResponse[dict])
async def run_collection_(
    collectionId: uuid.UUID,
    payload: RunCollectionRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[dict]:
    env_uuid = uuid.UUID(payload.envId) if payload.envId else None
    data = await run_collection_quick(
        db,
        user=user,
        collection_id=collectionId,
        env_id=env_uuid,
        concurrency=payload.concurrency,
        iterations=payload.iterations,
    )
    return ApiResponse(data=data, requestId=request_id)


@router.post("/{collectionId}/requests/{requestId}/run", response_model=ApiResponse[dict])
async def run_request_(
    collectionId: uuid.UUID,
    requestId: uuid.UUID,
    payload: RunApiRequestRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[dict]:
    env_uuid = uuid.UUID(payload.envId) if payload.envId else None
    data = await run_request_quick(
        db,
        user=user,
        collection_id=collectionId,
        request_id=requestId,
        env_id=env_uuid,
    )
    return ApiResponse(data=data, requestId=request_id)
