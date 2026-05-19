"""add performance tests and test runs tables

Revision ID: 0027_add_performance_tests
Revises: 0026_add_ui_automation
Create Date: 2026-05-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0027_add_performance_tests"
down_revision = "0026_add_ui_automation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "performance_tests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("test_type", sa.String(32), nullable=False, server_default="LOAD"),
        sa.Column("target_url", sa.String(512), nullable=False, server_default=""),
        sa.Column("config_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("script_content", sa.Text, nullable=False, server_default=""),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("tags", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_performance_tests_tenant_id", "performance_tests", ["tenant_id"])
    op.create_index("ix_performance_tests_project_id", "performance_tests", ["project_id"])

    op.create_table(
        "performance_test_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("test_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("performance_tests.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="QUEUED"),
        sa.Column("started_at", sa.String(32), nullable=True),
        sa.Column("finished_at", sa.String(32), nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("metrics_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("thresholds_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("report_path", sa.String(512), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_performance_test_runs_tenant_id", "performance_test_runs", ["tenant_id"])
    op.create_index("ix_performance_test_runs_test_id", "performance_test_runs", ["test_id"])


def downgrade() -> None:
    op.drop_index("ix_performance_test_runs_test_id", table_name="performance_test_runs")
    op.drop_index("ix_performance_test_runs_tenant_id", table_name="performance_test_runs")
    op.drop_table("performance_test_runs")
    op.drop_index("ix_performance_tests_project_id", table_name="performance_tests")
    op.drop_index("ix_performance_tests_tenant_id", table_name="performance_tests")
    op.drop_table("performance_tests")
