from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.models.api import ApiCollection, ApiRequest
from app.models.api_target import ApiTarget
from app.models.enums import ProjectRole
from app.models.project import Project, ProjectMember
from app.models.test_data_set import TestDataSet
from app.models.testcase import TestCase
from app.models.testcase_binding import TestcaseBinding
from app.schemas.testcase_binding import TestcaseBindingCreateRequest, TestcaseBindingUpdateRequest
from app.services.platform_record import create_audit_log

_LINK_TYPES = {"API_TARGET", "REQUEST", "COLLECTION"}


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


async def _get_testcase(
    db: AsyncSession,
    *,
    user: CurrentUser,
    testcase_id: uuid.UUID,
) -> TestCase:
    testcase = await db.scalar(select(TestCase).where(TestCase.id == testcase_id, TestCase.tenant_id == user.tenant_id))
    if testcase is None:
        raise HTTPException(status_code=404, detail="TestCase not found")
    return testcase


async def _validate_dataset(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    dataset_id: uuid.UUID | None,
) -> None:
    if dataset_id is None:
        return
    dataset = await db.scalar(select(TestDataSet).where(TestDataSet.id == dataset_id, TestDataSet.tenant_id == user.tenant_id))
    if dataset is None:
        raise HTTPException(status_code=404, detail="dataset_not_found")
    if dataset.project_id != project_id:
        raise HTTPException(status_code=400, detail="dataset_not_in_project")


async def _validate_api_target(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    api_target_id: uuid.UUID | None,
) -> None:
    if api_target_id is None:
        return
    target = await db.scalar(select(ApiTarget).where(ApiTarget.id == api_target_id, ApiTarget.tenant_id == user.tenant_id))
    if target is None:
        raise HTTPException(status_code=404, detail="api_target_not_found")
    if target.project_id != project_id:
        raise HTTPException(status_code=400, detail="api_target_not_in_project")


async def _validate_collection(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    collection_id: uuid.UUID | None,
) -> ApiCollection | None:
    if collection_id is None:
        return None
    collection = await db.scalar(
        select(ApiCollection).where(ApiCollection.id == collection_id, ApiCollection.tenant_id == user.tenant_id)
    )
    if collection is None:
        raise HTTPException(status_code=404, detail="collection_not_found")
    if collection.project_id != project_id:
        raise HTTPException(status_code=400, detail="collection_not_in_project")
    return collection


async def _validate_request(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    request_id: uuid.UUID | None,
) -> ApiRequest | None:
    if request_id is None:
        return None
    request = await db.scalar(select(ApiRequest).where(ApiRequest.id == request_id, ApiRequest.tenant_id == user.tenant_id))
    if request is None:
        raise HTTPException(status_code=404, detail="request_not_found")
    await _validate_collection(db, user=user, project_id=project_id, collection_id=request.collection_id)
    return request


def _resolve_link_type(payload: TestcaseBindingCreateRequest | TestcaseBindingUpdateRequest) -> str:
    if payload.linkType:
        link_type = payload.linkType.upper()
        if link_type not in _LINK_TYPES:
            raise HTTPException(status_code=400, detail="invalid_link_type")
        return link_type
    if payload.requestId:
        return "REQUEST"
    if payload.collectionId:
        return "COLLECTION"
    return "API_TARGET"


def _validate_link_consistency(
    *,
    link_type: str,
    api_target_id: uuid.UUID | None,
    request: ApiRequest | None,
    collection: ApiCollection | None,
) -> None:
    if link_type == "REQUEST" and request is None:
        raise HTTPException(status_code=400, detail="request_id_required")
    if link_type == "COLLECTION" and collection is None:
        raise HTTPException(status_code=400, detail="collection_id_required")
    if link_type == "API_TARGET" and (request is not None or collection is not None):
        raise HTTPException(status_code=400, detail="api_target_link_cannot_reference_request_or_collection")
    if api_target_id is not None and (request is not None or collection is not None):
        raise HTTPException(status_code=400, detail="api_target_cannot_mix_with_api_asset_link")
    if request is not None and collection is not None and request.collection_id != collection.id:
        raise HTTPException(status_code=400, detail="request_not_in_collection")


async def get_testcase_binding(
    db: AsyncSession,
    *,
    user: CurrentUser,
    binding_id: uuid.UUID,
) -> TestcaseBinding:
    binding = await db.scalar(
        select(TestcaseBinding).where(
            TestcaseBinding.id == binding_id,
            TestcaseBinding.tenant_id == user.tenant_id,
        )
    )
    if binding is None:
        raise HTTPException(status_code=404, detail="binding_not_found")
    project = await _get_project(db, user=user, project_id=binding.project_id)
    await _require_project_read(db, user=user, project=project)
    return binding


async def list_testcase_bindings(
    db: AsyncSession,
    *,
    user: CurrentUser,
    testcase_id: uuid.UUID,
    page: int,
    page_size: int,
) -> tuple[int, list[TestcaseBinding]]:
    testcase = await _get_testcase(db, user=user, testcase_id=testcase_id)
    project = await _get_project(db, user=user, project_id=testcase.project_id)
    await _require_project_read(db, user=user, project=project)

    base_stmt = select(TestcaseBinding).where(
        TestcaseBinding.tenant_id == user.tenant_id,
        TestcaseBinding.testcase_id == testcase.id,
    )
    total = int((await db.execute(select(func.count()).select_from(base_stmt.subquery()))).scalar_one() or 0)
    rows = (
        await db.execute(
            base_stmt.order_by(desc(TestcaseBinding.updated_at)).offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars()
    return total, list(rows.all())


async def list_testcase_bindings_by_request(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    request_id: uuid.UUID,
) -> list[TestcaseBinding]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    await _validate_request(db, user=user, project_id=project.id, request_id=request_id)
    rows = (
        await db.execute(
            select(TestcaseBinding)
            .where(
                TestcaseBinding.tenant_id == user.tenant_id,
                TestcaseBinding.project_id == project.id,
                TestcaseBinding.request_id == request_id,
            )
            .order_by(desc(TestcaseBinding.updated_at))
        )
    ).scalars()
    return list(rows.all())


async def list_testcase_bindings_by_collection(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    collection_id: uuid.UUID,
) -> list[TestcaseBinding]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    await _validate_collection(db, user=user, project_id=project.id, collection_id=collection_id)
    request_ids = select(ApiRequest.id).where(ApiRequest.tenant_id == user.tenant_id, ApiRequest.collection_id == collection_id)
    rows = (
        await db.execute(
            select(TestcaseBinding)
            .where(
                TestcaseBinding.tenant_id == user.tenant_id,
                TestcaseBinding.project_id == project.id,
                or_(TestcaseBinding.collection_id == collection_id, TestcaseBinding.request_id.in_(request_ids)),
            )
            .order_by(desc(TestcaseBinding.updated_at))
        )
    ).scalars()
    return list(rows.all())


async def create_testcase_binding(
    db: AsyncSession,
    *,
    user: CurrentUser,
    testcase_id: uuid.UUID,
    payload: TestcaseBindingCreateRequest,
) -> TestcaseBinding:
    testcase = await _get_testcase(db, user=user, testcase_id=testcase_id)
    project = await _get_project(db, user=user, project_id=testcase.project_id)
    await _require_project_write(db, user=user, project=project)

    dataset_id = uuid.UUID(payload.datasetId) if payload.datasetId else None
    api_target_id = uuid.UUID(payload.apiTargetId) if payload.apiTargetId else None
    request_id = uuid.UUID(payload.requestId) if payload.requestId else None
    collection_id = uuid.UUID(payload.collectionId) if payload.collectionId else None
    await _validate_dataset(db, user=user, project_id=project.id, dataset_id=dataset_id)
    await _validate_api_target(db, user=user, project_id=project.id, api_target_id=api_target_id)
    request = await _validate_request(db, user=user, project_id=project.id, request_id=request_id)
    collection = await _validate_collection(db, user=user, project_id=project.id, collection_id=collection_id)
    link_type = _resolve_link_type(payload)
    _validate_link_consistency(link_type=link_type, api_target_id=api_target_id, request=request, collection=collection)

    binding = TestcaseBinding(
        tenant_id=user.tenant_id,
        project_id=project.id,
        testcase_id=testcase.id,
        name=payload.name,
        dataset_id=dataset_id,
        api_target_id=api_target_id,
        request_id=request_id,
        collection_id=collection_id,
        params_json=dict(payload.params or {}),
        link_type=link_type,
        source_type=payload.sourceType.upper(),
        assert_summary=payload.assertSummary,
        priority=payload.priority,
        enabled=payload.enabled,
        version=1,
        created_by=user.id,
    )
    db.add(binding)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="binding_name_conflict") from exc
    await create_audit_log(
        db,
        user=user,
        project_id=project.id,
        module="TESTCASE_BINDING",
        action="CREATE",
        resource_type="testcase_binding",
        resource_id=str(binding.id),
        summary=f"创建用例绑定：{binding.name}",
        detail={"testcaseId": str(testcase.id)},
    )
    return binding


async def update_testcase_binding(
    db: AsyncSession,
    *,
    user: CurrentUser,
    binding_id: uuid.UUID,
    payload: TestcaseBindingUpdateRequest,
) -> TestcaseBinding:
    binding = await get_testcase_binding(db, user=user, binding_id=binding_id)
    project = await _get_project(db, user=user, project_id=binding.project_id)
    await _require_project_write(db, user=user, project=project)

    if binding.version != payload.version:
        raise HTTPException(status_code=409, detail="version_conflict")

    dataset_id = uuid.UUID(payload.datasetId) if payload.datasetId else None
    api_target_id = uuid.UUID(payload.apiTargetId) if payload.apiTargetId else None
    request_id = uuid.UUID(payload.requestId) if payload.requestId else None
    collection_id = uuid.UUID(payload.collectionId) if payload.collectionId else None
    await _validate_dataset(db, user=user, project_id=project.id, dataset_id=dataset_id)
    await _validate_api_target(db, user=user, project_id=project.id, api_target_id=api_target_id)
    request = await _validate_request(db, user=user, project_id=project.id, request_id=request_id)
    collection = await _validate_collection(db, user=user, project_id=project.id, collection_id=collection_id)
    link_type = _resolve_link_type(payload)
    _validate_link_consistency(link_type=link_type, api_target_id=api_target_id, request=request, collection=collection)

    binding.name = payload.name
    binding.dataset_id = dataset_id
    binding.api_target_id = api_target_id
    binding.request_id = request_id
    binding.collection_id = collection_id
    binding.params_json = dict(payload.params or {})
    binding.link_type = link_type
    binding.source_type = payload.sourceType.upper()
    binding.assert_summary = payload.assertSummary
    binding.priority = payload.priority
    binding.enabled = payload.enabled
    binding.version += 1
    try:
        await db.flush()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="binding_name_conflict") from exc
    await create_audit_log(
        db,
        user=user,
        project_id=project.id,
        module="TESTCASE_BINDING",
        action="UPDATE",
        resource_type="testcase_binding",
        resource_id=str(binding.id),
        summary=f"更新用例绑定：{binding.name}",
        detail={"version": binding.version},
    )
    return binding


async def delete_testcase_binding(
    db: AsyncSession,
    *,
    user: CurrentUser,
    binding_id: uuid.UUID,
) -> None:
    binding = await get_testcase_binding(db, user=user, binding_id=binding_id)
    project = await _get_project(db, user=user, project_id=binding.project_id)
    await _require_project_write(db, user=user, project=project)
    await create_audit_log(
        db,
        user=user,
        project_id=project.id,
        module="TESTCASE_BINDING",
        action="DELETE",
        resource_type="testcase_binding",
        resource_id=str(binding.id),
        summary=f"删除用例绑定：{binding.name}",
        detail={"testcaseId": str(binding.testcase_id)},
    )
    await db.delete(binding)
