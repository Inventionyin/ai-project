"""expand testcase bindings for api links

Revision ID: 0015_expand_testcase_bindings_for_api_links
Revises: 0014_add_requirement_change_analysis_and_revisions
Create Date: 2026-05-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0015_expand_testcase_bindings_for_api_links"
down_revision = "0014_add_requirement_change_analysis_and_revisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("testcase_bindings", sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("testcase_bindings", sa.Column("collection_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column(
        "testcase_bindings",
        sa.Column("link_type", sa.String(length=32), nullable=False, server_default="API_TARGET"),
    )
    op.add_column(
        "testcase_bindings",
        sa.Column("source_type", sa.String(length=32), nullable=False, server_default="MANUAL"),
    )
    op.add_column(
        "testcase_bindings",
        sa.Column("assert_summary", sa.String(length=255), nullable=False, server_default=""),
    )
    op.add_column("testcase_bindings", sa.Column("last_run_status", sa.String(length=32), nullable=True))
    op.add_column("testcase_bindings", sa.Column("last_run_at", sa.DateTime(), nullable=True))

    op.create_foreign_key(
        "fk_testcase_bindings_request_id_api_requests",
        "testcase_bindings",
        "api_requests",
        ["request_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_testcase_bindings_collection_id_api_collections",
        "testcase_bindings",
        "api_collections",
        ["collection_id"],
        ["id"],
    )
    op.create_index(op.f("ix_testcase_bindings_request_id"), "testcase_bindings", ["request_id"], unique=False)
    op.create_index(op.f("ix_testcase_bindings_collection_id"), "testcase_bindings", ["collection_id"], unique=False)

    op.alter_column("testcase_bindings", "link_type", server_default=None)
    op.alter_column("testcase_bindings", "source_type", server_default=None)
    op.alter_column("testcase_bindings", "assert_summary", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_testcase_bindings_collection_id"), table_name="testcase_bindings")
    op.drop_index(op.f("ix_testcase_bindings_request_id"), table_name="testcase_bindings")
    op.drop_constraint("fk_testcase_bindings_collection_id_api_collections", "testcase_bindings", type_="foreignkey")
    op.drop_constraint("fk_testcase_bindings_request_id_api_requests", "testcase_bindings", type_="foreignkey")
    op.drop_column("testcase_bindings", "last_run_at")
    op.drop_column("testcase_bindings", "last_run_status")
    op.drop_column("testcase_bindings", "assert_summary")
    op.drop_column("testcase_bindings", "source_type")
    op.drop_column("testcase_bindings", "link_type")
    op.drop_column("testcase_bindings", "collection_id")
    op.drop_column("testcase_bindings", "request_id")
