# Figma 连接索引

用于维护 Figma 页面连接、路由映射、同步状态与责任人。  
一行代表一个可验证页面。

## 字段说明

| 字段 | 含义 | 示例 |
|---|---|---|
| id | 页面唯一标识（建议 kebab-case） | login-page |
| bizModule | 业务模块 | auth |
| figmaUrl | Figma 原型链接 | https://www.figma.com/file/xxx |
| fileKey | 从 Figma 链接解析出的 fileKey | xxx |
| nodeId | Figma 节点 ID（可选） | 12:34 |
| routePath | 前端路由路径 | /login |
| envUrl | 验证环境完整地址 | http://localhost:5173/login |
| owner | 负责人 | zhangsan |
| status | 同步状态 | pending_sync |
| lastSyncAt | 最近同步时间（ISO8601） | 2026-03-25T10:00:00+08:00 |

## 状态枚举

- pending_sync
- synced
- script_generated
- verified
- failed

## 索引表

| id | bizModule | figmaUrl | fileKey | nodeId | routePath | envUrl | owner | status | lastSyncAt |
|---|---|---|---|---|---|---|---|---|---|
| sample-login-page | auth | https://www.figma.com/file/REPLACE_FILE_KEY/REPLACE_PAGE?node-id=12-34 | REPLACE_FILE_KEY | 12:34 | /login | http://localhost:5173/login | REPLACE_OWNER | failed | 2026-03-25T21:41:00+08:00 |
