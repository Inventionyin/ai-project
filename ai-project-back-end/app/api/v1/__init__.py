from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.dashboard import router as dashboard_router
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
router.include_router(worker_router, tags=["workers"])
router.include_router(doc_ingest_router, tags=["doc-ingest"])
router.include_router(ui_tests_router, tags=["ui-tests"])
router.include_router(requirements_router, tags=["requirements"])
