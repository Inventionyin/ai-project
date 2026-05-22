"""add doc parse jobs, devops pipelines, executors, plugins

Revision ID: 0021_add_doc_parse_devops_executors_plugins
Revises: 0020_add_notification_outbox
Create Date: 2026-05-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0021_add_doc_parse_devops_executors_plugins"
down_revision = "0020_add_notification_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A: Doc parse jobs
    op.create_table(
        "doc_parse_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doc_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doc_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["doc_id"], ["requirement_docs.id"]),
        sa.ForeignKeyConstraint(["doc_version_id"], ["requirement_doc_versions.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_doc_parse_jobs_tenant_id"), "doc_parse_jobs", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_doc_parse_jobs_project_id"), "doc_parse_jobs", ["project_id"], unique=False)
    op.create_index(op.f("ix_doc_parse_jobs_status"), "doc_parse_jobs", ["status"], unique=False)

    # B: DevOps pipelines
    op.create_table(
        "devops_pipelines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("repo_full_name", sa.String(length=255), nullable=True),
        sa.Column("workflow_file", sa.String(length=255), nullable=True),
        sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("webhook_secret", sa.String(length=255), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_devops_pipelines_tenant_id"), "devops_pipelines", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_devops_pipelines_project_id"), "devops_pipelines", ["project_id"], unique=False)

    op.create_table(
        "devops_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_run_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("trigger_type", sa.String(length=50), nullable=False),
        sa.Column("commit_sha", sa.String(length=64), nullable=True),
        sa.Column("branch", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("log_url", sa.Text(), nullable=True),
        sa.Column("meta_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["pipeline_id"], ["devops_pipelines.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_devops_runs_tenant_id"), "devops_runs", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_devops_runs_project_id"), "devops_runs", ["project_id"], unique=False)
    op.create_index(op.f("ix_devops_runs_pipeline_id"), "devops_runs", ["pipeline_id"], unique=False)
    op.create_index(op.f("ix_devops_runs_status"), "devops_runs", ["status"], unique=False)

    # D: Executors
    op.create_table(
        "executors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("executor_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_executors_tenant_id"), "executors", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_executors_project_id"), "executors", ["project_id"], unique=False)

    # E: Plugins
    op.create_table(
        "plugins",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("plugin_type", sa.String(length=50), nullable=False),
        sa.Column("config_schema_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("entry_point", sa.String(length=500), nullable=True),
        sa.Column("min_platform_version", sa.String(length=50), nullable=True),
        sa.Column("icon_url", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("download_count", sa.Integer(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_plugin_tenant_slug"),
    )
    op.create_index(op.f("ix_plugins_tenant_id"), "plugins", ["tenant_id"], unique=False)

    op.create_table(
        "plugin_installations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plugin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("installed_version", sa.String(length=50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("installed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["plugin_id"], ["plugins.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "plugin_id", name="uq_plugin_install_project"),
    )
    op.create_index(op.f("ix_plugin_installations_tenant_id"), "plugin_installations", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_plugin_installations_project_id"), "plugin_installations", ["project_id"], unique=False)
    op.create_index(op.f("ix_plugin_installations_plugin_id"), "plugin_installations", ["plugin_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_plugin_installations_plugin_id"), table_name="plugin_installations")
    op.drop_index(op.f("ix_plugin_installations_project_id"), table_name="plugin_installations")
    op.drop_index(op.f("ix_plugin_installations_tenant_id"), table_name="plugin_installations")
    op.drop_table("plugin_installations")
    op.drop_index(op.f("ix_plugins_tenant_id"), table_name="plugins")
    op.drop_table("plugins")
    op.drop_index(op.f("ix_executors_project_id"), table_name="executors")
    op.drop_index(op.f("ix_executors_tenant_id"), table_name="executors")
    op.drop_table("executors")
    op.drop_index(op.f("ix_devops_runs_status"), table_name="devops_runs")
    op.drop_index(op.f("ix_devops_runs_pipeline_id"), table_name="devops_runs")
    op.drop_index(op.f("ix_devops_runs_project_id"), table_name="devops_runs")
    op.drop_index(op.f("ix_devops_runs_tenant_id"), table_name="devops_runs")
    op.drop_table("devops_runs")
    op.drop_index(op.f("ix_devops_pipelines_project_id"), table_name="devops_pipelines")
    op.drop_index(op.f("ix_devops_pipelines_tenant_id"), table_name="devops_pipelines")
    op.drop_table("devops_pipelines")
    op.drop_index(op.f("ix_doc_parse_jobs_status"), table_name="doc_parse_jobs")
    op.drop_index(op.f("ix_doc_parse_jobs_project_id"), table_name="doc_parse_jobs")
    op.drop_index(op.f("ix_doc_parse_jobs_tenant_id"), table_name="doc_parse_jobs")
    op.drop_table("doc_parse_jobs")
