# API Debugger and Suite Execution Loop Design

## Goal

Build the next productization slice around a clear test workflow:

1. Import or create API requests in a collection.
2. Debug a single request with an environment.
3. Save the debugged request as a testcase binding.
4. Add the testcase to a regression suite.
5. Run the suite.
6. Review the run result from the suite/detail/dashboard surfaces.

This iteration should make the platform feel like a usable test workbench rather than a set of disconnected asset pages.

## Current Baseline

The codebase already has most backend primitives:

- API collections: create/list/detail/import/export/group/request CRUD.
- API execution: `POST /api/collections/{collectionId}/requests/{requestId}/run` and `POST /api/collections/{collectionId}/run`.
- Testcase bindings: bind a testcase to API target/request/collection.
- Suites: create/list/detail/update, upsert ordered suite items.
- Runs: create suite run and inspect run/case-run results.

The frontend already has:

- `CollectionDetail.vue`, with request editing, single request run, export/import, and binding display.
- `SuiteDetailPanel.vue`, with testcase pool, ordered suite table, save, and run.
- `RunsPanel.vue` and dashboard recent-run/failure widgets.

The next slice should therefore connect and refine existing surfaces, not create a separate second product.

## Scope

### In Scope

- Add a focused API debugger area inside collection detail.
- Let users select an environment before running a request.
- Show response status, duration, response body, headers, assertion summary, and error message in a stable result panel.
- Add a clear action to create or update a testcase binding from the selected request.
- Add an action to add the bound testcase to a suite.
- Improve suite cards so "Run" triggers a real suite run instead of a placeholder toast.
- Improve suite detail after run by showing the created run ID and a link to run detail/results.
- Add E2E coverage for the workflow using mocked backend routes.

### Out of Scope

- Full Postman clone features such as script sandbox, pre-request scripts, collection-level auth inheritance, and advanced variable scoping.
- New database tables for API debug history. Debug result can remain transient in this iteration.
- Real network testing from browser. Execution remains backend-side through existing collection run endpoints.
- Drag-and-drop library adoption. Existing move up/down suite ordering is enough for this slice.

## UX Design

### Collection Detail

`CollectionDetail.vue` becomes the primary API workbench for this iteration.

The selected request panel should be organized into compact tabs or sections:

- Request: method, URL, headers, auth, body.
- Assertions: assertion JSON and a short readable summary.
- Debug: environment selector, run button, result panel.
- Bindings: existing testcase bindings plus create/update action.

Controls should use selects for environment and suite selection. The page should avoid adding many always-visible buttons; contextual actions belong near the selected request.

### Debug Result Panel

The result panel should have stable dimensions and support empty/loading/success/failure states:

- Empty: "选择环境后运行请求".
- Loading: disabled run button and inline progress text.
- Success: status code, duration, pass/fail, response body preview.
- Failure: error type/message, request URL, and troubleshooting hint.

Large JSON should render in a monospace pre block with wrapping and a max height.

### Binding and Suite Actions

From a selected request:

- "保存为用例绑定" creates a testcase binding if a target testcase is selected.
- If no testcase exists, the UI should guide the user to create/import cases instead of silently failing.
- "加入测试套件" appears when the selected request has at least one binding.
- Suite selection uses the existing suite list.
- Adding to a suite uses existing suite items, preserves current order, and prevents duplicate testcase IDs.

### Suite List and Detail

`SuitesPanel.vue` should stop using placeholder run behavior.

- Suite cards run the actual suite when the suite has a default environment.
- If no default environment exists, the UI should show a clear error and direct the user to edit suite settings/detail.
- After a successful run, show the run ID and expose a route to run detail/history.

`SuiteDetailPanel.vue` already supports saving ordered items and running. It should add stronger feedback:

- Last run created ID.
- Quick link to run detail.
- Save/run disabled states that explain why an action is unavailable.

## API Design

Prefer existing backend endpoints:

- `GET /api/projects/{projectId}/environments`
- `GET /api/collections/{collectionId}`
- `POST /api/collections/{collectionId}/requests/{requestId}/run`
- `GET /api/projects/{projectId}/requests/{requestId}/bindings`
- `POST /api/testcases/{testcaseId}/bindings`
- `GET /api/suites?projectId=...`
- `GET /api/suites/{suiteId}/items`
- `POST /api/suites/{suiteId}/items`
- `POST /api/runs`
- `GET /api/runs/{runId}`
- `GET /api/runs/{runId}/case-runs`

Frontend API wrappers should be added to `aiTestingPlatformApi.ts` or reused from `lib/api/collections` where already available.

No new backend endpoint is required unless implementation proves a missing atomic operation. If needed, the only acceptable addition in this slice is a small backend helper to append suite items while deduping, but the preferred first implementation should do this through existing `GET items` + `POST items`.

## Data Flow

1. User opens collection detail.
2. Frontend loads collection detail, project environments, collection/request bindings, and suites.
3. User selects request and environment.
4. Frontend calls request quick-run endpoint.
5. Backend executes through existing collection service and returns transient debug result.
6. User binds request to an existing testcase.
7. Frontend creates testcase binding and refreshes bindings.
8. User selects suite and adds testcase.
9. Frontend reads current suite items, appends non-duplicate testcase, posts full ordered item list.
10. User runs suite.
11. Frontend calls `POST /api/runs`, shows run ID, and links to run detail.

## Error Handling

- Missing auth token: use existing auth-expired handling.
- Missing project/collection/request ID: show local validation error before request.
- Invalid JSON in request fields: keep existing JSON parse errors but label the field.
- Missing environment for debug/run: block action with a visible message.
- Duplicate suite testcase: show "已在套件中" and do not call update.
- Backend execution error: preserve backend message and show a concise troubleshooting hint.
- 403: use existing API error message and avoid leaking resource existence.

## Testing

### Frontend E2E

Add or extend `tests/ui/generated/product-information-architecture.spec.ts`:

- Collection detail displays API debugger controls.
- Selecting an environment and running a request shows response status and body.
- A request binding can be shown/refreshed after save action.
- Adding a bound request testcase to a suite shows success and avoids duplicates.
- Suite card run triggers real run API and shows confirmation.

Use mocked routes to keep the E2E stable.

### Backend Tests

Only add backend tests if a new backend helper endpoint/service is required. If existing endpoints are reused, rely on existing collection/suite/run tests and frontend E2E for the integrated flow.

### Build Verification

Run:

- Frontend targeted Playwright spec.
- Frontend build.
- Existing backend focused tests if backend code changes.

## Acceptance Criteria

- A user can debug a selected API request with an environment from the UI.
- The debug result is visible and understandable without opening devtools.
- A user can connect a debugged request to a testcase binding.
- A user can add the bound testcase to a suite from the same workbench.
- Suite list/detail run actions call real APIs and return a run ID.
- The workflow is covered by E2E tests.
- No new secrets, generated reports, or local artifacts are committed.

## Risks and Mitigations

- Risk: Collection detail becomes crowded.
  Mitigation: Use compact sections/tabs and contextual actions.

- Risk: Suite item append through full upsert can overwrite concurrent edits.
  Mitigation: Reload suite items immediately before append and dedupe by testcase ID.

- Risk: Existing quick-run response shape is loose.
  Mitigation: Render defensive fields with fallback labels and test the expected stable subset.

- Risk: Users expect full Postman behavior.
  Mitigation: Label this feature as API debugger and keep advanced scripting out of this iteration.
