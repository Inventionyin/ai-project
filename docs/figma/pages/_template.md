# 页面：REPLACE_PAGE_ID

## 元信息

- bizModule: REPLACE_BIZ_MODULE
- routePath: REPLACE_ROUTE_PATH
- figma:
  - fileKey: REPLACE_FILE_KEY
  - nodeId: REPLACE_NODE_ID
- baselineDir: ai-project_front_end/tests/ui/baseline/REPLACE_PAGE_ID
- lastSyncAt: 2026-03-25T10:00:00+08:00

## 页面固定字段（P0）

- title:
  - text: REPLACE_TITLE_TEXT
  - selector: REPLACE_TITLE_SELECTOR
- subtitle:
  - text: REPLACE_SUBTITLE_TEXT
  - selector: REPLACE_SUBTITLE_SELECTOR
- primaryButton:
  - text: REPLACE_PRIMARY_BUTTON_TEXT
  - selector: REPLACE_PRIMARY_BUTTON_SELECTOR
- navItems:
  - text: REPLACE_NAV_TEXT
  - selector: REPLACE_NAV_SELECTOR

## 关键区域视觉（P1）

```yaml
targets:
  - name: header
    figmaNodeId: "REPLACE_NODE_ID"
    testId: "REPLACE_BIZ_MODULE-header"
    baseline: "header__REPLACE_NODE_ID__vREPLACE_DESIGN_VERSION.png"
    maxDiffRatio: 0.01
  - name: main
    figmaNodeId: "REPLACE_NODE_ID"
    testId: "REPLACE_BIZ_MODULE-main"
    baseline: "main__REPLACE_NODE_ID__vREPLACE_DESIGN_VERSION.png"
    maxDiffRatio: 0.01

masks:
  - testId: "REPLACE_BIZ_MODULE-dynamic-time"
  - testId: "REPLACE_BIZ_MODULE-user-name"
```

## 全页视觉（P2，可选）

- fullPage:
  - screenshotName: REPLACE_PAGE_ID-fullpage.png

## 断言策略

- locale: zh-CN
- textMatch: exact
- retry:
  - timeoutMs: 8000
  - intervalMs: 200

## 已知动态区（忽略）

- timestamp
- avatar
- random-banner

## 验收标准

- P0 通过率 = 100%
- P1 关键区域通过率 >= 95%
- P2 仅做预警，不阻断
