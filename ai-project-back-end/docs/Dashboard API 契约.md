## Dashboard API 契约

> 

PRD 第 15 节未为仪表盘单独列契约，以下依据 PRD 数据模型 + 统一规范推导

------

### 1. 今日执行统计卡片

```
GET /api/projects/{projectId}/dashboard/summary
```

**用途：** 4 张 StatCard 的数据源

**Query 参数：**

| 参数   | 说明                              |
| ------ | --------------------------------- |
| `date` | 日期，默认当天，格式 `YYYY-MM-DD` |

**Response：**

```json
{
  "code": 0,
  "data": {
    "date": "2024-03-14",
    "totalRuns": 4,
    "passedRuns": 2,
    "failedRuns": 1,
    "runningRuns": 1,
    "canceledRuns": 0,
    "passRate": 66.7
  }
}
```

------

### 2. 近 7 天趋势折线

```
GET /api/projects/{projectId}/dashboard/trend
```

**用途：** 折线图数据源（通过率 + 失败数按日聚合）

**Query 参数：**

| 参数   | 类型 | 默认 | 说明             |
| ------ | ---- | ---- | ---------------- |
| `days` | int  | `7`  | 支持 7 / 14 / 30 |

**Response：**

```json
{
  "code": 0,
  "data": {
    "days": 7,
    "items": [
      { "date": "03-08", "passRate": 88.5, "failCount": 14, "totalRuns": 12 },
      { "date": "03-09", "passRate": 91.2, "failCount": 10, "totalRuns": 11 },
      { "date": "03-14", "passRate": 92.8, "failCount": 8,  "totalRuns": 15 }
    ]
  }
}
```

------

### 3. 失败 Top 10

```
GET /api/projects/{projectId}/dashboard/failure-top
```

**用途：** 失败榜单，支持"用例维度 / 套件维度"切换

**Query 参数：**

| 参数        | 类型   | 默认       | 说明                 |
| ----------- | ------ | ---------- | -------------------- |
| `dimension` | string | `testcase` | `testcase` | `suite` |
| `days`      | int    | `7`        | 统计时间窗口         |
| `limit`     | int    | `10`       | 最多返回条数         |

**Response（testcase 维度）：**

```json
{
  "code": 0,
  "data": {
    "dimension": "testcase",
    "items": [
      {
        "id": "tc3",
        "name": "支付-微信支付回调验签",
        "failCount": 8,
        "totalRuns": 10,
        "flake": false,
        "projectName": "支付服务",
        "suiteNames": ["支付冒烟套件"]
      }
    ]
  }
}
```

**Response（suite 维度）：**

```json
{
  "code": 0,
  "data": {
    "dimension": "suite",
    "items": [
      {
        "id": "s2",
        "name": "订单全量回归",
        "failCount": 11,
        "totalRuns": 5,
        "lastRunAt": "2024-03-14T12:18:45Z"
      }
    ]
  }
}
```

------

### 4. 质量门禁状态（V1.1）

```
GET /api/projects/{projectId}/dashboard/quality-gate
```

**用途：** 质量门禁卡片，展示最近一次门禁检测结果

**Response：**

```json
{
  "code": 0,
  "data": {
    "overall": "PARTIAL_FAIL",
    "lastCheckedAt": "2024-03-14T14:30:00Z",
    "linkedRunId": "r001",
    "gates": [
      { "name": "整体通过率",    "threshold": "≥90%",    "current": "92.8%", "passed": true  },
      { "name": "P0 用例全通过", "threshold": "100%",    "current": "100%",  "passed": true  },
      { "name": "关键路径通过率","threshold": "≥95%",    "current": "91.2%", "passed": false },
      { "name": "平均响应时间",  "threshold": "≤2000ms", "current": "1280ms","passed": true  }
    ]
  }
}
```

> 

```
overall` 枚举：`PASSED` / `PARTIAL_FAIL` / `FAILED` / `UNKNOWN
```

------

### 5. 最近运行列表（右下卡片）

复用 PRD 已有契约：

```
GET /api/runs?projectId={projectId}&page=1&pageSize=5
```

**Response（节选）：**

```json
{
  "code": 0,
  "data": {
    "page": 1, "pageSize": 5, "total": 22,
    "items": [
      {
        "id": "r001",
        "shortId": "R-001",
        "status": "PASSED",
        "suiteName": "支付冒烟套件",
        "envName": "staging",
        "passRate": 100,
        "startAt": "2024-03-14T14:30:00Z"
      }
    ]
  }
}
```

------

### 6. 进行中 Run 实时状态轮询

复用 PRD 已有契约：

```
GET /api/runs/{runId}
```

> 

PRD 14.3 要求进行中的 Run 每 **5s 轮询**一次，或使用 SSE：

> 

> ```
> GET /
> ```

api/runs/{runId}/events （text/event-stream）

> ```
> 
> ```

> 

事件类型：`run_status`（状态变更）、`case_status`（用例状态）

------

## 汇总表

| 卡片 / 区块          | API                                                    | 是否 PRD 原文          |
| -------------------- | ------------------------------------------------------ | ---------------------- |
| 今日执行 4 卡片      | `GET /dashboard/summary?date=`                         | ❌ 推导（原文无）       |
| 近 7 天趋势折线      | `GET /dashboard/trend?days=7`                          | ❌ 推导（原文无）       |
| 失败 Top10（双维度） | `GET /dashboard/failure-top?dimension=testcase&days=7` | ❌ 推导（原文无）       |
| 质量门禁状态         | `GET /dashboard/quality-gate`                          | ❌ 推导（V1.1）         |
| 最近运行列表         | `GET /api/runs?projectId=&pageSize=5`                  | ✅ PRD 15.6 原文        |
| 进行中实时刷新       | `GET /api/runs/{runId}` 轮询 / SSE                     | ✅ PRD 15.6 + 16 节原文 |

------

**结论：** PRD 第 15 节对仪表盘**没有单独的契约章节**，但 14.3 节明确了所有需要展示的数据字段，结合数据库表结构（`runs`、`case_runs`）完全可以后端聚合实现。建议将前 4 个接口归入一个 `/api/projects/{projectId}/dashboard/*` 路由组，由后端做聚合查询，避免前端发多次独立请求。