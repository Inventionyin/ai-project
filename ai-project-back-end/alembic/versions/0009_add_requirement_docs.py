from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0009_add_requirement_docs"
down_revision = "0008_add_test_case_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "requirement_docs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("tags_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_requirement_docs_created_by"), "requirement_docs", ["created_by"], unique=False)
    op.create_index(op.f("ix_requirement_docs_owner_id"), "requirement_docs", ["owner_id"], unique=False)
    op.create_index(op.f("ix_requirement_docs_project_id"), "requirement_docs", ["project_id"], unique=False)
    op.create_index(op.f("ix_requirement_docs_tenant_id"), "requirement_docs", ["tenant_id"], unique=False)

    op.create_table(
        "requirement_doc_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doc_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(length=512), nullable=False),
        sa.Column("file_type", sa.String(length=32), nullable=False),
        sa.Column("storage_url", sa.String(length=2048), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("parsed_text_url", sa.String(length=2048), nullable=True),
        sa.Column("parsed_text_preview", sa.Text(), nullable=True),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("effective_scope", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["doc_id"], ["requirement_docs.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("doc_id", "version", name="uq_requirement_doc_versions_doc_version"),
    )
    op.create_index(op.f("ix_requirement_doc_versions_created_by"), "requirement_doc_versions", ["created_by"], unique=False)
    op.create_index(op.f("ix_requirement_doc_versions_doc_id"), "requirement_doc_versions", ["doc_id"], unique=False)
    op.create_index(op.f("ix_requirement_doc_versions_project_id"), "requirement_doc_versions", ["project_id"], unique=False)
    op.create_index(op.f("ix_requirement_doc_versions_tenant_id"), "requirement_doc_versions", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_requirement_doc_versions_tenant_id"), table_name="requirement_doc_versions")
    op.drop_index(op.f("ix_requirement_doc_versions_project_id"), table_name="requirement_doc_versions")
    op.drop_index(op.f("ix_requirement_doc_versions_doc_id"), table_name="requirement_doc_versions")
    op.drop_index(op.f("ix_requirement_doc_versions_created_by"), table_name="requirement_doc_versions")
    op.drop_table("requirement_doc_versions")
    op.drop_index(op.f("ix_requirement_docs_tenant_id"), table_name="requirement_docs")
    op.drop_index(op.f("ix_requirement_docs_project_id"), table_name="requirement_docs")
    op.drop_index(op.f("ix_requirement_docs_owner_id"), table_name="requirement_docs")
    op.drop_index(op.f("ix_requirement_docs_created_by"), table_name="requirement_docs")
    op.drop_table("requirement_docs")
