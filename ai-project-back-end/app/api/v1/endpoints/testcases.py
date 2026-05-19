from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id, to_unix_ts
from app.core.database import get_db
from app.models.enums import AiImportSourceType, TestCaseStatus, TestCaseType
from app.schemas.ai_import import (
    AiImportCreateJobData,
    AiImportCreateJobRequest,
    AiImportGetJobData,
    AiImportPreviewItem,
    AiImportUploadJobFileData,
)
from app.schemas.common import ApiResponse, PageData
from app.schemas.testcase import (
    TestCaseCreateRequest,
    TestCaseDetail,
    TestCaseListItem,
    TestCaseOwnerOption,
    TestCasePutRequest,
    TestCaseRestoreRequest,
    TestCaseVersionSchema,
)
from app.schemas.testcase_import import TestCaseImportData
from app.services.testcase import (
    archive_testcase,
    create_testcase,
    delete_testcase,
    get_latest_case_runs,
    get_owner_name,
    get_testcase,
    get_testcase_versions,
    list_testcases,
    list_testcase_owner_options,
    restore_testcase_version,
    unarchive_testcase,
    update_testcase,
)
from app.services.ai_import import create_ai_import_job, get_ai_import_job, upload_ai_import_job_file
from app.services.testcase_import import import_testcases_from_file

router = APIRouter(prefix="/testcases")

def _format_version(minor: int) -> str:
    return f"v1.{minor}"


def _extract_api_params(ai_meta_json: dict | None) -> dict:
    if not isinstance(ai_meta_json, dict):
        return {}
    value = ai_meta_json.get("apiParams")
    if not isinstance(value, dict):
        return {}
    return value


def _extract_api_headers(ai_meta_json: dict | None) -> dict[str, str]:
    if not isinstance(ai_meta_json, dict):
        return {}
    value = ai_meta_json.get("apiHeaders")
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, str] = {}
    for key, item in value.items():
        normalized[str(key)] = str(item)
    return normalized


def _extract_expected_result(ai_meta_json: dict | None) -> str | None:
    if not isinstance(ai_meta_json, dict):
        return None
    value = ai_meta_json.get("expectedResult")
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _extract_expected_status_code(ai_meta_json: dict | None) -> int | None:
    if not isinstance(ai_meta_json, dict):
        return None
    value = ai_meta_json.get("expectedStatusCode")
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return parsed


def _extract_preconditions(ai_meta_json: dict | None) -> str | None:
    if not isinstance(ai_meta_json, dict):
        return None
    value = ai_meta_json.get("preconditions")
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _extract_postconditions(ai_meta_json: dict | None) -> str | None:
    if not isinstance(ai_meta_json, dict):
        return None
    value = ai_meta_json.get("postconditions")
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


@router.post("/ai-import/jobs", response_model=ApiResponse[AiImportCreateJobData])
async def create_ai_import_job_(
    payload: AiImportCreateJobRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[AiImportCreateJobData]:
    idem = (idempotency_key or "").strip() or None
    if idem is not None and len(idem) > 128:
        raise HTTPException(status_code=400, detail="Idempotency-Key length must be <= 128")
    try:
        job = await create_ai_import_job(db, user=user, payload=payload, idempotency_key=idem)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return ApiResponse(
        data=AiImportCreateJobData(
            jobId=str(job.id),
            projectId=str(job.project_id),
            sourceType=job.source_type,
            status=job.status,
            createdAt=to_unix_ts(job.created_at),
        ),
        requestId=request_id,
    )


@router.post("/ai-import/jobs/{jobId}/file", response_model=ApiResponse[AiImportUploadJobFileData])
async def upload_ai_import_job_file_(
    jobId: uuid.UUID,
    file: UploadFile = File(...),
    filename: str = Form(...),
    sourceType: AiImportSourceType = Form(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[AiImportUploadJobFileData]:
    final_filename = filename.strip()
    file_content = await file.read()

    try:
        job, file_size = await upload_ai_import_job_file(
            db,
            user=user,
            job_id=jobId,
            source_type=sourceType,
            filename=final_filename,
            file_content=file_content,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await file.close()

    source_ref = job.source_ref_json if isinstance(job.source_ref_json, dict) else {}
    file_name = source_ref.get("fileName", final_filename)
    if not isinstance(file_name, str) or not file_name.strip():
        file_name = final_filename

    return ApiResponse(
        data=AiImportUploadJobFileData(
            jobId=str(job.id),
            projectId=str(job.project_id),
            sourceType=job.source_type,
            status=job.status,
            fileName=file_name,
            fileSize=file_size,
            uploadedAt=to_unix_ts(job.updated_at),
        ),
        requestId=request_id,
    )


@router.get("/ai-import/jobs/{jobId}", response_model=ApiResponse[AiImportGetJobData])
async def get_ai_import_job_(
    jobId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[AiImportGetJobData]:
    job, preview_items = await get_ai_import_job(db, user=user, job_id=jobId)
    return ApiResponse(
        data=AiImportGetJobData(
            jobId=str(job.id),
            projectId=str(job.project_id),
            sourceType=job.source_type,
            status=job.status,
            summary=job.summary_json or {},
            previewItems=[
                AiImportPreviewItem(
                    id=str(item.id),
                    title=item.title,
                    type=item.type,
                    priority=item.priority,
                    status=item.status,
                    feature=item.feature,
                    epic=item.epic,
                    story=item.story,
                    task=item.task,
                    description=item.description,
                    steps=item.steps_json,
                    apiUrl=item.api_url,
                    apiMethod=item.api_method,
                    tags=item.tags_json,
                    confidence=float(item.confidence) if item.confidence is not None else None,
                    selected=item.selected,
                )
                for item in preview_items
            ],
            createdAt=to_unix_ts(job.created_at),
            updatedAt=to_unix_ts(job.updated_at),
        ),
        requestId=request_id,
    )


@router.post("/import", response_model=ApiResponse[TestCaseImportData])
async def import_(
    projectId: str = Form(...),
    mode: str = Form(default="partial"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[TestCaseImportData]:
    project_uuid = uuid.UUID(projectId)
    file_content = await file.read()
    try:
        data = await import_testcases_from_file(
            db,
            user=user,
            project_id=project_uuid,
            filename=file.filename or "",
            file_bytes=file_content,
            mode=mode,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await file.close()

    return ApiResponse(data=data, requestId=request_id)


@router.post("", response_model=ApiResponse[TestCaseDetail])
async def create(
    payload: TestCaseCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[TestCaseDetail]:
    try:
        testcase = await create_testcase(db, user=user, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return ApiResponse(
        data=TestCaseDetail(
            id=str(testcase.id),
            projectId=str(testcase.project_id),
            testCaseId=testcase.test_case_id,
            expectedStatusCode=_extract_expected_status_code(testcase.ai_meta_json),
            preconditions=_extract_preconditions(testcase.ai_meta_json),
            postconditions=_extract_postconditions(testcase.ai_meta_json),
            title=testcase.title,
            type=testcase.type,
            priority=testcase.priority,
            status=testcase.status,
            tags=testcase.tags_json,
            ownerId=str(testcase.owner_id) if testcase.owner_id else None,
            version=_format_version(testcase.version),
            contentMd=testcase.content_md,
            feature=testcase.feature,
            apiMethod=testcase.api_method,
            apiUrl=testcase.api_url,
            apiParams=_extract_api_params(testcase.ai_meta_json),
            apiHeaders=_extract_api_headers(testcase.ai_meta_json),
            expectedResult=_extract_expected_result(testcase.ai_meta_json),
        ),
        requestId=request_id,
    )


@router.get("", response_model=ApiResponse[PageData[TestCaseListItem]])
async def list_(
    projectId: str = Query(...),
    title: str | None = Query(default=None, min_length=1, max_length=100),
    type: TestCaseType | None = None,
    status: TestCaseStatus | None = None,
    tag: str | None = None,
    ownerId: str | None = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[TestCaseListItem]]:
    project_uuid = uuid.UUID(projectId)
    owner_uuid = uuid.UUID(ownerId) if ownerId else None

    total, testcases = await list_testcases(
        db,
        user=user,
        project_id=project_uuid,
        title=title,
        page=page,
        page_size=pageSize,
        type_=type,
        status=status,
        tag=tag,
        owner_id=owner_uuid,
    )
    latest_case_runs = await get_latest_case_runs(
        db,
        user=user,
        testcase_ids=[tc.id for tc in testcases],
    )
    items: list[TestCaseListItem] = []
    for tc in testcases:
        latest_case_run = latest_case_runs.get(tc.id)
        items.append(
            TestCaseListItem(
                id=str(tc.id),
                projectId=str(tc.project_id),
                testCaseId=tc.test_case_id,
                expectedStatusCode=_extract_expected_status_code(tc.ai_meta_json),
                preconditions=_extract_preconditions(tc.ai_meta_json),
                postconditions=_extract_postconditions(tc.ai_meta_json),
                title=tc.title,
                type=tc.type,
                priority=tc.priority,
                status=tc.status,
                tags=tc.tags_json,
                ownerId=str(tc.owner_id) if tc.owner_id else None,
                ownerName=None,
                version=_format_version(tc.version),
                feature=tc.feature,
                apiMethod=tc.api_method,
                apiUrl=tc.api_url,
                apiParams=_extract_api_params(tc.ai_meta_json),
                apiHeaders=_extract_api_headers(tc.ai_meta_json),
                expectedResult=_extract_expected_result(tc.ai_meta_json),
                lastRun=latest_case_run.status if latest_case_run else None,
                updatedAt=to_unix_ts(tc.updated_at),
            )
        )

    return ApiResponse(
        data=PageData(page=page, pageSize=pageSize, total=total, items=items),
        requestId=request_id,
    )


@router.get("/owners", response_model=ApiResponse[list[TestCaseOwnerOption]])
async def owners(
    projectId: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[TestCaseOwnerOption]]:
    project_uuid = uuid.UUID(projectId)
    owner_options = await list_testcase_owner_options(
        db,
        user=user,
        project_id=project_uuid,
    )
    data = [TestCaseOwnerOption(id=str(item[0]), username=item[1]) for item in owner_options]
    return ApiResponse(data=data, requestId=request_id)


@router.get("/{id}", response_model=ApiResponse[TestCaseDetail])
async def get(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[TestCaseDetail]:
    testcase = await get_testcase(db, user=user, testcase_id=id)
    owner_name = await get_owner_name(db, user=user, owner_id=testcase.owner_id)
    return ApiResponse(
        data=TestCaseDetail(
            id=str(testcase.id),
            projectId=str(testcase.project_id),
            testCaseId=testcase.test_case_id,
            expectedStatusCode=_extract_expected_status_code(testcase.ai_meta_json),
            preconditions=_extract_preconditions(testcase.ai_meta_json),
            postconditions=_extract_postconditions(testcase.ai_meta_json),
            title=testcase.title,
            type=testcase.type,
            priority=testcase.priority,
            status=testcase.status,
            tags=testcase.tags_json,
            ownerId=str(testcase.owner_id) if testcase.owner_id else None,
            ownerName=owner_name,
            version=_format_version(testcase.version),
            contentMd=testcase.content_md,
            feature=testcase.feature,
            apiMethod=testcase.api_method,
            apiUrl=testcase.api_url,
            apiParams=_extract_api_params(testcase.ai_meta_json),
            apiHeaders=_extract_api_headers(testcase.ai_meta_json),
            expectedResult=_extract_expected_result(testcase.ai_meta_json),
        ),
        requestId=request_id,
    )


@router.put("/{id}", response_model=ApiResponse[TestCaseDetail])
async def update(
    id: uuid.UUID,
    payload: TestCasePutRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[TestCaseDetail]:
    try:
        testcase = await update_testcase(db, user=user, testcase_id=id, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return ApiResponse(
        data=TestCaseDetail(
            id=str(testcase.id),
            projectId=str(testcase.project_id),
            testCaseId=testcase.test_case_id,
            expectedStatusCode=_extract_expected_status_code(testcase.ai_meta_json),
            preconditions=_extract_preconditions(testcase.ai_meta_json),
            postconditions=_extract_postconditions(testcase.ai_meta_json),
            title=testcase.title,
            type=testcase.type,
            priority=testcase.priority,
            status=testcase.status,
            tags=testcase.tags_json,
            ownerId=str(testcase.owner_id) if testcase.owner_id else None,
            version=_format_version(testcase.version),
            contentMd=testcase.content_md,
            feature=testcase.feature,
            apiMethod=testcase.api_method,
            apiUrl=testcase.api_url,
            apiParams=_extract_api_params(testcase.ai_meta_json),
            apiHeaders=_extract_api_headers(testcase.ai_meta_json),
            expectedResult=_extract_expected_result(testcase.ai_meta_json),
        ),
        requestId=request_id,
    )

@router.delete("/{id}", response_model=ApiResponse[dict])
async def delete(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[dict]:
    try:
        await delete_testcase(db, user=user, testcase_id=id)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data={}, requestId=request_id)


@router.post("/{id}/archive", response_model=ApiResponse[TestCaseDetail])
async def archive(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[TestCaseDetail]:
    try:
        testcase = await archive_testcase(db, user=user, testcase_id=id)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    owner_name = await get_owner_name(db, user=user, owner_id=testcase.owner_id)
    return ApiResponse(
        data=TestCaseDetail(
            id=str(testcase.id),
            projectId=str(testcase.project_id),
            testCaseId=testcase.test_case_id,
            expectedStatusCode=_extract_expected_status_code(testcase.ai_meta_json),
            preconditions=_extract_preconditions(testcase.ai_meta_json),
            postconditions=_extract_postconditions(testcase.ai_meta_json),
            title=testcase.title,
            type=testcase.type,
            priority=testcase.priority,
            status=testcase.status,
            tags=testcase.tags_json,
            ownerId=str(testcase.owner_id) if testcase.owner_id else None,
            ownerName=owner_name,
            version=_format_version(testcase.version),
            contentMd=testcase.content_md,
            feature=testcase.feature,
            apiMethod=testcase.api_method,
            apiUrl=testcase.api_url,
            apiParams=_extract_api_params(testcase.ai_meta_json),
            apiHeaders=_extract_api_headers(testcase.ai_meta_json),
            expectedResult=_extract_expected_result(testcase.ai_meta_json),
        ),
        requestId=request_id,
    )


@router.post("/{id}/unarchive", response_model=ApiResponse[TestCaseDetail])
async def unarchive(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[TestCaseDetail]:
    try:
        testcase = await unarchive_testcase(db, user=user, testcase_id=id)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    owner_name = await get_owner_name(db, user=user, owner_id=testcase.owner_id)
    return ApiResponse(
        data=TestCaseDetail(
            id=str(testcase.id),
            projectId=str(testcase.project_id),
            testCaseId=testcase.test_case_id,
            expectedStatusCode=_extract_expected_status_code(testcase.ai_meta_json),
            preconditions=_extract_preconditions(testcase.ai_meta_json),
            postconditions=_extract_postconditions(testcase.ai_meta_json),
            title=testcase.title,
            type=testcase.type,
            priority=testcase.priority,
            status=testcase.status,
            tags=testcase.tags_json,
            ownerId=str(testcase.owner_id) if testcase.owner_id else None,
            ownerName=owner_name,
            version=_format_version(testcase.version),
            contentMd=testcase.content_md,
            feature=testcase.feature,
            apiMethod=testcase.api_method,
            apiUrl=testcase.api_url,
            apiParams=_extract_api_params(testcase.ai_meta_json),
            apiHeaders=_extract_api_headers(testcase.ai_meta_json),
            expectedResult=_extract_expected_result(testcase.ai_meta_json),
        ),
        requestId=request_id,
    )


@router.get("/{id}/versions", response_model=ApiResponse[list[TestCaseVersionSchema]])
async def list_versions(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[TestCaseVersionSchema]]:
    versions = await get_testcase_versions(db, user=user, testcase_id=id)

    data = [
        TestCaseVersionSchema(
            id=str(v.id),
            testcaseId=str(v.testcase_id),
            version=_format_version(v.version),
            contentMd=v.content_md,
            createdAt=to_unix_ts(v.created_at),
            createdBy=str(v.created_by) if v.created_by else None,
        )
        for v in versions
    ]
    return ApiResponse(data=data, requestId=request_id)


@router.post("/{id}/restore", response_model=ApiResponse[TestCaseDetail])
async def restore(
    id: uuid.UUID,
    payload: TestCaseRestoreRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[TestCaseDetail]:
    try:
        testcase = await restore_testcase_version(
            db,
            user=user,
            testcase_id=id,
            version_num=payload.version,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return ApiResponse(
        data=TestCaseDetail(
            id=str(testcase.id),
            projectId=str(testcase.project_id),
            testCaseId=testcase.test_case_id,
            expectedStatusCode=_extract_expected_status_code(testcase.ai_meta_json),
            preconditions=_extract_preconditions(testcase.ai_meta_json),
            postconditions=_extract_postconditions(testcase.ai_meta_json),
            title=testcase.title,
            type=testcase.type,
            priority=testcase.priority,
            status=testcase.status,
            tags=testcase.tags_json,
            ownerId=str(testcase.owner_id) if testcase.owner_id else None,
            version=_format_version(testcase.version),
            contentMd=testcase.content_md,
            feature=testcase.feature,
            apiMethod=testcase.api_method,
            apiUrl=testcase.api_url,
            apiParams=_extract_api_params(testcase.ai_meta_json),
            apiHeaders=_extract_api_headers(testcase.ai_meta_json),
            expectedResult=_extract_expected_result(testcase.ai_meta_json),
        ),
        requestId=request_id,
    )
