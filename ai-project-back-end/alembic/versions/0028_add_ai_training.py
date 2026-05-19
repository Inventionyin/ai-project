"""add ai training tables

Revision ID: 0028_add_ai_training
Revises: 0026_add_ui_automation
Create Date: 2026-05-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0028_add_ai_training"
down_revision = "0026_add_ui_automation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_training_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("training_type", sa.String(32), nullable=False, server_default="FINE_TUNE"),
        sa.Column("base_model", sa.String(128), nullable=False, server_default="deepseek-chat"),
        sa.Column("dataset_config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("hyperparams", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("progress", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("metrics_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("model_ref", sa.String(512), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ai_training_jobs_tenant_id", "ai_training_jobs", ["tenant_id"])
    op.create_index("ix_ai_training_jobs_project_id", "ai_training_jobs", ["project_id"])

    op.create_table(
        "ai_training_datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False, server_default="TESTCASES"),
        sa.Column("record_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("sample_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("config_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ai_training_datasets_tenant_id", "ai_training_datasets", ["tenant_id"])
    op.create_index("ix_ai_training_datasets_project_id", "ai_training_datasets", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_training_datasets_project_id", table_name="ai_training_datasets")
    op.drop_index("ix_ai_training_datasets_tenant_id", table_name="ai_training_datasets")
    op.drop_table("ai_training_datasets")
    op.drop_index("ix_ai_training_jobs_project_id", table_name="ai_training_jobs")
    op.drop_index("ix_ai_training_jobs_tenant_id", table_name="ai_training_jobs")
    op.drop_table("ai_training_jobs")
