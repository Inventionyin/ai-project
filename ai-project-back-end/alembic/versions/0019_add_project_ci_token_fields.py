"""add project ci token fields

Revision ID: 0019_add_project_ci_token_fields
Revises: 0018_add_prompt_templates
Create Date: 2026-05-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0019_add_project_ci_token_fields"
down_revision = "0018_add_prompt_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("ci_token_hash", sa.String(length=128), nullable=True))
    op.add_column("projects", sa.Column("ci_token_hint", sa.String(length=32), nullable=True))
    op.add_column("projects", sa.Column("ci_token_rotated_at", sa.DateTime(), nullable=True))
    op.add_column("projects", sa.Column("ci_token_last_used_at", sa.DateTime(), nullable=True))
    op.add_column("projects", sa.Column("ci_token_rotated_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_projects_ci_token_rotated_by"), "projects", ["ci_token_rotated_by"], unique=False)
    op.create_foreign_key(
        "fk_projects_ci_token_rotated_by_users",
        "projects",
        "users",
        ["ci_token_rotated_by"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_projects_ci_token_rotated_by_users", "projects", type_="foreignkey")
    op.drop_index(op.f("ix_projects_ci_token_rotated_by"), table_name="projects")
    op.drop_column("projects", "ci_token_rotated_by")
    op.drop_column("projects", "ci_token_last_used_at")
    op.drop_column("projects", "ci_token_rotated_at")
    op.drop_column("projects", "ci_token_hint")
    op.drop_column("projects", "ci_token_hash")
