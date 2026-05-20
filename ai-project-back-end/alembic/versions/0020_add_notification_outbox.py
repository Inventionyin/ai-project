"""add notification outbox

Revision ID: 0020_add_notification_outbox
Revises: 0019_add_project_ci_token_fields
Create Date: 2026-05-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0020_add_notification_outbox"
down_revision = "0019_add_project_ci_token_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notification_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("target", sa.String(length=2048), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rule_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_status_code", sa.Integer(), nullable=True),
        sa.Column("last_duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["notification_id"], ["notifications.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notification_outbox_notification_id"), "notification_outbox", ["notification_id"], unique=False)
    op.create_index(op.f("ix_notification_outbox_project_id"), "notification_outbox", ["project_id"], unique=False)
    op.create_index(op.f("ix_notification_outbox_run_id"), "notification_outbox", ["run_id"], unique=False)
    op.create_index(op.f("ix_notification_outbox_tenant_id"), "notification_outbox", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notification_outbox_tenant_id"), table_name="notification_outbox")
    op.drop_index(op.f("ix_notification_outbox_run_id"), table_name="notification_outbox")
    op.drop_index(op.f("ix_notification_outbox_project_id"), table_name="notification_outbox")
    op.drop_index(op.f("ix_notification_outbox_notification_id"), table_name="notification_outbox")
    op.drop_table("notification_outbox")
