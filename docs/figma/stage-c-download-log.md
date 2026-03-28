# 阶段C执行记录（Baseline PNG 下载）

## 执行目标

- 按 manifest 记录下载 Figma 页面 baseline PNG
- 命名规则：`<page-id>__<node-id>__v<design-version>.png`

## 本次输入

- pageId: `sample-login-page`
- fileKey: `REPLACE_FILE_KEY`
- nodeId: `12:34`
- baselineDir: `ai-project_front_end/tests/ui/baseline/sample-login-page`

## 执行结果

- MCP `get_figma_data` 校验失败：`fileKey` 仅支持字母数字，`REPLACE_FILE_KEY` 为占位值，无法访问 Figma API。
- 已将 `docs/figma/manifest.json` 与 `docs/figma/figma-links.md` 状态更新为 `failed`。

## 可直接重试条件

- 将 `figma-links.md` 和 `manifest.json` 中以下字段替换为真实值：
  - `figmaUrl`
  - `fileKey`（必须字母数字）
  - `nodeId`（格式如 `12:34`）
- 替换后可继续执行下载流程并生成 baseline PNG。
