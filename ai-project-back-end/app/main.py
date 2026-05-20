import sys
import asyncio

# 兼容 Windows 平台的 asyncio 子进程调用 (NotImplementedError 修复)
# 必须在任何异步操作（如 asyncpg, uvicorn 循环启动）之前设置
if sys.platform == 'win32':
    # 强制设置 ProactorEventLoopPolicy
    try:
        if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception as e:
        # 如果策略设置失败，通常是因为循环已经运行，但至少我们尝试了
        print(f"Warning: Failed to set ProactorEventLoopPolicy: {e}")

import logging
from pathlib import Path

try:
    import asyncpg
except ModuleNotFoundError:  # pragma: no cover - optional dependency in test env
    asyncpg = None

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException


from app.api.deps import get_request_id
from app.api.router import api_router
from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.database import get_sessionmaker
from app.core.observability import mask_sensitive_mapping, mask_sensitive_text
from app.services.integration_delivery import run_notification_outbox_consumer
from app.services.doc_parse_job import run_doc_parse_job_consumer

logger = logging.getLogger(__name__)

# Request logging middleware
async def log_requests(request: Request, call_next):
    request_id = await get_request_id(request)
    path = request.url.path
    if request.query_params:
        path += f"?{mask_sensitive_mapping(dict(request.query_params))}"
    
    logger.info(f"[{request_id}] Incoming request: {request.method} {path}")
    
    import time
    start_time = time.time()
    
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    
    process_time = (time.time() - start_time) * 1000
    logger.info(f"[{request_id}] Completed request: {request.method} {path} - Status: {response.status_code} - Time: {process_time:.2f}ms")
    
    return response


def _run_migrations() -> None:
    alembic_ini = Path(__file__).resolve().parents[1] / "alembic.ini"
    config = Config(str(alembic_ini))
    command.upgrade(config, "head")


def create_app() -> FastAPI:
    settings = get_settings()

    application = FastAPI(title=settings.app_name, debug=settings.debug)

    # Add request logging middleware
    application.middleware("http")(log_requests)

    @application.on_event("startup")
    async def run_startup_migrations() -> None:
        if settings.env != "local":
            return
        try:
            await asyncio.to_thread(_run_migrations)
        except Exception as exc:
            logger.exception("Failed to run startup migrations", exc_info=exc)

    @application.on_event("startup")
    async def start_notification_outbox_consumer() -> None:
        if settings.env != "local" or not settings.notification_outbox_consumer_enabled:
            return
        stop_event = asyncio.Event()
        task = asyncio.create_task(
            run_notification_outbox_consumer(
                stop_event=stop_event,
                sessionmaker=get_sessionmaker(),
                poll_interval_seconds=settings.notification_outbox_poll_interval_seconds,
                batch_size=settings.notification_outbox_batch_size,
                retry_base_seconds=settings.notification_outbox_retry_base_seconds,
            )
        )
        application.state.notification_outbox_stop_event = stop_event
        application.state.notification_outbox_task = task

    @application.on_event("startup")
    async def start_doc_parse_job_consumer() -> None:
        if settings.env != "local":
            return
        stop_event = asyncio.Event()
        task = asyncio.create_task(
            run_doc_parse_job_consumer(
                stop_event=stop_event,
                sessionmaker=get_sessionmaker(),
                poll_interval_seconds=3.0,
                batch_size=5,
            )
        )
        application.state.doc_parse_stop_event = stop_event
        application.state.doc_parse_task = task

    @application.on_event("shutdown")
    async def stop_notification_outbox_consumer() -> None:
        stop_event = getattr(application.state, "notification_outbox_stop_event", None)
        task = getattr(application.state, "notification_outbox_task", None)
        if stop_event is None or task is None:
            return
        stop_event.set()
        try:
            await task
        except Exception:
            logger.exception("Notification outbox consumer shutdown failed")

    @application.on_event("shutdown")
    async def stop_doc_parse_job_consumer() -> None:
        stop_event = getattr(application.state, "doc_parse_stop_event", None)
        task = getattr(application.state, "doc_parse_task", None)
        if stop_event is None or task is None:
            return
        stop_event.set()
        try:
            await task
        except Exception:
            logger.exception("Doc parse job consumer shutdown failed")

    cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    cors_allow_methods = [m.strip() for m in settings.cors_allow_methods.split(",") if m.strip()]
    cors_allow_headers = [h.strip() for h in settings.cors_allow_headers.split(",") if h.strip()]

    if cors_origins == ["*"]:
        cors_origins = ["*"]
        cors_allow_methods = ["*"]
        cors_allow_headers = ["*"]

    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=cors_allow_methods or ["*"],
        allow_headers=cors_allow_headers or ["*"],
    )

    def _map_status_to_code(status_code: int) -> int:
        if status_code in (400, 422):
            return 40001
        if status_code == 401:
            return 40101
        if status_code == 403:
            return 40301
        if status_code == 404:
            return 40401
        if status_code == 405:
            return 40501
        if status_code == 409:
            return 40901
        if status_code == 429:
            return 42901
        if status_code == 503:
            return 50301
        return 50001

    @application.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_id = await get_request_id(request)
        return JSONResponse(
            status_code=200,
            content={
                "code": _map_status_to_code(exc.status_code),
                "message": str(exc.detail) if exc.detail is not None else "error",
                "data": None,
                "requestId": request_id,
            },
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = await get_request_id(request)
        return JSONResponse(
            status_code=200,
            content={
                "code": 40001,
                "message": "参数校验失败",
                "data": {"errors": exc.errors()},
                "requestId": request_id,
            },
        )

    if asyncpg is not None:
        @application.exception_handler(asyncpg.PostgresError)
        async def asyncpg_exception_handler(request: Request, exc: asyncpg.PostgresError) -> JSONResponse:
            logger.exception("Database error", exc_info=exc)
            request_id = await get_request_id(request)
            return JSONResponse(
                status_code=200,
                content={
                    "code": 50301,
                    "message": "db_unavailable",
                    "data": None,
                    "requestId": request_id,
                },
            )

    @application.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("Database error", exc_info=exc)
        request_id = await get_request_id(request)
        return JSONResponse(
            status_code=200,
            content={
                "code": 50301,
                "message": "db_unavailable",
                "data": None,
                "requestId": request_id,
            },
        )

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception", exc_info=exc)
        request_id = await get_request_id(request)
        return JSONResponse(
            status_code=200,
            content={
                "code": 50001,
                "message": "服务内部错误",
                "data": None,
                "requestId": request_id,
            },
        )

    application.include_router(health_router, tags=["health"])
    application.include_router(api_router, prefix=settings.api_prefix)
    return application


app = create_app()

