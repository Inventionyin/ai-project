---
name: api-doc-test-generator
description: 根据接口文档生成 CSV 测试用例，或根据后端代码自动生成接口文档。支持多语言项目（Java、Node.js、Python、Go 等）。
alwaysApply: false
---

# API 文档与测试用例生成器

## 功能概述
此技能提供两个核心功能：
1. **从接口文档生成 CSV 测试用例**：用户提供一份接口文档（Markdown 格式，如 @API.md），自动生成符合 api-test-csv-generator 规则的 CSV 测试用例文件。
2. **从代码生成接口文档**：用户指定一个模块（如“用户管理模块”），自动分析项目代码（支持 Spring Boot、Express、FastAPI、Gin 等），生成标准化的接口文档到 `doc/API.md`。

## 触发条件
- **生成测试用例**：当用户说“根据接口文档生成测试用例”、“帮我生成 CSV 测试用例”、“把 API.md 转成测试用例”等。
- **生成接口文档**：当用户说“生成登录模块的接口文档”、“帮我生成 API 文档”、“根据代码生成接口文档”等。

## 工作流程

### 模式一：接口文档 → CSV 测试用例
1. **定位接口文档**：优先使用用户提供的文件路径，否则搜索项目中的 `API.md` 或类似文档。
2. **解析文档**：提取接口名称、URL、方法、参数、响应示例、权限等。
3. **生成测试用例**：根据规则生成正向、负向、边界用例，填充 CSV 字段（test_case_id, feature, title, apiMethod, apiUrl, apiParams, expected_status_code, expectedResult, test_type, priority, status, type, preconditions, postconditions, tags）。
4. **写入文件**：保存到 `test_cases/api_test_cases_<timestamp>.csv`，并告知用户。

**调用的脚本**：`scripts/generate_csv_from_api_doc.py`

### 模式二：代码 → 接口文档
1. **识别项目语言和框架**：自动检测项目根目录下的 `package.json`、`pom.xml`、`requirements.txt` 等，判断语言和框架。
2. **定位模块代码**：根据用户指定的模块名（如“用户管理”），搜索对应的控制器/路由文件（如 `UserController.java`、`userRoutes.js`）。
3. **解析代码**：提取路由、参数、验证规则、权限注解、响应模型等。
4. **生成文档**：按统一模板生成 Markdown 文档，包含接口说明、参数表、请求示例、响应示例、错误码表。
5. **写入文件**：保存到 `doc/API.md`，支持增量更新（仅更新指定模块）。

**调用的脚本**：`scripts/generate_api_doc_from_code.py`

## 脚本调用说明
AI 在执行任务时，会根据模式选择对应的脚本，并传入必要参数。脚本返回结构化数据后，AI 可进一步处理或直接输出结果。

### 脚本 1: generate_csv_from_api_doc.py
**输入**：接口文档路径（如 `API.md`）  
**输出**：CSV 文件路径（如 `test_cases/api_test_cases_20250322143000.csv`）  
**用法**：
```bash
python scripts/generate_csv_from_api_doc.py --doc API.md --output test_cases/
python scripts/generate_api_doc_from_code.py --module "用户管理" --project-root . --output doc/API.md
