"""add ui_test_scripts and ui_test_runs tables

Revision ID: 0026_add_ui_automation
Revises: 0025_add_organizations
Create Date: 2026-05-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0026_add_ui_automation"
down_revision = "0025_add_organizations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ui_test_scripts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("script_type", sa.String(32), nullable=False, server_default="PLAYWRIGHT"),
        sa.Column("script_content", sa.Text, nullable=False, server_default=""),
        sa.Column("recording_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("browser", sa.String(32), nullable=False, server_default="chromium"),
        sa.Column("viewport_width", sa.Integer, nullable=False, server_default="1280"),
        sa.Column("viewport_height", sa.Integer, nullable=False, server_default="720"),
        sa.Column("base_url", sa.String(512), nullable=False, server_default=""),
        sa.Column("tags", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ui_test_scripts_tenant_id", "ui_test_scripts", ["tenant_id"])
    op.create_index("ix_ui_test_scripts_project_id", "ui_test_scripts", ["project_id"])

    op.create_table(
        "ui_test_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("script_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ui_test_scripts.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="QUEUED"),
        sa.Column("started_at", sa.String(32), nullable=True),
        sa.Column("finished_at", sa.String(32), nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("steps_total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("steps_passed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("steps_failed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("screenshot_paths", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("trace_path", sa.String(512), nullable=True),
        sa.Column("report_path", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ui_test_runs_tenant_id", "ui_test_runs", ["tenant_id"])
    op.create_index("ix_ui_test_runs_script_id", "ui_test_runs", ["script_id"])


def downgrade() -> None:
    op.drop_index("ix_ui_test_runs_script_id", table_name="ui_test_runs")
    op.drop_index("ix_ui_test_runs_tenant_id", table_name="ui_test_runs")
    op.drop_table("ui_test_runs")

    op.drop_index("ix_ui_test_scripts_project_id", table_name="ui_test_scripts")
    op.drop_index("ix_ui_test_scripts_tenant_id", table_name="ui_test_scripts")
    op.drop_table("ui_test_scripts")
