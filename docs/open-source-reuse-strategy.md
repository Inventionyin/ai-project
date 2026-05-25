# WeiTesting Open Source Reuse Strategy

Last updated: 2026-05-25

This document records the GitHub research result for the meeting-driven WeiTesting optimization work. The goal is to avoid rebuilding mature capabilities from scratch while keeping the main platform lightweight, license-safe, and aligned with the existing Vue + FastAPI project.

## Decision Summary

| Area | Recommended reuse | Use mode | Reason |
| --- | --- | --- | --- |
| Custom dashboard | `gridstack.js`, `echarts`, `vue-echarts` | Direct dependency after POC | Compatible with Vue, active, permissive licenses, covers draggable widgets and charts |
| Asset center / test management | Kiwi TCMS, TestLink, MeterSphere, QuAck, QaraTMS | Reference model/UI only | Many mature ideas, but GPL-heavy or different stacks; avoid copying code |
| API debugging | Hoppscotch, Bruno, Insomnia | Reference product workflow | Full products are too heavy; keep WeiTesting focused and embed only the needed workflow |
| OpenAPI/Postman import/export | `swagger-parser`, `postman-collection`, `openapi-to-postman` | Direct dependency candidate | Library-level scope, suitable for parsing and conversion |
| API case generation | Schemathesis, Keploy | Service/reference candidate | Good for OpenAPI-based boundary tests and traffic replay, but should be isolated |

## Dashboard Candidates

| Project | Link | License | Stack | WeiTesting decision |
| --- | --- | --- | --- | --- |
| Apache ECharts | https://github.com/apache/echarts | Apache-2.0 | TypeScript/JavaScript | Direct chart engine candidate |
| vue-echarts | https://github.com/ecomfe/vue-echarts | MIT | Vue + ECharts | Direct Vue wrapper candidate |
| gridstack.js | https://github.com/gridstack/gridstack.js | MIT | TypeScript | Direct dashboard layout candidate |
| react-grid-layout | https://github.com/react-grid-layout/react-grid-layout | MIT | React/TypeScript | Reference only because current project is Vue |
| Apache Superset | https://github.com/apache/superset | Apache-2.0 | Python + React | Reference only; embedding cost is high |
| Grafana | https://github.com/grafana/grafana | AGPL-3.0 | Go + React | Interaction reference only; do not mix code into product |

Landing direction:

- Add a dashboard layout schema with widget id, position, size, visible state, and version.
- Persist personal layout first; team templates can come later.
- First widgets: requirement coverage, case execution progress, defect severity/status, pass-rate trend, high-risk module TopN.
- Keep filters at the top: project, version, iteration, time range, environment, owner.

## Asset Center Candidates

| Project | Link | License | Stack | WeiTesting decision |
| --- | --- | --- | --- | --- |
| Kiwi TCMS | https://github.com/kiwitcms/Kiwi | GPL-2.0 | Python/Django | Data model reference only |
| TestLink | https://github.com/TestLinkOpenSourceTRMS/testlink-code | GPL-2.0 | PHP | Requirement-case-plan-run model reference only |
| MeterSphere | https://github.com/metersphere/metersphere | GPLv3 with additional branding constraints | Java + Vue | UI and module organization reference only |
| QaraTMS | https://github.com/a13xh7/QaraTMS | MIT, needs license review | PHP/Laravel | Lightweight data model reference |
| QuAck | https://github.com/greatbit/quack | Apache-2.0 | JavaScript | Attribute-driven filtering and heatmap reference |
| Testopia | https://github.com/bugzilla/extensions-Testopia | Bugzilla ecosystem license needs review | Perl/Bugzilla | Defect integration relationship reference |

Landing direction:

- Do not copy GPL product code.
- Normalize core assets around `Requirement`, `TestCase`, `ApiCase`, `TestPlan`, `TestRun`, and `Defect`.
- Use a generic link model: `source_type/source_id/target_type/target_id/link_type`.
- Make import a three-step flow: field mapping, validation preview, submit receipt.
- Make batch operations first-class: edit fields, merge tags, move modules, add/remove links.

## API Debugging And AI Generation Candidates

| Project | Link | License | Stack | WeiTesting decision |
| --- | --- | --- | --- | --- |
| Hoppscotch | https://github.com/hoppscotch/hoppscotch | MIT | TypeScript/Vue | Product workflow reference |
| Bruno | https://github.com/usebruno/bruno | MIT | JavaScript/Electron | Strong reference for Git-friendly API collections |
| Insomnia | https://github.com/Kong/insomnia | Apache-2.0 | TypeScript/Electron | Debugging workflow reference |
| postman-collection | https://github.com/postmanlabs/postman-collection | Apache-2.0 | JavaScript | Direct dependency candidate |
| openapi-to-postman | https://github.com/postmanlabs/openapi-to-postman | Apache-2.0 | JavaScript | Direct dependency candidate |
| swagger-parser | https://github.com/APIDevTools/swagger-parser | MIT | JavaScript | Direct dependency candidate |
| Schemathesis | https://github.com/schemathesis/schemathesis | MIT | Python | Optional isolated service for OpenAPI case generation |
| Keploy | https://github.com/keploy/keploy | Apache-2.0 | Go | Traffic replay and case generation reference |

Landing direction:

- Keep WeiTesting's current API collection feature as the product surface.
- Add Postman/OpenAPI import-export compatibility instead of embedding another whole API client.
- Use the AI generation flow: document check -> candidate cases -> governance suggestions -> user confirmation -> formal case library.
- Never let AI write directly to the formal case library without an explicit review/apply step.

## License Guardrails

- Safe for direct dependency after normal review: MIT, Apache-2.0 libraries.
- Reference only: GPL/AGPL products, projects with unclear or extra license terms.
- Do not copy product code from MeterSphere, Kiwi TCMS, TestLink, Grafana, or Testopia into WeiTesting.
- It is safe to copy ideas, data-model concepts, and UX patterns, then implement them ourselves in the existing codebase.

## Recommended Next Implementation Slice

1. Dashboard POC:
   - Add `echarts` + `vue-echarts`.
   - Keep grid drag optional; start with widget visibility/order persisted in localStorage or backend workspace config.
   - Replace manual SVG charts in `Overview.vue` only where it clearly reduces code.

2. Asset Center polish:
   - Unify list toolbar actions across case, requirement, and API assets.
   - Add field mapping + validation preview language to import flows.
   - Add saved filters and batch operation affordances.

3. API debugging:
   - Keep current collection detail page.
   - Add a Bruno/Hoppscotch-like left tree + middle request editor + right response/history layout if not already present.
   - Add Postman/OpenAPI compatibility as isolated import/export adapters.

4. AI generation workflow:
   - Keep the review gate.
   - Add visible generation stages and batch accept/reject/edit actions.
   - Record AI decision history for later audit.
