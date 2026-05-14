"""add requirement test points and generated case drafts

Revision ID: 0011_add_requirement_test_points_and_case_drafts
Revises: 0010b_expand_alembic_version_num
Create Date: 2026-05-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0011_add_requirement_test_points_and_case_drafts"
down_revision = "0010b_expand_alembic_version_num"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "requirement_test_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scenario_type", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("source_path", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("ai_meta_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["requirement_analyses.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_requirement_test_points_analysis_id"), "requirement_test_points", ["analysis_id"], unique=False)
    op.create_index(op.f("ix_requirement_test_points_created_by"), "requirement_test_points", ["created_by"], unique=False)
    op.create_index(op.f("ix_requirement_test_points_project_id"), "requirement_test_points", ["project_id"], unique=False)
    op.create_index(op.f("ix_requirement_test_points_tenant_id"), "requirement_test_points", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_requirement_test_points_updated_by"), "requirement_test_points", ["updated_by"], unique=False)

    op.create_table(
        "generated_case_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("test_point_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("preconditions", sa.Text(), nullable=True),
        sa.Column("steps_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expected_results_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("test_data_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("ai_meta_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["requirement_analyses.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["test_point_id"], ["requirement_test_points.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_generated_case_drafts_analysis_id"), "generated_case_drafts", ["analysis_id"], unique=False)
    op.create_index(op.f("ix_generated_case_drafts_created_by"), "generated_case_drafts", ["created_by"], unique=False)
    op.create_index(op.f("ix_generated_case_drafts_project_id"), "generated_case_drafts", ["project_id"], unique=False)
    op.create_index(op.f("ix_generated_case_drafts_reviewed_by"), "generated_case_drafts", ["reviewed_by"], unique=False)
    op.create_index(op.f("ix_generated_case_drafts_tenant_id"), "generated_case_drafts", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_generated_case_drafts_test_point_id"), "generated_case_drafts", ["test_point_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_generated_case_drafts_test_point_id"), table_name="generated_case_drafts")
    op.drop_index(op.f("ix_generated_case_drafts_tenant_id"), table_name="generated_case_drafts")
    op.drop_index(op.f("ix_generated_case_drafts_reviewed_by"), table_name="generated_case_drafts")
    op.drop_index(op.f("ix_generated_case_drafts_project_id"), table_name="generated_case_drafts")
    op.drop_index(op.f("ix_generated_case_drafts_created_by"), table_name="generated_case_drafts")
    op.drop_index(op.f("ix_generated_case_drafts_analysis_id"), table_name="generated_case_drafts")
    op.drop_table("generated_case_drafts")

    op.drop_index(op.f("ix_requirement_test_points_updated_by"), table_name="requirement_test_points")
    op.drop_index(op.f("ix_requirement_test_points_tenant_id"), table_name="requirement_test_points")
    op.drop_index(op.f("ix_requirement_test_points_project_id"), table_name="requirement_test_points")
    op.drop_index(op.f("ix_requirement_test_points_created_by"), table_name="requirement_test_points")
    op.drop_index(op.f("ix_requirement_test_points_analysis_id"), table_name="requirement_test_points")
    op.drop_table("requirement_test_points")
