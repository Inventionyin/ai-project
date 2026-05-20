"""add project ci token policy

Revision ID: 0022_add_project_ci_token_policy
Revises: 0021_add_doc_parse_devops_executors_plugins
Create Date: 2026-05-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0022_add_project_ci_token_policy"
down_revision = "0021_add_doc_parse_devops_executors_plugins"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("ci_token_allowed_runner_types", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("projects", sa.Column("ci_token_allowed_testcase_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("projects", sa.Column("ci_token_max_testcase_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "ci_token_max_testcase_count")
    op.drop_column("projects", "ci_token_allowed_testcase_ids")
    op.drop_column("projects", "ci_token_allowed_runner_types")
