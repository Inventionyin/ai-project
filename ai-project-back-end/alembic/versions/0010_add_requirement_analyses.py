from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0010_add_requirement_analyses"
down_revision = "0009_add_requirement_docs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "requirement_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doc_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doc_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("analysis_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("coverage_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("ai_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["doc_id"], ["requirement_docs.id"]),
        sa.ForeignKeyConstraint(["doc_version_id"], ["requirement_doc_versions.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_requirement_analyses_ai_task_id"), "requirement_analyses", ["ai_task_id"], unique=False)
    op.create_index(op.f("ix_requirement_analyses_created_by"), "requirement_analyses", ["created_by"], unique=False)
    op.create_index(op.f("ix_requirement_analyses_doc_id"), "requirement_analyses", ["doc_id"], unique=False)
    op.create_index(op.f("ix_requirement_analyses_doc_version_id"), "requirement_analyses", ["doc_version_id"], unique=False)
    op.create_index(op.f("ix_requirement_analyses_project_id"), "requirement_analyses", ["project_id"], unique=False)
    op.create_index(op.f("ix_requirement_analyses_tenant_id"), "requirement_analyses", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_requirement_analyses_updated_by"), "requirement_analyses", ["updated_by"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_requirement_analyses_updated_by"), table_name="requirement_analyses")
    op.drop_index(op.f("ix_requirement_analyses_tenant_id"), table_name="requirement_analyses")
    op.drop_index(op.f("ix_requirement_analyses_project_id"), table_name="requirement_analyses")
    op.drop_index(op.f("ix_requirement_analyses_doc_version_id"), table_name="requirement_analyses")
    op.drop_index(op.f("ix_requirement_analyses_doc_id"), table_name="requirement_analyses")
    op.drop_index(op.f("ix_requirement_analyses_created_by"), table_name="requirement_analyses")
    op.drop_index(op.f("ix_requirement_analyses_ai_task_id"), table_name="requirement_analyses")
    op.drop_table("requirement_analyses")
