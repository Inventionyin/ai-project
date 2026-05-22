from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.dashboard import router as dashboard_router
from app.api.v1.endpoints.acceptance import router as acceptance_router
from app.api.v1.endpoints.environments import router as environments_router
from app.api.v1.endpoints.api_targets import router as api_targets_router
from app.api.v1.endpoints.projects import router as projects_router
from app.api.v1.endpoints.runs import router as runs_router
from app.api.v1.endpoints.suites import router as suites_router
from app.api.v1.endpoints.testcases import router as testcases_router
from app.api.v1.endpoints.testcase_bindings import router as testcase_bindings_router
from app.api.v1.endpoints.collections import router as collections_router
from app.api.v1.endpoints.worker import router as worker_router
from app.api.v1.endpoints.doc_ingest import router as doc_ingest_router
from app.api.v1.endpoints.ui_tests import router as ui_tests_router
from app.api.v1.endpoints.requirements import router as requirements_router
from app.api.v1.endpoints.platform_records import router as platform_records_router
from app.api.v1.endpoints.requirement_changes import router as requirement_changes_router
from app.api.v1.endpoints.defects import router as defects_router
from app.api.v1.endpoints.knowledge import router as knowledge_router
from app.api.v1.endpoints.knowledge import templates_router as knowledge_templates_router
from app.api.v1.endpoints.integrations import router as integrations_router
from app.api.v1.endpoints.integration_issues import router as integration_issues_router
from app.api.v1.endpoints.prompt_templates import router as prompt_templates_router
from app.api.v1.endpoints.doc_parse_jobs import router as doc_parse_jobs_router
from app.api.v1.endpoints.devops import router as devops_router
from app.api.v1.endpoints.security_policy import router as security_policy_router
from app.api.v1.endpoints.executors import router as executors_router
from app.api.v1.endpoints.plugins import router as plugins_router
from app.api.v1.endpoints.plugins import project_router as plugins_project_router
from app.api.v1.endpoints.ops import router as ops_router

router = APIRouter()
router.include_router(auth_router, tags=["auth"])
router.include_router(projects_router, tags=["projects"])
router.include_router(api_targets_router, tags=["api-targets"])
router.include_router(testcases_router, tags=["testcases"])
router.include_router(testcase_bindings_router, tags=["testcase-bindings"])
router.include_router(suites_router, tags=["suites"])
router.include_router(environments_router, tags=["environments"])
router.include_router(runs_router, tags=["runs"])
router.include_router(collections_router, tags=["collections"])
router.include_router(dashboard_router, tags=["dashboard"])
router.include_router(acceptance_router, tags=["acceptance"])
router.include_router(worker_router, tags=["workers"])
router.include_router(doc_ingest_router, tags=["doc-ingest"])
router.include_router(ui_tests_router, tags=["ui-tests"])
router.include_router(requirements_router, tags=["requirements"])
router.include_router(platform_records_router, tags=["platform-records"])
router.include_router(requirement_changes_router, tags=["requirement-changes"])
router.include_router(defects_router, tags=["defects"])
router.include_router(knowledge_router, tags=["knowledge"])
router.include_router(knowledge_templates_router, tags=["knowledge-templates"])
router.include_router(integrations_router, tags=["integrations"])
router.include_router(integration_issues_router, tags=["integration-issues"])
router.include_router(prompt_templates_router, tags=["prompt-templates"])
router.include_router(doc_parse_jobs_router, tags=["doc-parse-jobs"])
router.include_router(devops_router, tags=["devops"])
router.include_router(security_policy_router, tags=["security-policy"])
router.include_router(executors_router, tags=["executors"])
router.include_router(plugins_router, tags=["plugins"])
router.include_router(plugins_project_router, tags=["plugins-project"])
router.include_router(ops_router, tags=["ops"])
