from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest
from fastapi import HTTPException

from app.api.deps import CurrentUser
from app.models.project import Project
from app.services.project import _project_read_filter, get_home_stats, get_project


def _compile_filter(user: CurrentUser) -> str:
    return str(_project_read_filter(user).compile(compile_kwargs={"literal_binds": True}))


def test_project_read_filter_allows_admins_to_see_all_projects() -> None:
    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset({"ADMIN"}),
    )

    assert _compile_filter(user) == "true"


def test_project_read_filter_scopes_regular_users_to_owned_or_member_projects() -> None:
    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset({"Viewer"}),
    )

    sql = _compile_filter(user)

    assert "projects.owner_id" in sql
    assert "project_members.project_id" in sql
    assert "project_members.user_id" in sql
    assert "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" in sql
    assert "11111111111111111111111111111111" in sql


@dataclass
class _ScalarResult:
    value: object

    def scalar_one(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value


@dataclass
class _RowsResult:
    rows: list[object]

    def all(self):
        return self.rows


class _HomeStatsCaptureDb:
    def __init__(self) -> None:
        self.sql: list[str] = []

    async def execute(self, stmt):
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        self.sql.append(compiled)
        if "GROUP BY runs.status" in compiled:
            return _RowsResult([])
        return _ScalarResult(0)


class _ForbiddenProjectDb:
    async def execute(self, stmt):
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        if "FROM projects" in compiled:
            return _ScalarResult(
                Project(
                    id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
                    tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
                    name="other project",
                    owner_id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
                )
            )
        if "FROM project_members" in compiled:
            return _ScalarResult(None)
        return _ScalarResult(0)


@pytest.mark.anyio
async def test_home_stats_scopes_counts_to_readable_projects() -> None:
    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset({"Viewer"}),
    )
    db = _HomeStatsCaptureDb()

    await get_home_stats(db, user=user)

    sql = "\n".join(db.sql)
    assert "project_members.project_id" in sql
    assert "testcases.project_id" in sql
    assert "runs.project_id" in sql
    assert "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" in sql


@pytest.mark.anyio
async def test_get_project_rejects_unowned_project_without_membership() -> None:
    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset({"Viewer"}),
    )

    with pytest.raises(HTTPException) as exc:
        await get_project(
            _ForbiddenProjectDb(),
            user=user,
            project_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "No access to this project"
