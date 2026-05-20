"""add ci token lifecycle fields

Revision ID: 0023_add_ci_token_lifecycle_fields
Revises: 0022_add_project_ci_token_policy
Create Date: 2026-05-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0023_add_ci_token_lifecycle_fields"
down_revision = "0022_add_project_ci_token_policy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("ci_token_expires_at", sa.DateTime(), nullable=True))
    op.add_column("projects", sa.Column("ci_token_revoked_at", sa.DateTime(), nullable=True))
    op.add_column("projects", sa.Column("ci_token_revoked_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("projects", sa.Column("ci_token_revoked_reason", sa.String(length=255), nullable=True))
    op.add_column("projects", sa.Column("ci_token_leak_reported_at", sa.DateTime(), nullable=True))
    op.add_column("projects", sa.Column("ci_token_leak_reported_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("projects", sa.Column("ci_token_leak_report_reason", sa.String(length=255), nullable=True))
    op.create_index("ix_projects_ci_token_revoked_by", "projects", ["ci_token_revoked_by"], unique=False)
    op.create_index("ix_projects_ci_token_leak_reported_by", "projects", ["ci_token_leak_reported_by"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_projects_ci_token_leak_reported_by", table_name="projects")
    op.drop_index("ix_projects_ci_token_revoked_by", table_name="projects")
    op.drop_column("projects", "ci_token_leak_report_reason")
    op.drop_column("projects", "ci_token_leak_reported_by")
    op.drop_column("projects", "ci_token_leak_reported_at")
    op.drop_column("projects", "ci_token_revoked_reason")
    op.drop_column("projects", "ci_token_revoked_by")
    op.drop_column("projects", "ci_token_revoked_at")
    op.drop_column("projects", "ci_token_expires_at")
