# 页面：login-page

## 元信息

- bizModule: auth
- routePath: /login
- figma:
  - fileKey: 7gp8uybcxpI1wMH5fVGicg
  - nodeId: 1:2578
- baselineDir: ai-project_front_end/tests/ui/baseline/login-page
- lastSyncAt: 2026-03-26T00:00:00+08:00

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
    figmaNodeId: "1:2578"
    testId: "auth-header"
    baseline: "header__1-2578__v1.png"
    maxDiffRatio: 0.01
  - name: main
    figmaNodeId: "1:2578"
    testId: "auth-main"
    baseline: "main__1-2578__v1.png"
    maxDiffRatio: 0.01
  - name: login-form
    figmaNodeId: "1:2578"
    testId: "auth-login-form"
    baseline: "login-form.png"
    maxDiffRatio: 0.01

masks:
  - testId: "auth-dynamic-time"
  - testId: "auth-user-name"
```

## 全页视觉（P2，可选）

- fullPage:
  - screenshotName: full-page.png

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
