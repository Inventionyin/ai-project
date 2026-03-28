from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_init_models"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_status = postgresql.ENUM("ACTIVE", "DISABLED", name="user_status", create_type=False)
    project_role = postgresql.ENUM("ADMIN", "OWNER", "EDITOR", "VIEWER", name="project_role", create_type=False)
    testcase_type = postgresql.ENUM("API", "UI", "PERF", "MIX", name="testcase_type", create_type=False)
    priority = postgresql.ENUM("P0", "P1", "P2", "P3", name="priority", create_type=False)
    testcase_status = postgresql.ENUM(
        "DRAFT",
        "REVIEWED",
        "DEPRECATED",
        name="testcase_status",
        create_type=False,
    )
    trigger_type = postgresql.ENUM("MANUAL", "CRON", "CI", "WEBHOOK", name="trigger_type", create_type=False)
    run_status = postgresql.ENUM(
        "QUEUED",
        "RUNNING",
        "PASSED",
        "FAILED",
        "CANCELED",
        name="run_status",
        create_type=False,
    )
    job_status = postgresql.ENUM(
        "QUEUED",
        "RUNNING",
        "DONE",
        "FAILED",
        "CANCELED",
        name="job_status",
        create_type=False,
    )
    case_run_status = postgresql.ENUM(
        "QUEUED",
        "RUNNING",
        "PASSED",
        "FAILED",
        "SKIPPED",
        name="case_run_status",
        create_type=False,
    )
    artifact_type = postgresql.ENUM(
        "API_EXCHANGE",
        "SCREENSHOT",
        "VIDEO",
        "TRACE",
        "LOG_BUNDLE",
        "PERF_REPORT",
        name="artifact_type",
        create_type=False,
    )
    worker_status = postgresql.ENUM("ONLINE", "OFFLINE", name="worker_status", create_type=False)

    bind = op.get_bind()
    for enum_type in [
        user_status,
        project_role,
        testcase_type,
        priority,
        testcase_status,
        trigger_type,
        run_status,
        job_status,
        case_run_status,
        artifact_type,
        worker_status,
    ]:
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", user_status, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.UniqueConstraint("tenant_id", "name", name="uq_projects_tenant_name"),
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])
    op.create_index("ix_projects_tenant_id", "projects", ["tenant_id"])

    op.create_table(
        "project_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", project_role, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
    )
    op.create_index("ix_project_members_project_id", "project_members", ["project_id"])
    op.create_index("ix_project_members_tenant_id", "project_members", ["tenant_id"])
    op.create_index("ix_project_members_user_id", "project_members", ["user_id"])

    op.create_table(
        "environments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("base_url", sa.String(length=2048), nullable=False),
        sa.Column("variables_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("secrets_ref", sa.String(length=512), nullable=True),
        sa.Column("health_config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
    )
    op.create_index("ix_environments_project_id", "environments", ["project_id"])
    op.create_index("ix_environments_tenant_id", "environments", ["tenant_id"])

    op.create_table(
        "testcases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("type", testcase_type, nullable=False),
        sa.Column("priority", priority, nullable=False),
        sa.Column("status", testcase_status, nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("tags_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
    )
    op.create_index("ix_testcases_created_by", "testcases", ["created_by"])
    op.create_index("ix_testcases_owner_id", "testcases", ["owner_id"])
    op.create_index("ix_testcases_project_id", "testcases", ["project_id"])
    op.create_index("ix_testcases_tenant_id", "testcases", ["tenant_id"])
    op.create_index(
        "ix_testcases_project_updated_at_desc",
        "testcases",
        ["project_id", sa.text("updated_at DESC")],
        postgresql_using="btree",
    )

    op.create_table(
        "testcase_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("testcase_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["testcase_id"], ["testcases.id"]),
    )
    op.create_index("ix_testcase_versions_created_by", "testcase_versions", ["created_by"])
    op.create_index("ix_testcase_versions_tenant_id", "testcase_versions", ["tenant_id"])
    op.create_index("ix_testcase_versions_testcase_id", "testcase_versions", ["testcase_id"])
    op.create_index(
        "ix_testcase_versions_testcase_version",
        "testcase_versions",
        ["testcase_id", "version"],
        unique=True,
    )

    op.create_table(
        "suites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
    )
    op.create_index("ix_suites_created_by", "suites", ["created_by"])
    op.create_index("ix_suites_project_id", "suites", ["project_id"])
    op.create_index("ix_suites_tenant_id", "suites", ["tenant_id"])

    op.create_table(
        "suite_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("suite_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("testcase_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_no", sa.Integer(), nullable=False),
        sa.Column("params_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["suite_id"], ["suites.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["testcase_id"], ["testcases.id"]),
    )
    op.create_index("ix_suite_items_suite_id", "suite_items", ["suite_id"])
    op.create_index("ix_suite_items_tenant_id", "suite_items", ["tenant_id"])
    op.create_index("ix_suite_items_testcase_id", "suite_items", ["testcase_id"])
    op.create_index("ix_suite_items_suite_order_no", "suite_items", ["suite_id", "order_no"], unique=True)

    op.create_table(
        "api_collections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("variables_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
    )
    op.create_index("ix_api_collections_project_id", "api_collections", ["project_id"])
    op.create_index("ix_api_collections_tenant_id", "api_collections", ["tenant_id"])

    op.create_table(
        "api_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("collection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("headers_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("body_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("asserts_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["collection_id"], ["api_collections.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
    )
    op.create_index("ix_api_requests_collection_id", "api_requests", ["collection_id"])
    op.create_index("ix_api_requests_tenant_id", "api_requests", ["tenant_id"])

    op.create_table(
        "test_data_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("content_blob_ref", sa.String(length=1024), nullable=True),
        sa.Column("schema_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
    )
    op.create_index("ix_test_data_sets_project_id", "test_data_sets", ["project_id"])
    op.create_index("ix_test_data_sets_tenant_id", "test_data_sets", ["tenant_id"])

    op.create_table(
        "workers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("capabilities_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("slots", sa.Integer(), nullable=False),
        sa.Column("status", worker_status, nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("version", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_workers_tenant_id", "workers", ["tenant_id"])
    op.create_index("ix_workers_last_seen_at", "workers", ["last_seen_at"])
    op.create_index(
        "ix_workers_tenant_last_seen_at_desc",
        "workers",
        ["tenant_id", sa.text("last_seen_at DESC")],
        postgresql_using="btree",
    )

    op.create_table(
        "runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("suite_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("env_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trigger_type", trigger_type, nullable=False),
        sa.Column("status", run_status, nullable=False),
        sa.Column("start_at", sa.DateTime(), nullable=True),
        sa.Column("end_at", sa.DateTime(), nullable=True),
        sa.Column("summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["env_id"], ["environments.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["suite_id"], ["suites.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
    )
    op.create_index("ix_runs_created_by", "runs", ["created_by"])
    op.create_index("ix_runs_env_id", "runs", ["env_id"])
    op.create_index("ix_runs_project_id", "runs", ["project_id"])
    op.create_index("ix_runs_start_at", "runs", ["start_at"])
    op.create_index("ix_runs_suite_id", "runs", ["suite_id"])
    op.create_index("ix_runs_tenant_id", "runs", ["tenant_id"])
    op.create_index(
        "ix_runs_project_start_at_desc",
        "runs",
        ["project_id", sa.text("start_at DESC")],
        postgresql_using="btree",
    )

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("worker_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", job_status, nullable=False),
        sa.Column("start_at", sa.DateTime(), nullable=True),
        sa.Column("end_at", sa.DateTime(), nullable=True),
        sa.Column("meta_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"]),
    )
    op.create_index("ix_jobs_run_id", "jobs", ["run_id"])
    op.create_index("ix_jobs_tenant_id", "jobs", ["tenant_id"])
    op.create_index("ix_jobs_worker_id", "jobs", ["worker_id"])

    op.create_table(
        "case_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("testcase_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", case_run_status, nullable=False),
        sa.Column("start_at", sa.DateTime(), nullable=True),
        sa.Column("end_at", sa.DateTime(), nullable=True),
        sa.Column("error_type", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metrics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["testcase_id"], ["testcases.id"]),
    )
    op.create_index("ix_case_runs_run_id", "case_runs", ["run_id"])
    op.create_index("ix_case_runs_tenant_id", "case_runs", ["tenant_id"])
    op.create_index("ix_case_runs_testcase_id", "case_runs", ["testcase_id"])
    op.create_index("ix_case_runs_run_status", "case_runs", ["run_id", "status"])

    op.create_table(
        "artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("type", artifact_type, nullable=False),
        sa.Column("storage_url", sa.String(length=2048), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=True),
        sa.Column("meta_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["case_run_id"], ["case_runs.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
    )
    op.create_index("ix_artifacts_case_run_id", "artifacts", ["case_run_id"])
    op.create_index("ix_artifacts_run_id", "artifacts", ["run_id"])
    op.create_index("ix_artifacts_tenant_id", "artifacts", ["tenant_id"])

    op.create_table(
        "ai_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("context_refs_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
    )
    op.create_index("ix_ai_records_created_by", "ai_records", ["created_by"])
    op.create_index("ix_ai_records_project_id", "ai_records", ["project_id"])
    op.create_index("ix_ai_records_tenant_id", "ai_records", ["tenant_id"])

    op.create_table(
        "issue_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("issue_key", sa.String(length=128), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["case_run_id"], ["case_runs.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
    )
    op.create_index("ix_issue_links_case_run_id", "issue_links", ["case_run_id"])
    op.create_index("ix_issue_links_run_id", "issue_links", ["run_id"])
    op.create_index("ix_issue_links_tenant_id", "issue_links", ["tenant_id"])

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("target", sa.String(length=2048), nullable=False),
        sa.Column("rule_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
    )
    op.create_index("ix_notifications_project_id", "notifications", ["project_id"])
    op.create_index("ix_notifications_tenant_id", "notifications", ["tenant_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=False),
        sa.Column("detail_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_tenant_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_notifications_tenant_id", table_name="notifications")
    op.drop_index("ix_notifications_project_id", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_issue_links_tenant_id", table_name="issue_links")
    op.drop_index("ix_issue_links_run_id", table_name="issue_links")
    op.drop_index("ix_issue_links_case_run_id", table_name="issue_links")
    op.drop_table("issue_links")

    op.drop_index("ix_ai_records_tenant_id", table_name="ai_records")
    op.drop_index("ix_ai_records_project_id", table_name="ai_records")
    op.drop_index("ix_ai_records_created_by", table_name="ai_records")
    op.drop_table("ai_records")

    op.drop_index("ix_artifacts_tenant_id", table_name="artifacts")
    op.drop_index("ix_artifacts_run_id", table_name="artifacts")
    op.drop_index("ix_artifacts_case_run_id", table_name="artifacts")
    op.drop_table("artifacts")

    op.drop_index("ix_case_runs_run_status", table_name="case_runs")
    op.drop_index("ix_case_runs_testcase_id", table_name="case_runs")
    op.drop_index("ix_case_runs_tenant_id", table_name="case_runs")
    op.drop_index("ix_case_runs_run_id", table_name="case_runs")
    op.drop_table("case_runs")

    op.drop_index("ix_jobs_worker_id", table_name="jobs")
    op.drop_index("ix_jobs_tenant_id", table_name="jobs")
    op.drop_index("ix_jobs_run_id", table_name="jobs")
    op.drop_table("jobs")

    op.drop_index("ix_runs_project_start_at_desc", table_name="runs")
    op.drop_index("ix_runs_tenant_id", table_name="runs")
    op.drop_index("ix_runs_suite_id", table_name="runs")
    op.drop_index("ix_runs_start_at", table_name="runs")
    op.drop_index("ix_runs_project_id", table_name="runs")
    op.drop_index("ix_runs_env_id", table_name="runs")
    op.drop_index("ix_runs_created_by", table_name="runs")
    op.drop_table("runs")

    op.drop_index("ix_workers_tenant_last_seen_at_desc", table_name="workers")
    op.drop_index("ix_workers_last_seen_at", table_name="workers")
    op.drop_index("ix_workers_tenant_id", table_name="workers")
    op.drop_table("workers")

    op.drop_index("ix_test_data_sets_tenant_id", table_name="test_data_sets")
    op.drop_index("ix_test_data_sets_project_id", table_name="test_data_sets")
    op.drop_table("test_data_sets")

    op.drop_index("ix_api_requests_tenant_id", table_name="api_requests")
    op.drop_index("ix_api_requests_collection_id", table_name="api_requests")
    op.drop_table("api_requests")

    op.drop_index("ix_api_collections_tenant_id", table_name="api_collections")
    op.drop_index("ix_api_collections_project_id", table_name="api_collections")
    op.drop_table("api_collections")

    op.drop_index("ix_suite_items_suite_order_no", table_name="suite_items")
    op.drop_index("ix_suite_items_testcase_id", table_name="suite_items")
    op.drop_index("ix_suite_items_tenant_id", table_name="suite_items")
    op.drop_index("ix_suite_items_suite_id", table_name="suite_items")
    op.drop_table("suite_items")

    op.drop_index("ix_suites_tenant_id", table_name="suites")
    op.drop_index("ix_suites_project_id", table_name="suites")
    op.drop_index("ix_suites_created_by", table_name="suites")
    op.drop_table("suites")

    op.drop_index("ix_testcase_versions_testcase_version", table_name="testcase_versions")
    op.drop_index("ix_testcase_versions_testcase_id", table_name="testcase_versions")
    op.drop_index("ix_testcase_versions_tenant_id", table_name="testcase_versions")
    op.drop_index("ix_testcase_versions_created_by", table_name="testcase_versions")
    op.drop_table("testcase_versions")

    op.drop_index("ix_testcases_project_updated_at_desc", table_name="testcases")
    op.drop_index("ix_testcases_tenant_id", table_name="testcases")
    op.drop_index("ix_testcases_project_id", table_name="testcases")
    op.drop_index("ix_testcases_owner_id", table_name="testcases")
    op.drop_index("ix_testcases_created_by", table_name="testcases")
    op.drop_table("testcases")

    op.drop_index("ix_environments_tenant_id", table_name="environments")
    op.drop_index("ix_environments_project_id", table_name="environments")
    op.drop_table("environments")

    op.drop_index("ix_project_members_user_id", table_name="project_members")
    op.drop_index("ix_project_members_tenant_id", table_name="project_members")
    op.drop_index("ix_project_members_project_id", table_name="project_members")
    op.drop_table("project_members")

    op.drop_index("ix_projects_tenant_id", table_name="projects")
    op.drop_index("ix_projects_owner_id", table_name="projects")
    op.drop_table("projects")

    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_table("users")

    op.drop_table("tenants")

    bind = op.get_bind()
    for enum_type in [
        sa.Enum(name="worker_status"),
        sa.Enum(name="artifact_type"),
        sa.Enum(name="case_run_status"),
        sa.Enum(name="job_status"),
        sa.Enum(name="run_status"),
        sa.Enum(name="trigger_type"),
        sa.Enum(name="testcase_status"),
        sa.Enum(name="priority"),
        sa.Enum(name="testcase_type"),
        sa.Enum(name="project_role"),
        sa.Enum(name="user_status"),
    ]:
        enum_type.drop(bind, checkfirst=True)
