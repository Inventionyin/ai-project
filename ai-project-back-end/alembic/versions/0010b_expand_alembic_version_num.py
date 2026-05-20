"""expand alembic version num length

Revision ID: 0010b_expand_alembic_version_num
Revises: 0010_add_requirement_analyses
Create Date: 2026-05-12 14:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0010b_expand_alembic_version_num"
down_revision = "0010_add_requirement_analyses"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "alembic_version",
        "version_num",
        existing_type=sa.String(length=32),
        type_=sa.String(length=128),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "alembic_version",
        "version_num",
        existing_type=sa.String(length=128),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
