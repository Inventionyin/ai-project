# 页面：sample-login-page

## 元信息

- bizModule: auth
- routePath: /login
- figma:
  - fileKey: REPLACE_FILE_KEY
  - nodeId: 12:34
- baselineDir: ai-project_front_end/tests/ui/baseline/sample-login-page
- lastSyncAt: 2026-03-25T22:05:00+08:00

## 页面固定字段（P0）

- header:
  - text: AI 测试平台
- subtitle:
  - text: 智能化测试资产管理与执行编排
- tabs:
  - text: 账号登录
  - text: 注册账号
- loginForm:
  - text: 用户名
  - text: 密码
  - text: 登 录

## 关键区域视觉（P1）

```yaml
targets:
  - name: header
    figmaNodeId: "12:34"
    testId: "auth-header"
    baseline: "header__12-34__v20260325.png"
    maxDiffRatio: 0.01
  - name: loginForm
    figmaNodeId: "12:35"
    testId: "auth-login-form"
    baseline: "loginForm__12-35__v20260325.png"
    maxDiffRatio: 0.01
```
