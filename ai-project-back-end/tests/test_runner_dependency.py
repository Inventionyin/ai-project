from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.services.runner_pytest_allure import _order_job_items


@dataclass
class _Item:
    caseRunId: str
    testcaseId: str
    testCaseId: str | None = None
    preconditions: str | None = None
    postconditions: str | None = None
    orderNo: int | None = None


def test_order_job_items_toposort_by_depends_on() -> None:
    a = _Item(caseRunId="cr-a", testcaseId="db-a", testCaseId="TC_A", preconditions="")
    b = _Item(caseRunId="cr-b", testcaseId="db-b", testCaseId="TC_B", preconditions='{"dependsOn":["TC_A"]}')
    c = _Item(caseRunId="cr-c", testcaseId="db-c", testCaseId="TC_C", preconditions='{"dependsOn":["TC_B"]}')
    ordered = _order_job_items([c, a, b])
    assert [x.testCaseId for x in ordered] == ["TC_A", "TC_B", "TC_C"]


def test_order_job_items_cycle_detected() -> None:
    a = _Item(caseRunId="cr-a", testcaseId="db-a", testCaseId="TC_A", preconditions='{"dependsOn":["TC_B"]}')
    b = _Item(caseRunId="cr-b", testcaseId="db-b", testCaseId="TC_B", preconditions='{"dependsOn":["TC_A"]}')
    with pytest.raises(ValueError, match=r"dependency_cycle_detected"):
        _order_job_items([a, b])


def test_order_job_items_missing_dependency_rejected() -> None:
    a = _Item(caseRunId="cr-a", testcaseId="db-a", testCaseId="TC_A", preconditions='{"dependsOn":["TC_X"]}')
    with pytest.raises(ValueError, match=r"dependency_not_in_job"):
        _order_job_items([a])

