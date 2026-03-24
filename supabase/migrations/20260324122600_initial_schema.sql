BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001_init_models

CREATE TYPE user_status AS ENUM ('ACTIVE', 'DISABLED');

CREATE TYPE project_role AS ENUM ('ADMIN', 'OWNER', 'EDITOR', 'VIEWER');

CREATE TYPE testcase_type AS ENUM ('API', 'UI', 'PERF', 'MIX');

CREATE TYPE priority AS ENUM ('P0', 'P1', 'P2', 'P3');

CREATE TYPE testcase_status AS ENUM ('DRAFT', 'REVIEWED', 'DEPRECATED');

CREATE TYPE trigger_type AS ENUM ('MANUAL', 'CRON', 'CI', 'WEBHOOK');

CREATE TYPE run_status AS ENUM ('QUEUED', 'RUNNING', 'PASSED', 'FAILED', 'CANCELED');

CREATE TYPE job_status AS ENUM ('QUEUED', 'RUNNING', 'DONE', 'FAILED', 'CANCELED');

CREATE TYPE case_run_status AS ENUM ('QUEUED', 'RUNNING', 'PASSED', 'FAILED', 'SKIPPED');

CREATE TYPE artifact_type AS ENUM ('API_EXCHANGE', 'SCREENSHOT', 'VIDEO', 'TRACE', 'LOG_BUNDLE', 'PERF_REPORT');

CREATE TYPE worker_status AS ENUM ('ONLINE', 'OFFLINE');

CREATE TABLE tenants (
    id UUID NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE TABLE users (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    email VARCHAR(255), 
    name VARCHAR(255) NOT NULL, 
    status user_status NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    username VARCHAR(255), 
    hashed_password VARCHAR(255) DEFAULT '' NOT NULL, 
    roles_json JSONB DEFAULT '[]'::jsonb NOT NULL, 
    phone VARCHAR(32), 
    PRIMARY KEY (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
    CONSTRAINT uq_users_tenant_email UNIQUE (tenant_id, email), 
    CONSTRAINT uq_users_tenant_username UNIQUE (tenant_id, username), 
    CONSTRAINT uq_users_tenant_phone UNIQUE (tenant_id, phone)
);

CREATE INDEX ix_users_tenant_id ON users (tenant_id);

CREATE TABLE projects (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    owner_id UUID NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    description TEXT, 
    PRIMARY KEY (id), 
    FOREIGN KEY(owner_id) REFERENCES users (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
    CONSTRAINT uq_projects_tenant_name UNIQUE (tenant_id, name)
);

CREATE INDEX ix_projects_owner_id ON projects (owner_id);

CREATE INDEX ix_projects_tenant_id ON projects (tenant_id);

CREATE TABLE project_members (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    project_id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    role project_role NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
    FOREIGN KEY(user_id) REFERENCES users (id), 
    CONSTRAINT uq_project_members_project_user UNIQUE (project_id, user_id)
);

CREATE INDEX ix_project_members_project_id ON project_members (project_id);

CREATE INDEX ix_project_members_tenant_id ON project_members (tenant_id);

CREATE INDEX ix_project_members_user_id ON project_members (user_id);

CREATE TABLE environments (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    project_id UUID NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    base_url VARCHAR(2048) NOT NULL, 
    variables_json JSONB NOT NULL, 
    secrets_ref VARCHAR(512), 
    health_config_json JSONB, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX ix_environments_project_id ON environments (project_id);

CREATE INDEX ix_environments_tenant_id ON environments (tenant_id);

CREATE TABLE testcases (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    project_id UUID NOT NULL, 
    title VARCHAR(100) NOT NULL, 
    type testcase_type NOT NULL, 
    priority priority NOT NULL, 
    status testcase_status NOT NULL, 
    content_md TEXT NOT NULL, 
    tags_json JSONB NOT NULL, 
    owner_id UUID, 
    created_by UUID, 
    version INTEGER NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    feature VARCHAR(128), 
    story VARCHAR(128), 
    api_url VARCHAR(1024), 
    api_method VARCHAR(16), 
    ai_meta_json JSONB DEFAULT '{}'::jsonb NOT NULL, 
    generated_by_ai BOOLEAN DEFAULT false NOT NULL, 
    test_case_id VARCHAR(64), 
    PRIMARY KEY (id), 
    FOREIGN KEY(created_by) REFERENCES users (id), 
    FOREIGN KEY(owner_id) REFERENCES users (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX ix_testcases_created_by ON testcases (created_by);

CREATE INDEX ix_testcases_owner_id ON testcases (owner_id);

CREATE INDEX ix_testcases_project_id ON testcases (project_id);

CREATE INDEX ix_testcases_tenant_id ON testcases (tenant_id);

CREATE INDEX ix_testcases_project_updated_at_desc ON testcases USING btree (project_id, updated_at DESC);

CREATE INDEX ix_testcases_project_feature ON testcases (project_id, feature);

CREATE INDEX ix_testcases_project_story ON testcases (project_id, story);

CREATE INDEX ix_testcases_project_api_url ON testcases (project_id, api_url);

CREATE UNIQUE INDEX uq_testcases_project_test_case_id ON testcases (project_id, test_case_id) WHERE test_case_id IS NOT NULL;

CREATE TABLE testcase_versions (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    testcase_id UUID NOT NULL, 
    version INTEGER NOT NULL, 
    content_md TEXT NOT NULL, 
    created_by UUID, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(created_by) REFERENCES users (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
    FOREIGN KEY(testcase_id) REFERENCES testcases (id)
);

CREATE INDEX ix_testcase_versions_created_by ON testcase_versions (created_by);

CREATE INDEX ix_testcase_versions_tenant_id ON testcase_versions (tenant_id);

CREATE INDEX ix_testcase_versions_testcase_id ON testcase_versions (testcase_id);

CREATE UNIQUE INDEX ix_testcase_versions_testcase_version ON testcase_versions (testcase_id, version);

CREATE TABLE suites (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    project_id UUID NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    config_json JSONB NOT NULL, 
    created_by UUID, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(created_by) REFERENCES users (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX ix_suites_created_by ON suites (created_by);

CREATE INDEX ix_suites_project_id ON suites (project_id);

CREATE INDEX ix_suites_tenant_id ON suites (tenant_id);

CREATE TABLE suite_items (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    suite_id UUID NOT NULL, 
    testcase_id UUID NOT NULL, 
    order_no INTEGER NOT NULL, 
    params_json JSONB NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(suite_id) REFERENCES suites (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
    FOREIGN KEY(testcase_id) REFERENCES testcases (id)
);

CREATE INDEX ix_suite_items_suite_id ON suite_items (suite_id);

CREATE INDEX ix_suite_items_tenant_id ON suite_items (tenant_id);

CREATE INDEX ix_suite_items_testcase_id ON suite_items (testcase_id);

CREATE UNIQUE INDEX ix_suite_items_suite_order_no ON suite_items (suite_id, order_no);

CREATE TABLE api_collections (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    project_id UUID NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    variables_json JSONB NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX ix_api_collections_project_id ON api_collections (project_id);

CREATE INDEX ix_api_collections_tenant_id ON api_collections (tenant_id);

CREATE TABLE api_collection_groups (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    collection_id UUID NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    "order" INTEGER DEFAULT '0' NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
    FOREIGN KEY(collection_id) REFERENCES api_collections (id)
);

CREATE INDEX ix_api_collection_groups_tenant_id ON api_collection_groups (tenant_id);

CREATE INDEX ix_api_collection_groups_collection_id ON api_collection_groups (collection_id);

CREATE TABLE api_requests (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    collection_id UUID NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    method VARCHAR(16) NOT NULL, 
    url VARCHAR(2048) NOT NULL, 
    headers_json JSONB NOT NULL, 
    body_json JSONB NOT NULL, 
    asserts_json JSONB NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    group_id UUID, 
    auth_json JSONB DEFAULT '{}'::jsonb NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(collection_id) REFERENCES api_collections (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
    FOREIGN KEY(group_id) REFERENCES api_collection_groups (id)
);

CREATE INDEX ix_api_requests_collection_id ON api_requests (collection_id);

CREATE INDEX ix_api_requests_tenant_id ON api_requests (tenant_id);

CREATE INDEX ix_api_requests_group_id ON api_requests (group_id);

CREATE TABLE test_data_sets (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    project_id UUID NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    type VARCHAR(32) NOT NULL, 
    content_blob_ref VARCHAR(1024), 
    schema_json JSONB, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX ix_test_data_sets_project_id ON test_data_sets (project_id);

CREATE INDEX ix_test_data_sets_tenant_id ON test_data_sets (tenant_id);

CREATE TABLE workers (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    token_hash VARCHAR(255) NOT NULL, 
    capabilities_json JSONB NOT NULL, 
    slots INTEGER NOT NULL, 
    status worker_status NOT NULL, 
    last_seen_at TIMESTAMP WITHOUT TIME ZONE, 
    version VARCHAR(64), 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
    UNIQUE (token_hash)
);

CREATE INDEX ix_workers_tenant_id ON workers (tenant_id);

CREATE INDEX ix_workers_last_seen_at ON workers (last_seen_at);

CREATE INDEX ix_workers_tenant_last_seen_at_desc ON workers USING btree (tenant_id, last_seen_at DESC);

CREATE TABLE environments (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    project_id UUID NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    base_url VARCHAR(2048) NOT NULL, 
    variables_json JSONB NOT NULL, 
    secrets_ref VARCHAR(512), 
    health_config_json JSONB, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE TABLE runs (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    project_id UUID NOT NULL, 
    suite_id UUID, 
    env_id UUID, 
    trigger_type trigger_type NOT NULL, 
    status run_status NOT NULL, 
    start_at TIMESTAMP WITHOUT TIME ZONE, 
    end_at TIMESTAMP WITHOUT TIME ZONE, 
    summary_json JSONB NOT NULL, 
    created_by UUID, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    idempotency_key VARCHAR(128), 
    PRIMARY KEY (id), 
    FOREIGN KEY(created_by) REFERENCES users (id), 
    FOREIGN KEY(env_id) REFERENCES environments (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id), 
    FOREIGN KEY(suite_id) REFERENCES suites (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
    CONSTRAINT uq_runs_tenant_project_idempotency_key UNIQUE (tenant_id, project_id, idempotency_key)
);

CREATE INDEX ix_runs_created_by ON runs (created_by);

CREATE INDEX ix_runs_env_id ON runs (env_id);

CREATE INDEX ix_runs_project_id ON runs (project_id);

CREATE INDEX ix_runs_start_at ON runs (start_at);

CREATE INDEX ix_runs_suite_id ON runs (suite_id);

CREATE INDEX ix_runs_tenant_id ON runs (tenant_id);

CREATE INDEX ix_runs_project_start_at_desc ON runs USING btree (project_id, start_at DESC);

CREATE TABLE jobs (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    run_id UUID NOT NULL, 
    worker_id UUID, 
    status job_status NOT NULL, 
    start_at TIMESTAMP WITHOUT TIME ZONE, 
    end_at TIMESTAMP WITHOUT TIME ZONE, 
    meta_json JSONB NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(run_id) REFERENCES runs (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
    FOREIGN KEY(worker_id) REFERENCES workers (id)
);

CREATE INDEX ix_jobs_run_id ON jobs (run_id);

CREATE INDEX ix_jobs_tenant_id ON jobs (tenant_id);

CREATE INDEX ix_jobs_worker_id ON jobs (worker_id);

CREATE TABLE case_runs (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    run_id UUID NOT NULL, 
    testcase_id UUID NOT NULL, 
    status case_run_status NOT NULL, 
    start_at TIMESTAMP WITHOUT TIME ZONE, 
    end_at TIMESTAMP WITHOUT TIME ZONE, 
    error_type VARCHAR(64), 
    error_message TEXT, 
    metrics_json JSONB NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(run_id) REFERENCES runs (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
    FOREIGN KEY(testcase_id) REFERENCES testcases (id)
);

CREATE INDEX ix_case_runs_run_id ON case_runs (run_id);

CREATE INDEX ix_case_runs_tenant_id ON case_runs (tenant_id);

CREATE INDEX ix_case_runs_testcase_id ON case_runs (testcase_id);

CREATE INDEX ix_case_runs_run_status ON case_runs (run_id, status);

CREATE TABLE artifacts (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    run_id UUID NOT NULL, 
    case_run_id UUID, 
    type artifact_type NOT NULL, 
    storage_url VARCHAR(2048) NOT NULL, 
    size BIGINT, 
    meta_json JSONB NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(case_run_id) REFERENCES case_runs (id), 
    FOREIGN KEY(run_id) REFERENCES runs (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX ix_artifacts_case_run_id ON artifacts (case_run_id);

CREATE INDEX ix_artifacts_run_id ON artifacts (run_id);

CREATE INDEX ix_artifacts_tenant_id ON artifacts (tenant_id);

CREATE TABLE ai_records (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    project_id UUID NOT NULL, 
    entity_type VARCHAR(64) NOT NULL, 
    entity_id VARCHAR(128) NOT NULL, 
    model VARCHAR(128) NOT NULL, 
    prompt TEXT NOT NULL, 
    context_refs_json JSONB NOT NULL, 
    output_json JSONB NOT NULL, 
    created_by UUID, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(created_by) REFERENCES users (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX ix_ai_records_created_by ON ai_records (created_by);

CREATE INDEX ix_ai_records_project_id ON ai_records (project_id);

CREATE INDEX ix_ai_records_tenant_id ON ai_records (tenant_id);

CREATE TABLE issue_links (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    run_id UUID NOT NULL, 
    case_run_id UUID, 
    provider VARCHAR(64) NOT NULL, 
    issue_key VARCHAR(128) NOT NULL, 
    url VARCHAR(2048) NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(case_run_id) REFERENCES case_runs (id), 
    FOREIGN KEY(run_id) REFERENCES runs (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX ix_issue_links_case_run_id ON issue_links (case_run_id);

CREATE INDEX ix_issue_links_run_id ON issue_links (run_id);

CREATE INDEX ix_issue_links_tenant_id ON issue_links (tenant_id);

CREATE TABLE notifications (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    project_id UUID NOT NULL, 
    channel VARCHAR(32) NOT NULL, 
    target VARCHAR(2048) NOT NULL, 
    rule_json JSONB NOT NULL, 
    enabled BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX ix_notifications_project_id ON notifications (project_id);

CREATE INDEX ix_notifications_tenant_id ON notifications (tenant_id);

CREATE TABLE audit_logs (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    user_id UUID, 
    action VARCHAR(128) NOT NULL, 
    resource_type VARCHAR(64) NOT NULL, 
    resource_id VARCHAR(128) NOT NULL, 
    detail_json JSONB NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
    FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_audit_logs_tenant_id ON audit_logs (tenant_id);

CREATE INDEX ix_audit_logs_user_id ON audit_logs (user_id);

CREATE TABLE ai_import_jobs (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    project_id UUID NOT NULL, 
    source_type VARCHAR(32) NOT NULL CHECK (source_type IN ('PRD_DOC', 'FIGMA_LINK', 'HTML_DOC')), 
    status VARCHAR(32) NOT NULL CHECK (status IN ('PENDING', 'UPLOADED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'COMMITTED')), 
    source_ref_json JSONB DEFAULT '{}'::jsonb NOT NULL, 
    generate_config_json JSONB DEFAULT '{}'::jsonb NOT NULL, 
    skill_config_json JSONB DEFAULT '{}'::jsonb NOT NULL, 
    summary_json JSONB DEFAULT '{}'::jsonb NOT NULL, 
    error_message TEXT, 
    created_by UUID, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id), 
    FOREIGN KEY(created_by) REFERENCES users (id)
);

CREATE INDEX ix_ai_import_jobs_tenant_project_created ON ai_import_jobs USING btree (tenant_id, project_id, created_at DESC);

CREATE TABLE ai_import_items (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    job_id UUID NOT NULL, 
    project_id UUID NOT NULL, 
    title VARCHAR(100) NOT NULL, 
    type VARCHAR(16) NOT NULL, 
    priority VARCHAR(8) NOT NULL, 
    status VARCHAR(16) NOT NULL, 
    feature VARCHAR(128), 
    epic VARCHAR(128), 
    story VARCHAR(128), 
    task VARCHAR(128), 
    description TEXT, 
    steps_json JSONB DEFAULT '[]'::jsonb NOT NULL, 
    api_url VARCHAR(1024), 
    api_method VARCHAR(16), 
    tags_json JSONB DEFAULT '[]'::jsonb NOT NULL, 
    ai_meta_json JSONB DEFAULT '{}'::jsonb NOT NULL, 
    confidence NUMERIC(5, 4), 
    dedupe_key VARCHAR(256), 
    selected BOOLEAN DEFAULT true NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
    FOREIGN KEY(job_id) REFERENCES ai_import_jobs (id) ON DELETE CASCADE, 
    FOREIGN KEY(project_id) REFERENCES projects (id)
);

CREATE INDEX ix_ai_import_items_job ON ai_import_items (job_id);

CREATE INDEX ix_ai_import_items_project_story ON ai_import_items (project_id, story);

CREATE TABLE api_targets (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    project_id UUID NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    base_url VARCHAR(2048) NOT NULL, 
    default_method VARCHAR(16), 
    default_path VARCHAR(1024), 
    headers_json JSONB DEFAULT '{}'::jsonb NOT NULL, 
    auth_ref_json JSONB DEFAULT '{}'::jsonb NOT NULL, 
    timeout_ms INTEGER DEFAULT '10000' NOT NULL, 
    enabled BOOLEAN DEFAULT true NOT NULL, 
    version INTEGER DEFAULT '1' NOT NULL, 
    created_by UUID, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id), 
    FOREIGN KEY(created_by) REFERENCES users (id)
);

CREATE UNIQUE INDEX uq_api_targets_tenant_project_name ON api_targets (tenant_id, project_id, name);

CREATE TABLE testcase_bindings (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    project_id UUID NOT NULL, 
    testcase_id UUID NOT NULL, 
    dataset_id UUID, 
    api_target_id UUID, 
    name VARCHAR(255) NOT NULL, 
    params_json JSONB DEFAULT '{}'::jsonb NOT NULL, 
    priority INTEGER DEFAULT '100' NOT NULL, 
    enabled BOOLEAN DEFAULT true NOT NULL, 
    version INTEGER DEFAULT '1' NOT NULL, 
    created_by UUID, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id), 
    FOREIGN KEY(testcase_id) REFERENCES testcases (id) ON DELETE CASCADE, 
    FOREIGN KEY(dataset_id) REFERENCES test_data_sets (id), 
    FOREIGN KEY(api_target_id) REFERENCES api_targets (id), 
    FOREIGN KEY(created_by) REFERENCES users (id)
);

CREATE INDEX ix_testcase_bindings_testcase ON testcase_bindings (testcase_id);

CREATE UNIQUE INDEX uq_testcase_bindings_name ON testcase_bindings (tenant_id, testcase_id, name);

CREATE TABLE reports (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    project_id UUID NOT NULL, 
    run_id UUID NOT NULL, 
    report_type VARCHAR(32) NOT NULL CHECK (report_type IN ('ALLURE')), 
    status VARCHAR(32) NOT NULL CHECK (status IN ('GENERATING', 'READY', 'FAILED')), 
    summary_json JSONB DEFAULT '{}'::jsonb NOT NULL, 
    allure_result_key VARCHAR(1024), 
    allure_report_url VARCHAR(2048), 
    generated_at TIMESTAMP WITHOUT TIME ZONE, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id), 
    FOREIGN KEY(run_id) REFERENCES runs (id)
);

CREATE UNIQUE INDEX uq_reports_run_type ON reports (run_id, report_type);

CREATE INDEX ix_reports_project_created ON reports USING btree (project_id, created_at DESC);

INSERT INTO alembic_version (version_num) VALUES ('0008_add_test_case_id');

COMMIT;
