"""add requirement change analysis and revisions

Revision ID: 0014_add_requirement_change_analysis_and_revisions
Revises: 0013_add_ai_job_records_and_audit_scope
Create Date: 2026-05-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0014_add_requirement_change_analysis_and_revisions"
down_revision = "0013_add_ai_job_records_and_audit_scope"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "requirement_analysis_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doc_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doc_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("change_reason", sa.String(length=64), nullable=False),
        sa.Column("analysis_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("coverage_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["analysis_id"], ["requirement_analyses.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["doc_id"], ["requirement_docs.id"]),
        sa.ForeignKeyConstraint(["doc_version_id"], ["requirement_doc_versions.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_id", "revision_no", name="uq_requirement_analysis_revisions_analysis_revision_no"),
    )
    op.create_index(op.f("ix_requirement_analysis_revisions_analysis_id"), "requirement_analysis_revisions", ["analysis_id"], unique=False)
    op.create_index(op.f("ix_requirement_analysis_revisions_created_by"), "requirement_analysis_revisions", ["created_by"], unique=False)
    op.create_index(op.f("ix_requirement_analysis_revisions_doc_id"), "requirement_analysis_revisions", ["doc_id"], unique=False)
    op.create_index(op.f("ix_requirement_analysis_revisions_doc_version_id"), "requirement_analysis_revisions", ["doc_version_id"], unique=False)
    op.create_index(op.f("ix_requirement_analysis_revisions_project_id"), "requirement_analysis_revisions", ["project_id"], unique=False)
    op.create_index(op.f("ix_requirement_analysis_revisions_tenant_id"), "requirement_analysis_revisions", ["tenant_id"], unique=False)

    op.create_table(
        "requirement_change_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doc_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("baseline_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["baseline_version_id"], ["requirement_doc_versions.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["doc_id"], ["requirement_docs.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["target_version_id"], ["requirement_doc_versions.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_requirement_change_sets_baseline_version_id"), "requirement_change_sets", ["baseline_version_id"], unique=False)
    op.create_index(op.f("ix_requirement_change_sets_created_by"), "requirement_change_sets", ["created_by"], unique=False)
    op.create_index(op.f("ix_requirement_change_sets_doc_id"), "requirement_change_sets", ["doc_id"], unique=False)
    op.create_index(op.f("ix_requirement_change_sets_project_id"), "requirement_change_sets", ["project_id"], unique=False)
    op.create_index(op.f("ix_requirement_change_sets_target_version_id"), "requirement_change_sets", ["target_version_id"], unique=False)
    op.create_index(op.f("ix_requirement_change_sets_tenant_id"), "requirement_change_sets", ["tenant_id"], unique=False)

    op.create_table(
        "requirement_change_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("change_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("change_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("impact_level", sa.String(length=16), nullable=False),
        sa.Column("source_path", sa.String(length=255), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["change_set_id"], ["requirement_change_sets.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_requirement_change_items_change_set_id"), "requirement_change_items", ["change_set_id"], unique=False)
    op.create_index(op.f("ix_requirement_change_items_created_by"), "requirement_change_items", ["created_by"], unique=False)
    op.create_index(op.f("ix_requirement_change_items_project_id"), "requirement_change_items", ["project_id"], unique=False)
    op.create_index(op.f("ix_requirement_change_items_tenant_id"), "requirement_change_items", ["tenant_id"], unique=False)

    op.create_table(
        "requirement_regression_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("change_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["change_set_id"], ["requirement_change_sets.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "project_id",
            "change_set_id",
            name="uq_requirement_regression_sets_tenant_project_change_set",
        ),
    )
    op.create_index(op.f("ix_requirement_regression_sets_change_set_id"), "requirement_regression_sets", ["change_set_id"], unique=False)
    op.create_index(op.f("ix_requirement_regression_sets_created_by"), "requirement_regression_sets", ["created_by"], unique=False)
    op.create_index(op.f("ix_requirement_regression_sets_project_id"), "requirement_regression_sets", ["project_id"], unique=False)
    op.create_index(op.f("ix_requirement_regression_sets_tenant_id"), "requirement_regression_sets", ["tenant_id"], unique=False)

    op.create_table(
        "requirement_regression_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("regression_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("testcase_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("source_paths_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["regression_set_id"], ["requirement_regression_sets.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["testcase_id"], ["testcases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_requirement_regression_cases_created_by"), "requirement_regression_cases", ["created_by"], unique=False)
    op.create_index(op.f("ix_requirement_regression_cases_project_id"), "requirement_regression_cases", ["project_id"], unique=False)
    op.create_index(op.f("ix_requirement_regression_cases_regression_set_id"), "requirement_regression_cases", ["regression_set_id"], unique=False)
    op.create_index(op.f("ix_requirement_regression_cases_tenant_id"), "requirement_regression_cases", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_requirement_regression_cases_testcase_id"), "requirement_regression_cases", ["testcase_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_requirement_regression_cases_testcase_id"), table_name="requirement_regression_cases")
    op.drop_index(op.f("ix_requirement_regression_cases_tenant_id"), table_name="requirement_regression_cases")
    op.drop_index(op.f("ix_requirement_regression_cases_regression_set_id"), table_name="requirement_regression_cases")
    op.drop_index(op.f("ix_requirement_regression_cases_project_id"), table_name="requirement_regression_cases")
    op.drop_index(op.f("ix_requirement_regression_cases_created_by"), table_name="requirement_regression_cases")
    op.drop_table("requirement_regression_cases")

    op.drop_index(op.f("ix_requirement_regression_sets_tenant_id"), table_name="requirement_regression_sets")
    op.drop_index(op.f("ix_requirement_regression_sets_project_id"), table_name="requirement_regression_sets")
    op.drop_index(op.f("ix_requirement_regression_sets_created_by"), table_name="requirement_regression_sets")
    op.drop_index(op.f("ix_requirement_regression_sets_change_set_id"), table_name="requirement_regression_sets")
    op.drop_table("requirement_regression_sets")

    op.drop_index(op.f("ix_requirement_change_items_tenant_id"), table_name="requirement_change_items")
    op.drop_index(op.f("ix_requirement_change_items_project_id"), table_name="requirement_change_items")
    op.drop_index(op.f("ix_requirement_change_items_created_by"), table_name="requirement_change_items")
    op.drop_index(op.f("ix_requirement_change_items_change_set_id"), table_name="requirement_change_items")
    op.drop_table("requirement_change_items")

    op.drop_index(op.f("ix_requirement_change_sets_tenant_id"), table_name="requirement_change_sets")
    op.drop_index(op.f("ix_requirement_change_sets_target_version_id"), table_name="requirement_change_sets")
    op.drop_index(op.f("ix_requirement_change_sets_project_id"), table_name="requirement_change_sets")
    op.drop_index(op.f("ix_requirement_change_sets_doc_id"), table_name="requirement_change_sets")
    op.drop_index(op.f("ix_requirement_change_sets_created_by"), table_name="requirement_change_sets")
    op.drop_index(op.f("ix_requirement_change_sets_baseline_version_id"), table_name="requirement_change_sets")
    op.drop_table("requirement_change_sets")

    op.drop_index(op.f("ix_requirement_analysis_revisions_tenant_id"), table_name="requirement_analysis_revisions")
    op.drop_index(op.f("ix_requirement_analysis_revisions_project_id"), table_name="requirement_analysis_revisions")
    op.drop_index(op.f("ix_requirement_analysis_revisions_doc_version_id"), table_name="requirement_analysis_revisions")
    op.drop_index(op.f("ix_requirement_analysis_revisions_doc_id"), table_name="requirement_analysis_revisions")
    op.drop_index(op.f("ix_requirement_analysis_revisions_created_by"), table_name="requirement_analysis_revisions")
    op.drop_index(op.f("ix_requirement_analysis_revisions_analysis_id"), table_name="requirement_analysis_revisions")
    op.drop_table("requirement_analysis_revisions")
