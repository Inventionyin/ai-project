"""add knowledge core tables

Revision ID: 0017_add_knowledge_core_tables
Revises: 0016_add_defects_and_events
Create Date: 2026-05-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0017_add_knowledge_core_tables"
down_revision = "0016_add_defects_and_events"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "retrospective_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("problem_summary", sa.Text(), nullable=True),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("decision", sa.Text(), nullable=True),
        sa.Column("action_items", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_retrospective_records_created_by"), "retrospective_records", ["created_by"], unique=False)
    op.create_index(op.f("ix_retrospective_records_project_id"), "retrospective_records", ["project_id"], unique=False)
    op.create_index(op.f("ix_retrospective_records_tenant_id"), "retrospective_records", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_retrospective_records_updated_by"), "retrospective_records", ["updated_by"], unique=False)

    op.create_table(
        "knowledge_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("content_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_knowledge_templates_created_by"), "knowledge_templates", ["created_by"], unique=False)
    op.create_index(op.f("ix_knowledge_templates_project_id"), "knowledge_templates", ["project_id"], unique=False)
    op.create_index(op.f("ix_knowledge_templates_tenant_id"), "knowledge_templates", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_knowledge_templates_updated_by"), "knowledge_templates", ["updated_by"], unique=False)

    op.create_table(
        "knowledge_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("trigger_type", sa.String(length=64), nullable=False),
        sa.Column("condition_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("action_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_knowledge_rules_created_by"), "knowledge_rules", ["created_by"], unique=False)
    op.create_index(op.f("ix_knowledge_rules_project_id"), "knowledge_rules", ["project_id"], unique=False)
    op.create_index(op.f("ix_knowledge_rules_tenant_id"), "knowledge_rules", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_knowledge_rules_updated_by"), "knowledge_rules", ["updated_by"], unique=False)

    op.create_table(
        "knowledge_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("retrospective_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recommendation_type", sa.String(length=64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["retrospective_id"], ["retrospective_records.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_knowledge_recommendations_created_by"),
        "knowledge_recommendations",
        ["created_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_recommendations_project_id"),
        "knowledge_recommendations",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_recommendations_retrospective_id"),
        "knowledge_recommendations",
        ["retrospective_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_recommendations_tenant_id"),
        "knowledge_recommendations",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_recommendations_updated_by"),
        "knowledge_recommendations",
        ["updated_by"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_knowledge_recommendations_updated_by"), table_name="knowledge_recommendations")
    op.drop_index(op.f("ix_knowledge_recommendations_tenant_id"), table_name="knowledge_recommendations")
    op.drop_index(op.f("ix_knowledge_recommendations_retrospective_id"), table_name="knowledge_recommendations")
    op.drop_index(op.f("ix_knowledge_recommendations_project_id"), table_name="knowledge_recommendations")
    op.drop_index(op.f("ix_knowledge_recommendations_created_by"), table_name="knowledge_recommendations")
    op.drop_table("knowledge_recommendations")

    op.drop_index(op.f("ix_knowledge_rules_updated_by"), table_name="knowledge_rules")
    op.drop_index(op.f("ix_knowledge_rules_tenant_id"), table_name="knowledge_rules")
    op.drop_index(op.f("ix_knowledge_rules_project_id"), table_name="knowledge_rules")
    op.drop_index(op.f("ix_knowledge_rules_created_by"), table_name="knowledge_rules")
    op.drop_table("knowledge_rules")

    op.drop_index(op.f("ix_knowledge_templates_updated_by"), table_name="knowledge_templates")
    op.drop_index(op.f("ix_knowledge_templates_tenant_id"), table_name="knowledge_templates")
    op.drop_index(op.f("ix_knowledge_templates_project_id"), table_name="knowledge_templates")
    op.drop_index(op.f("ix_knowledge_templates_created_by"), table_name="knowledge_templates")
    op.drop_table("knowledge_templates")

    op.drop_index(op.f("ix_retrospective_records_updated_by"), table_name="retrospective_records")
    op.drop_index(op.f("ix_retrospective_records_tenant_id"), table_name="retrospective_records")
    op.drop_index(op.f("ix_retrospective_records_project_id"), table_name="retrospective_records")
    op.drop_index(op.f("ix_retrospective_records_created_by"), table_name="retrospective_records")
    op.drop_table("retrospective_records")
