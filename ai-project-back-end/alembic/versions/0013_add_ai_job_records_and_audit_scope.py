"""add ai job records and audit scope

Revision ID: 0013_add_ai_job_records_and_audit_scope
Revises: 0012_add_requirement_case_links
Create Date: 2026-05-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0013_add_ai_job_records_and_audit_scope"
down_revision = "0012_add_requirement_case_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_job_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("trigger_source", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("detail_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_job_records_tenant_id"), "ai_job_records", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_ai_job_records_project_id"), "ai_job_records", ["project_id"], unique=False)
    op.create_index(op.f("ix_ai_job_records_created_by"), "ai_job_records", ["created_by"], unique=False)

    op.add_column("audit_logs", sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("audit_logs", sa.Column("module", sa.String(length=64), nullable=True))
    op.add_column("audit_logs", sa.Column("summary", sa.String(length=255), nullable=True))
    op.create_foreign_key("fk_audit_logs_project_id_projects", "audit_logs", "projects", ["project_id"], ["id"])
    op.create_index(op.f("ix_audit_logs_project_id"), "audit_logs", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_project_id"), table_name="audit_logs")
    op.drop_constraint("fk_audit_logs_project_id_projects", "audit_logs", type_="foreignkey")
    op.drop_column("audit_logs", "summary")
    op.drop_column("audit_logs", "module")
    op.drop_column("audit_logs", "project_id")

    op.drop_index(op.f("ix_ai_job_records_created_by"), table_name="ai_job_records")
    op.drop_index(op.f("ix_ai_job_records_project_id"), table_name="ai_job_records")
    op.drop_index(op.f("ix_ai_job_records_tenant_id"), table_name="ai_job_records")
    op.drop_table("ai_job_records")
