from enum import Enum


class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class ProjectRole(str, Enum):
    ADMIN = "ADMIN"
    OWNER = "OWNER"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"


class TestCaseType(str, Enum):
    API = "API"
    UI = "UI"
    PERF = "PERF"
    MIX = "MIX"


class Priority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class TestCaseStatus(str, Enum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    DEPRECATED = "DEPRECATED"


class TriggerType(str, Enum):
    MANUAL = "MANUAL"
    CRON = "CRON"
    CI = "CI"
    WEBHOOK = "WEBHOOK"


class RunStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class CaseRunStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ArtifactType(str, Enum):
    API_EXCHANGE = "API_EXCHANGE"
    SCREENSHOT = "SCREENSHOT"
    VIDEO = "VIDEO"
    TRACE = "TRACE"
    LOG_BUNDLE = "LOG_BUNDLE"
    PERF_REPORT = "PERF_REPORT"


class WorkerStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


class AiImportSourceType(str, Enum):
    PRD_DOC = "PRD_DOC"
    FIGMA_LINK = "FIGMA_LINK"
    HTML_DOC = "HTML_DOC"
    API_COLLECTION_DOC = "API_COLLECTION_DOC"


class AiImportJobStatus(str, Enum):
    PENDING = "PENDING"
    UPLOADED = "UPLOADED"
    RUNNING = "RUNNING"
    PARSING = "PARSING"
    PARSED_PREVIEW = "PARSED_PREVIEW"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    COMMITTED = "COMMITTED"
