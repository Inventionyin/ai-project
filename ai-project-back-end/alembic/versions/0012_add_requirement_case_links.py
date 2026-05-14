"""add requirement case links

Revision ID: 0012_add_requirement_case_links
Revises: 0011_add_requirement_test_points_and_case_drafts
Create Date: 2026-05-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0012_add_requirement_case_links"
down_revision = "0011_add_requirement_test_points_and_case_drafts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "requirement_case_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doc_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doc_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("test_point_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("case_draft_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("testcase_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("link_type", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["requirement_analyses.id"]),
        sa.ForeignKeyConstraint(["case_draft_id"], ["generated_case_drafts.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["doc_id"], ["requirement_docs.id"]),
        sa.ForeignKeyConstraint(["doc_version_id"], ["requirement_doc_versions.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["test_point_id"], ["requirement_test_points.id"]),
        sa.ForeignKeyConstraint(["testcase_id"], ["testcases.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "project_id",
            "case_draft_id",
            "testcase_id",
            "link_type",
            name="uq_requirement_case_links_draft_case_type",
        ),
    )
    op.create_index(op.f("ix_requirement_case_links_analysis_id"), "requirement_case_links", ["analysis_id"], unique=False)
    op.create_index(op.f("ix_requirement_case_links_case_draft_id"), "requirement_case_links", ["case_draft_id"], unique=False)
    op.create_index(op.f("ix_requirement_case_links_created_by"), "requirement_case_links", ["created_by"], unique=False)
    op.create_index(op.f("ix_requirement_case_links_doc_id"), "requirement_case_links", ["doc_id"], unique=False)
    op.create_index(op.f("ix_requirement_case_links_doc_version_id"), "requirement_case_links", ["doc_version_id"], unique=False)
    op.create_index(op.f("ix_requirement_case_links_project_id"), "requirement_case_links", ["project_id"], unique=False)
    op.create_index(op.f("ix_requirement_case_links_tenant_id"), "requirement_case_links", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_requirement_case_links_test_point_id"), "requirement_case_links", ["test_point_id"], unique=False)
    op.create_index(op.f("ix_requirement_case_links_testcase_id"), "requirement_case_links", ["testcase_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_requirement_case_links_testcase_id"), table_name="requirement_case_links")
    op.drop_index(op.f("ix_requirement_case_links_test_point_id"), table_name="requirement_case_links")
    op.drop_index(op.f("ix_requirement_case_links_tenant_id"), table_name="requirement_case_links")
    op.drop_index(op.f("ix_requirement_case_links_project_id"), table_name="requirement_case_links")
    op.drop_index(op.f("ix_requirement_case_links_doc_version_id"), table_name="requirement_case_links")
    op.drop_index(op.f("ix_requirement_case_links_doc_id"), table_name="requirement_case_links")
    op.drop_index(op.f("ix_requirement_case_links_created_by"), table_name="requirement_case_links")
    op.drop_index(op.f("ix_requirement_case_links_case_draft_id"), table_name="requirement_case_links")
    op.drop_index(op.f("ix_requirement_case_links_analysis_id"), table_name="requirement_case_links")
    op.drop_table("requirement_case_links")
