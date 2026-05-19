"""add defect provider configs

Revision ID: 0024_add_defect_provider_configs
Revises: 0023_add_requirement_doc_current_version
Create Date: 2026-05-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0024_add_defect_provider_configs"
down_revision = "0023_add_requirement_doc_current_version"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "defect_provider_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("base_url", sa.String(512), nullable=False),
        sa.Column("auth_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("config_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_sync_at", sa.DateTime, nullable=True),
        sa.Column("sync_status", sa.String(32), nullable=False, server_default="IDLE"),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_defect_provider_configs_tenant_id", "defect_provider_configs", ["tenant_id"])
    op.create_index("ix_defect_provider_configs_project_id", "defect_provider_configs", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_defect_provider_configs_project_id", table_name="defect_provider_configs")
    op.drop_index("ix_defect_provider_configs_tenant_id", table_name="defect_provider_configs")
    op.drop_table("defect_provider_configs")
