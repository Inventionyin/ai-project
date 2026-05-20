"""add project ci tokens

Revision ID: 0024_add_project_ci_tokens
Revises: 0023_add_ci_token_lifecycle_fields
Create Date: 2026-05-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0024_add_project_ci_tokens"
down_revision = "0023_add_ci_token_lifecycle_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_ci_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("token_hint", sa.String(length=32), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rotated_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("rotated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("revoked_reason", sa.String(length=255), nullable=True),
        sa.Column("leak_reported_at", sa.DateTime(), nullable=True),
        sa.Column("leak_reported_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("leak_report_reason", sa.String(length=255), nullable=True),
        sa.Column("allowed_runner_types", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("allowed_testcase_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("max_testcase_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["revoked_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["rotated_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "name", name="uq_project_ci_tokens_project_name"),
        sa.UniqueConstraint("token_hash", name="uq_project_ci_tokens_token_hash"),
    )
    op.create_index("ix_project_ci_tokens_project_id", "project_ci_tokens", ["project_id"], unique=False)
    op.create_index("ix_project_ci_tokens_revoked_by", "project_ci_tokens", ["revoked_by"], unique=False)
    op.create_index("ix_project_ci_tokens_rotated_by", "project_ci_tokens", ["rotated_by"], unique=False)
    op.create_index("ix_project_ci_tokens_tenant_id", "project_ci_tokens", ["tenant_id"], unique=False)
    op.create_index("ix_project_ci_tokens_token_hash", "project_ci_tokens", ["token_hash"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_project_ci_tokens_token_hash", table_name="project_ci_tokens")
    op.drop_index("ix_project_ci_tokens_tenant_id", table_name="project_ci_tokens")
    op.drop_index("ix_project_ci_tokens_rotated_by", table_name="project_ci_tokens")
    op.drop_index("ix_project_ci_tokens_revoked_by", table_name="project_ci_tokens")
    op.drop_index("ix_project_ci_tokens_project_id", table_name="project_ci_tokens")
    op.drop_table("project_ci_tokens")
