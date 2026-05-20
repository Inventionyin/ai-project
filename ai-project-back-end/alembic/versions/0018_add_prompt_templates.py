"""add prompt templates

Revision ID: 0018_add_prompt_templates
Revises: 0017_add_knowledge_core_tables
Create Date: 2026-05-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0018_add_prompt_templates"
down_revision = "0017_add_knowledge_core_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prompt_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scene", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("variables_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "project_id", "scene", "name", "version", name="uq_prompt_templates_version"),
    )
    op.create_index(op.f("ix_prompt_templates_created_by"), "prompt_templates", ["created_by"], unique=False)
    op.create_index(op.f("ix_prompt_templates_project_id"), "prompt_templates", ["project_id"], unique=False)
    op.create_index(op.f("ix_prompt_templates_tenant_id"), "prompt_templates", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_prompt_templates_tenant_id"), table_name="prompt_templates")
    op.drop_index(op.f("ix_prompt_templates_project_id"), table_name="prompt_templates")
    op.drop_index(op.f("ix_prompt_templates_created_by"), table_name="prompt_templates")
    op.drop_table("prompt_templates")
