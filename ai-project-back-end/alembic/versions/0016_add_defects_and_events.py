"""add defects and defect events

Revision ID: 0016_add_defects_and_events
Revises: 0015_expand_testcase_bindings_for_api_links
Create Date: 2026-05-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0016_add_defects_and_events"
down_revision = "0015_expand_testcase_bindings_for_api_links"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "defects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("assignee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reporter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_defects_assignee_id"), "defects", ["assignee_id"], unique=False)
    op.create_index(op.f("ix_defects_created_by"), "defects", ["created_by"], unique=False)
    op.create_index(op.f("ix_defects_project_id"), "defects", ["project_id"], unique=False)
    op.create_index(op.f("ix_defects_reporter_id"), "defects", ["reporter_id"], unique=False)
    op.create_index(op.f("ix_defects_tenant_id"), "defects", ["tenant_id"], unique=False)

    op.create_table(
        "defect_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("defect_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=True),
        sa.Column("from_assignee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("to_assignee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("detail_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["defect_id"], ["defects.id"]),
        sa.ForeignKeyConstraint(["from_assignee_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["to_assignee_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_defect_events_created_by"), "defect_events", ["created_by"], unique=False)
    op.create_index(op.f("ix_defect_events_defect_id"), "defect_events", ["defect_id"], unique=False)
    op.create_index(op.f("ix_defect_events_from_assignee_id"), "defect_events", ["from_assignee_id"], unique=False)
    op.create_index(op.f("ix_defect_events_project_id"), "defect_events", ["project_id"], unique=False)
    op.create_index(op.f("ix_defect_events_tenant_id"), "defect_events", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_defect_events_to_assignee_id"), "defect_events", ["to_assignee_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_defect_events_to_assignee_id"), table_name="defect_events")
    op.drop_index(op.f("ix_defect_events_tenant_id"), table_name="defect_events")
    op.drop_index(op.f("ix_defect_events_project_id"), table_name="defect_events")
    op.drop_index(op.f("ix_defect_events_from_assignee_id"), table_name="defect_events")
    op.drop_index(op.f("ix_defect_events_defect_id"), table_name="defect_events")
    op.drop_index(op.f("ix_defect_events_created_by"), table_name="defect_events")
    op.drop_table("defect_events")

    op.drop_index(op.f("ix_defects_tenant_id"), table_name="defects")
    op.drop_index(op.f("ix_defects_reporter_id"), table_name="defects")
    op.drop_index(op.f("ix_defects_project_id"), table_name="defects")
    op.drop_index(op.f("ix_defects_created_by"), table_name="defects")
    op.drop_index(op.f("ix_defects_assignee_id"), table_name="defects")
    op.drop_table("defects")
