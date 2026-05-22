from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0007_ai_import_binding_reports"
down_revision = "0006_api_collection_groups"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("testcases", sa.Column("feature", sa.String(length=128), nullable=True))
    op.add_column("testcases", sa.Column("story", sa.String(length=128), nullable=True))
    op.add_column("testcases", sa.Column("api_url", sa.String(length=1024), nullable=True))
    op.add_column("testcases", sa.Column("api_method", sa.String(length=16), nullable=True))
    op.add_column(
        "testcases",
        sa.Column(
            "ai_meta_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "testcases",
        sa.Column("generated_by_ai", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_testcases_project_feature", "testcases", ["project_id", "feature"])
    op.create_index("ix_testcases_project_story", "testcases", ["project_id", "story"])
    op.create_index("ix_testcases_project_api_url", "testcases", ["project_id", "api_url"])

    op.create_table(
        "ai_import_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column(
            "source_type",
            sa.String(length=32),
            sa.CheckConstraint("source_type IN ('PRD_DOC', 'FIGMA_LINK', 'HTML_DOC')"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            sa.CheckConstraint("status IN ('PENDING', 'UPLOADED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'COMMITTED')"),
            nullable=False,
        ),
        sa.Column(
            "source_ref_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "generate_config_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "skill_config_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "summary_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_ai_import_jobs_tenant_project_created",
        "ai_import_jobs",
        ["tenant_id", "project_id", sa.text("created_at DESC")],
        postgresql_using="btree",
    )

    op.create_table(
        "ai_import_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_import_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("priority", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("feature", sa.String(length=128), nullable=True),
        sa.Column("epic", sa.String(length=128), nullable=True),
        sa.Column("story", sa.String(length=128), nullable=True),
        sa.Column("task", sa.String(length=128), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "steps_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("api_url", sa.String(length=1024), nullable=True),
        sa.Column("api_method", sa.String(length=16), nullable=True),
        sa.Column(
            "tags_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "ai_meta_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("dedupe_key", sa.String(length=256), nullable=True),
        sa.Column("selected", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ai_import_items_job", "ai_import_items", ["job_id"])
    op.create_index("ix_ai_import_items_project_story", "ai_import_items", ["project_id", "story"])

    op.create_table(
        "api_targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("base_url", sa.String(length=2048), nullable=False),
        sa.Column("default_method", sa.String(length=16), nullable=True),
        sa.Column("default_path", sa.String(length=1024), nullable=True),
        sa.Column(
            "headers_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "auth_ref_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("timeout_ms", sa.Integer(), nullable=False, server_default="10000"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "uq_api_targets_tenant_project_name",
        "api_targets",
        ["tenant_id", "project_id", "name"],
        unique=True,
    )

    op.create_table(
        "testcase_bindings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column(
            "testcase_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("testcases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_data_sets.id"), nullable=True),
        sa.Column("api_target_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("api_targets.id"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "params_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_testcase_bindings_testcase", "testcase_bindings", ["testcase_id"])
    op.create_index(
        "uq_testcase_bindings_name",
        "testcase_bindings",
        ["tenant_id", "testcase_id", "name"],
        unique=True,
    )

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column(
            "report_type",
            sa.String(length=32),
            sa.CheckConstraint("report_type IN ('ALLURE')"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            sa.CheckConstraint("status IN ('GENERATING', 'READY', 'FAILED')"),
            nullable=False,
        ),
        sa.Column(
            "summary_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("allure_result_key", sa.String(length=1024), nullable=True),
        sa.Column("allure_report_url", sa.String(length=2048), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("uq_reports_run_type", "reports", ["run_id", "report_type"], unique=True)
    op.create_index(
        "ix_reports_project_created",
        "reports",
        ["project_id", sa.text("created_at DESC")],
        postgresql_using="btree",
    )


def downgrade() -> None:
    op.drop_index("ix_reports_project_created", table_name="reports")
    op.drop_index("uq_reports_run_type", table_name="reports")
    op.drop_table("reports")

    op.drop_index("uq_testcase_bindings_name", table_name="testcase_bindings")
    op.drop_index("ix_testcase_bindings_testcase", table_name="testcase_bindings")
    op.drop_table("testcase_bindings")

    op.drop_index("uq_api_targets_tenant_project_name", table_name="api_targets")
    op.drop_table("api_targets")

    op.drop_index("ix_ai_import_items_project_story", table_name="ai_import_items")
    op.drop_index("ix_ai_import_items_job", table_name="ai_import_items")
    op.drop_table("ai_import_items")

    op.drop_index("ix_ai_import_jobs_tenant_project_created", table_name="ai_import_jobs")
    op.drop_table("ai_import_jobs")

    op.drop_index("ix_testcases_project_api_url", table_name="testcases")
    op.drop_index("ix_testcases_project_story", table_name="testcases")
    op.drop_index("ix_testcases_project_feature", table_name="testcases")
    op.drop_column("testcases", "generated_by_ai")
    op.drop_column("testcases", "ai_meta_json")
    op.drop_column("testcases", "api_method")
    op.drop_column("testcases", "api_url")
    op.drop_column("testcases", "story")
    op.drop_column("testcases", "feature")
