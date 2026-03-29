# 接口集合导入优化：异步解析与 Diff 预览技术方案

## 1. 目标与背景
当前系统在 `API Collections` 模块支持直接将 Postman/Swagger JSON 导入入库。但面对非结构化的 Markdown 接口文档，直接同步请求 LLM 解析存在严重的超时风险，且静默覆盖入库容易造成测试数据丢失。
本方案旨在引入**异步任务机制**、**Docling+LLM切片提取**与**前端 Diff 确认**，实现高可用、防丢失的导入体验。

## 2. 核心架构设计

### 2.1 任务模型复用与扩展
参考项目中现有的 `AiImportJob` 设计，我们在 API 导入中复用或参考其“创建 Job -> 上传文件 -> 后台解析 -> 轮询结果 -> 确认入库”的异步状态机模式。

**状态流转**：
`PENDING` -> `UPLOADED` -> `PARSING` -> `PARSED_PREVIEW` -> `COMMITTED` / `FAILED`

### 2.2 数据模型 (Schema)
定义中间态数据结构 `ApiImportPreviewResult`，用于前后端传递解析结果及 Diff 对比：

```json
{
  "collectionName": "用户中心 API",
  "groups": [
    {
      "name": "登录模块",
      "requests": [
        {
          "method": "POST",
          "url": "/api/v1/login",
          "name": "用户登录",
          "headers": {"Content-Type": "application/json"},
          "body": "...",
          "diffStatus": "new" // enum: new, updated, unchanged
        }
      ]
    }
  ]
}
```

## 3. 后端实现路径 (FastAPI + SQLAlchemy)

### 3.1 接口契约
1. **创建导入任务**: `POST /api/collections/import-jobs`
   - 入参：`projectId`
   - 返回：`jobId`
2. **上传文档**: `POST /api/collections/import-jobs/{jobId}/file`
   - 行为：接收文件，保存至本地或 OSS，状态置为 `UPLOADED`，并触发 `asyncio.create_task` 或 `BackgroundTasks` 开始解析。
3. **轮询状态**: `GET /api/collections/import-jobs/{jobId}`
   - 返回：当前状态，如果到达 `PARSED_PREVIEW` 则附带 `ApiImportPreviewResult`。
4. **确认入库**: `POST /api/collections/import-jobs/{jobId}/commit`
   - 入参：用户在前端勾选确认的 Request 列表及覆盖策略。
   - 行为：执行真实数据库的 CRUD，将 `Collection`, `Group`, `Request` 写入 `api_collections` 等表。

### 3.2 解析引擎设计 (Docling + LLM)
在后台解析任务中：
1. **AST 切片**：使用现有的 `Docling` 引擎，将 Markdown 解析为树结构，根据 `H2/H3` 切割为多个 Chunk。
2. **LLM 提取**：利用 `LLMProvider`，传入 `Chunk`，System Prompt 要求返回 JSON（包含 `name, method, url, body` 等）。开启大模型的 `json_object` 模式。
3. **Diff 对比**：将提取结果与数据库中该项目/该集合下的现有接口按 `(method, url)` 进行比对，标记出 `new` 和 `updated`。

## 4. 前端实现路径 (Vue 3 + TailwindCSS)

### 4.1 组件设计
1. **ImportCollectionModal.vue** (主弹窗)
   - 维护向导式步骤：步骤 1 (上传) -> 步骤 2 (解析中/轮询) -> 步骤 3 (数据预览与 Diff)。
2. **UploadStep.vue**
   - 封装文件拖拽/选择，调用上传 API。
3. **DiffPreviewStep.vue**
   - 接收 `PARSED_PREVIEW` 数据。
   - 使用树形组件展示，左侧显示接口名，右侧显示 Badge（🟢新增、🟡修改）。
   - 提供 Checkbox 供用户选择是否要导入/覆盖该接口。

### 4.2 交互链路
- 用户点击列表右上角“导入” -> 弹出 `ImportCollectionModal`。
- 上传 `API.md` -> 界面进入 loading 状态（轮询 GET 接口）。
- 解析完成 -> 展示树形 Diff 预览。
- 用户取消勾选不需要的接口 -> 点击“确认导入”。
- 调用 commit 接口 -> 关闭弹窗 -> 刷新集合列表。

## 5. 风险控制与兜底
- **超大文件处理**：文件大小限制 10MB；Docling 切片可控制单次喂给 LLM 的 token 数不超过 8k。
- **解析失败兜底**：如果某一切片 LLM 返回 JSON 破损，记录在 Job 的 `warnings` 字段中，前端予以展示，不阻断其他切片的正常展示。
- **幂等与重复提交**：Commit 接口校验 Job 状态，只有 `PARSED_PREVIEW` 允许提交，提交后置为 `COMMITTED`。