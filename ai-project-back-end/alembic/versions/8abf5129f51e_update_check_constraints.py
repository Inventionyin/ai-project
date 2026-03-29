"""update check constraints

Revision ID: 8abf5129f51e
Revises: 93a5ad2e0df7
Create Date: 2026-03-29 12:28:35.477353

"""

from alembic import op
import sqlalchemy as sa



revision = '8abf5129f51e'
down_revision = '93a5ad2e0df7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE ai_import_jobs DROP CONSTRAINT IF EXISTS ai_import_jobs_source_type_check")
    op.execute("ALTER TABLE ai_import_jobs DROP CONSTRAINT IF EXISTS ai_import_jobs_status_check")
    
    op.create_check_constraint(
        "ai_import_jobs_source_type_check",
        "ai_import_jobs",
        "source_type IN ('PRD_DOC', 'FIGMA_LINK', 'HTML_DOC', 'API_COLLECTION_DOC')"
    )
    op.create_check_constraint(
        "ai_import_jobs_status_check",
        "ai_import_jobs",
        "status IN ('PENDING', 'UPLOADED', 'RUNNING', 'PARSING', 'PARSED_PREVIEW', 'SUCCEEDED', 'FAILED', 'COMMITTED')"
    )


def downgrade() -> None:
    pass

