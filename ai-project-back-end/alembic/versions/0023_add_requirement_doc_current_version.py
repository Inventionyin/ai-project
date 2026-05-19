"""add requirement doc current version

Revision ID: 0023_add_requirement_doc_current_version
Revises: 0022_add_project_ci_token_policy
Create Date: 2026-05-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0023_add_requirement_doc_current_version"
down_revision = "0022_add_project_ci_token_policy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("requirement_docs", sa.Column("current_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("requirement_doc_versions.id"), nullable=True))
    op.create_index("ix_requirement_docs_current_version_id", "requirement_docs", ["current_version_id"])


def downgrade() -> None:
    op.drop_index("ix_requirement_docs_current_version_id", table_name="requirement_docs")
    op.drop_column("requirement_docs", "current_version_id")
