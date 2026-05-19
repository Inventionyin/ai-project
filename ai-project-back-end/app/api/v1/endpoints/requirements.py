from __future__ import annotations

import uuid

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.common import ApiResponse, PageData
from app.schemas.requirement import (
    BulkApproveCaseDraftsRequest,
    BulkApproveCaseDraftsResult,
    GenerateCaseDraftsRequest,
    GeneratedCaseDraftDetail,
    RequirementCaseLinkDetail,
    RequirementAnalysisDetail,
    RequirementAnalysisGenerateRequest,
    RequirementAnalysisUpdateRequest,
    RequirementDocCreateRequest,
    RequirementDocDetail,
    RequirementDocUpdateRequest,
    RequirementDocVersionDetail,
    RequirementTestPointDetail,
    RequirementTestPointUpdateRequest,
)
from app.schemas.requirement_change import RequirementAnalysisRevisionDetail, RequirementAnalysisRollbackRequest
from app.services.requirement import (
    bulk_approve_case_drafts,
    create_requirement_doc,
    create_requirement_doc_version,
    create_requirement_doc_version_from_bytes,
    delete_requirement_doc,
    generate_case_drafts_from_analysis,
    generate_requirement_analysis,
    get_requirement_analysis,
    get_requirement_doc,
    get_requirement_doc_version_parsed_text,
    list_generated_case_drafts,
    list_requirement_analysis_revisions,
    list_requirement_case_links,
    list_requirement_analyses,
    list_requirement_doc_versions,
    list_requirement_docs,
    list_requirement_test_points,
    parse_requirement_doc_version,
    sync_requirement_test_points,
    rollback_requirement_analysis_revision,
    rollback_requirement_doc_version,
    update_requirement_test_point,
    update_requirement_analysis,
    update_requirement_doc,
)

router = APIRouter(prefix="/projects/{projectId}/requirements")


@router.get("/docs", response_model=ApiResponse[PageData[RequirementDocDetail]])
async def list_docs(
    projectId: uuid.UUID,
    page: int = 1,
    pageSize: int = 20,
    status: str | None = None,
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[RequirementDocDetail]]:
    total, items = await list_requirement_docs(
        db,
        user=user,
        project_id=projectId,
        page=page,
        page_size=pageSize,
        status=status,
        q=q,
    )
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=items), requestId=request_id)


@router.post("/docs", response_model=ApiResponse[RequirementDocDetail])
async def create_doc(
    projectId: uuid.UUID,
    payload: RequirementDocCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RequirementDocDetail]:
    try:
        data = await create_requirement_doc(db, user=user, project_id=projectId, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.get("/docs/{docId}", response_model=ApiResponse[RequirementDocDetail])
async def get_doc(
    projectId: uuid.UUID,
    docId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RequirementDocDetail]:
    data = await get_requirement_doc(db, user=user, project_id=projectId, doc_id=docId)
    return ApiResponse(data=data, requestId=request_id)


@router.put("/docs/{docId}", response_model=ApiResponse[RequirementDocDetail])
async def update_doc(
    projectId: uuid.UUID,
    docId: uuid.UUID,
    payload: RequirementDocUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RequirementDocDetail]:
    try:
        data = await update_requirement_doc(db, user=user, project_id=projectId, doc_id=docId, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.delete("/docs/{docId}", response_model=ApiResponse[dict])
async def delete_doc(
    projectId: uuid.UUID,
    docId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[dict]:
    try:
        await delete_requirement_doc(db, user=user, project_id=projectId, doc_id=docId)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data={}, requestId=request_id)


@router.get("/docs/{docId}/versions", response_model=ApiResponse[list[RequirementDocVersionDetail]])
async def list_versions(
    projectId: uuid.UUID,
    docId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[RequirementDocVersionDetail]]:
    data = await list_requirement_doc_versions(db, user=user, project_id=projectId, doc_id=docId)
    return ApiResponse(data=data, requestId=request_id)


@router.post("/docs/{docId}/versions", response_model=ApiResponse[RequirementDocVersionDetail])
async def create_version(
    projectId: uuid.UUID,
    docId: uuid.UUID,
    file: UploadFile = File(...),
    changeSummary: str | None = Form(default=None),
    effectiveScope: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RequirementDocVersionDetail]:
    try:
        data = await create_requirement_doc_version(
            db,
            user=user,
            project_id=projectId,
            doc_id=docId,
            upload_file=file,
            change_summary=changeSummary,
            effective_scope=effectiveScope,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.post("/docs/{docId}/versions/import-url", response_model=ApiResponse[dict])
async def import_doc_version_from_url(
    projectId: uuid.UUID,
    docId: uuid.UUID,
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[dict]:
    """Import a document version from a URL."""
    import asyncio
    import requests as req_lib
    from urllib.parse import urlparse

    url = str(payload.get("url", "")).strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    change_summary = str(payload.get("changeSummary", "")).strip()
    effective_scope = str(payload.get("effectiveScope", "")).strip()

    # Fetch content from URL
    def _fetch() -> tuple[bytes, str]:
        resp = req_lib.get(url, timeout=30, allow_redirects=True)
        resp.raise_for_status()
        return resp.content, resp.headers.get("content-type", "")

    try:
        content, content_type = await asyncio.to_thread(_fetch)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {e}")

    # Determine filename from URL
    parsed = urlparse(url)
    filename = parsed.path.split("/")[-1] or "imported-doc"
    if "." not in filename:
        if "markdown" in content_type or "md" in content_type:
            filename += ".md"
        elif "html" in content_type:
            filename += ".html"
        elif "pdf" in content_type:
            filename += ".pdf"
        else:
            filename += ".txt"

    # Create version using service
    try:
        version = await create_requirement_doc_version_from_bytes(
            db,
            user=user,
            doc_id=docId,
            content=content,
            filename=filename,
            change_summary=change_summary,
            effective_scope=effective_scope,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return ApiResponse(data={"id": str(version.id), "version": version.version}, requestId=request_id)


@router.post("/docs/{docId}/versions/{versionId}/parse", response_model=ApiResponse[dict])
async def parse_version(
    projectId: uuid.UUID,
    docId: uuid.UUID,
    versionId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[dict]:
    try:
        data = await parse_requirement_doc_version(db, user=user, project_id=projectId, doc_id=docId, version_id=versionId)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.get("/docs/{docId}/versions/{versionId}/parsed-text", response_model=ApiResponse[dict])
async def get_parsed_text(
    projectId: uuid.UUID,
    docId: uuid.UUID,
    versionId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[dict]:
    data = await get_requirement_doc_version_parsed_text(db, user=user, project_id=projectId, doc_id=docId, version_id=versionId)
    return ApiResponse(data=data, requestId=request_id)


@router.post("/docs/{docId}/versions/{versionId}/analyze", response_model=ApiResponse[RequirementAnalysisDetail])
async def analyze_version(
    projectId: uuid.UUID,
    docId: uuid.UUID,
    versionId: uuid.UUID,
    payload: RequirementAnalysisGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RequirementAnalysisDetail]:
    try:
        data = await generate_requirement_analysis(
            db,
            user=user,
            project_id=projectId,
            doc_id=docId,
            version_id=versionId,
            instruction=payload.instruction,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.post("/docs/{docId}/rollback", response_model=ApiResponse[dict])
async def rollback_doc_version(
    projectId: uuid.UUID,
    docId: uuid.UUID,
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[dict]:
    version_id = uuid.UUID(str(payload.get("versionId", "")))
    if not version_id:
        raise HTTPException(status_code=400, detail="versionId is required")
    try:
        doc = await rollback_requirement_doc_version(
            db, user=user, project_id=projectId, doc_id=docId, version_id=version_id,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data={"id": str(doc.id), "currentVersionId": str(doc.current_version_id)}, requestId=request_id)


@router.get("/analyses", response_model=ApiResponse[list[RequirementAnalysisDetail]])
async def list_analyses(
    projectId: uuid.UUID,
    docId: uuid.UUID | None = None,
    versionId: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[RequirementAnalysisDetail]]:
    data = await list_requirement_analyses(db, user=user, project_id=projectId, doc_id=docId, version_id=versionId)
    return ApiResponse(data=data, requestId=request_id)


@router.get("/analyses/{analysisId}", response_model=ApiResponse[RequirementAnalysisDetail])
async def get_analysis(
    projectId: uuid.UUID,
    analysisId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RequirementAnalysisDetail]:
    data = await get_requirement_analysis(db, user=user, project_id=projectId, analysis_id=analysisId)
    return ApiResponse(data=data, requestId=request_id)


@router.put("/analyses/{analysisId}", response_model=ApiResponse[RequirementAnalysisDetail])
async def update_analysis(
    projectId: uuid.UUID,
    analysisId: uuid.UUID,
    payload: RequirementAnalysisUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RequirementAnalysisDetail]:
    try:
        data = await update_requirement_analysis(db, user=user, project_id=projectId, analysis_id=analysisId, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.get("/analyses/{analysisId}/revisions", response_model=ApiResponse[list[RequirementAnalysisRevisionDetail]])
async def list_analysis_revisions(
    projectId: uuid.UUID,
    analysisId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[RequirementAnalysisRevisionDetail]]:
    data = await list_requirement_analysis_revisions(db, user=user, project_id=projectId, analysis_id=analysisId)
    return ApiResponse(data=data, requestId=request_id)


@router.post("/analyses/{analysisId}/rollback", response_model=ApiResponse[RequirementAnalysisDetail])
async def rollback_analysis_revision(
    projectId: uuid.UUID,
    analysisId: uuid.UUID,
    payload: RequirementAnalysisRollbackRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RequirementAnalysisDetail]:
    try:
        data = await rollback_requirement_analysis_revision(
            db,
            user=user,
            project_id=projectId,
            analysis_id=analysisId,
            revision_id=uuid.UUID(payload.revisionId),
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.post("/analyses/{analysisId}/sync-test-points", response_model=ApiResponse[list[RequirementTestPointDetail]])
async def sync_test_points(
    projectId: uuid.UUID,
    analysisId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[RequirementTestPointDetail]]:
    try:
        data = await sync_requirement_test_points(db, user=user, project_id=projectId, analysis_id=analysisId)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.get("/analyses/{analysisId}/test-points", response_model=ApiResponse[list[RequirementTestPointDetail]])
async def list_test_points(
    projectId: uuid.UUID,
    analysisId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[RequirementTestPointDetail]]:
    data = await list_requirement_test_points(db, user=user, project_id=projectId, analysis_id=analysisId)
    return ApiResponse(data=data, requestId=request_id)


@router.put("/test-points/{testPointId}", response_model=ApiResponse[RequirementTestPointDetail])
async def update_test_point(
    projectId: uuid.UUID,
    testPointId: uuid.UUID,
    payload: RequirementTestPointUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RequirementTestPointDetail]:
    try:
        data = await update_requirement_test_point(db, user=user, project_id=projectId, test_point_id=testPointId, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.post("/analyses/{analysisId}/generate-case-drafts", response_model=ApiResponse[list[GeneratedCaseDraftDetail]])
async def generate_case_drafts(
    projectId: uuid.UUID,
    analysisId: uuid.UUID,
    payload: GenerateCaseDraftsRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[GeneratedCaseDraftDetail]]:
    try:
        data = await generate_case_drafts_from_analysis(
            db,
            user=user,
            project_id=projectId,
            analysis_id=analysisId,
            payload=payload,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.get("/analyses/{analysisId}/case-drafts", response_model=ApiResponse[list[GeneratedCaseDraftDetail]])
async def list_case_drafts(
    projectId: uuid.UUID,
    analysisId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[GeneratedCaseDraftDetail]]:
    data = await list_generated_case_drafts(db, user=user, project_id=projectId, analysis_id=analysisId)
    return ApiResponse(data=data, requestId=request_id)


@router.get("/analyses/{analysisId}/case-links", response_model=ApiResponse[list[RequirementCaseLinkDetail]])
async def list_case_links(
    projectId: uuid.UUID,
    analysisId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[RequirementCaseLinkDetail]]:
    data = await list_requirement_case_links(db, user=user, project_id=projectId, analysis_id=analysisId)
    return ApiResponse(data=data, requestId=request_id)


@router.post("/case-drafts/bulk-approve", response_model=ApiResponse[BulkApproveCaseDraftsResult])
async def bulk_approve_drafts(
    projectId: uuid.UUID,
    payload: BulkApproveCaseDraftsRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[BulkApproveCaseDraftsResult]:
    try:
        data = await bulk_approve_case_drafts(db, user=user, project_id=projectId, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)
