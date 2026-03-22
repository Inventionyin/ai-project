---
alwaysApply: false
---
***

## alwaysApply: false

````
# API接口测试用例CSV生成规则

## 概述
此规则用于根据接口文档自动生成CSV格式的测试用例，这些测试用例将用于Python、pytest、allure接口自动化测试框架。

## 接口文档要求
用户需要提供包含以下信息的接口文档：
- 接口名称和描述
- 请求方法（GET、POST、PUT、DELETE等）
- 请求URL
- 请求参数（包括参数名、类型、是否必填、描述）
- 响应示例
- 权限要求（如有）
- 错误码说明

参考文档格式：@API.md

## CSV测试用例格式标准

### CSV文件结构
生成的CSV文件应包含以下列：

| 列名 | 描述 | 示例 |
|------|------|------|
| test_case_id | 测试用例ID | TC001 |
| feature | 功能模块| 登录认证 |
| title | 测试用例名称 | 用户登录_正常流程 |
| apiMethod | 请求方法 | POST |
| apiUrl | 请求URL | /api/login |
| apiHeaders | 请求头 | {"Content-Type": "application/json"} |
| apiParams | 请求参数 | {"username": "admin", "password": "admin123"} |
| expected_status_code | 期望状态码 | 200 |
| expectedResult | 期望响应 | {"code": 200, "msg": "操作成功"} |
| test_type | 测试类型 | positive/negative/boundary |
| priority | 优先级 | P0/P1/P2 |
| status | 状态 | DRAFT |
| type | 类型| API/UI/MIX |
| preconditions | 前置条件 | `{"dependsOn":["TC00001"],"bind":{"headers":{"Authorization":"Bearer ${accessToken}"}}}` |
| postconditions | 后置条件 | `{"asserts":[{"json":"$.code","op":"==","value":0},{"json":"$.data.accessToken","op":"!=","value":""}],"exports":{"accessToken":{"json":"$.data.accessToken"}}}` |
| tags | 标签 | login,auth,smoke |
### 前置 / 后置条件格式强制规范
#### 前置条件（preconditions）
- 仅允许 JSON 字符串格式，禁止纯文本描述，包含两个核心可选节点：
- dependsOn：数组类型，填写依赖的测试用例 ID，无依赖则为空数组[]
- bind：对象类型，填写需要从依赖用例绑定的参数（如请求头、请求参数），无绑定则为空对象{}
- 无前置依赖 / 绑定：{"dependsOn":[],"bind":{}}
- 有登录依赖：{"dependsOn":["TC001015"],"bind":{"headers":{"Authorization":"Bearer ${accessToken}"}}}
#### 后置条件（postconditions）
- 仅允许 JSON 字符串格式，禁止纯文本描述，包含两个核心可选节点：
- asserts：数组类型，填写响应结果的断言规则，无断言则为空数组[]
- 断言节点格式：{"json":"JSONPath表达式","op":"比较运算符","value":"比较值"}
- 支持运算符：==/!=/>/</>=/<=
- exports：对象类型，填写需要导出的参数（供其他用例绑定使用），无导出则为空对象{}
- 导出节点格式：{"导出参数名":{"json":"JSONPath表达式"}}
- 无断言 / 导出：{"asserts":[],"exports":{}}
- 有断言 + 导出 token：{"asserts":[{"json":"$.code","op":"==","value":0}],"exports":{"accessToken":{"json":"$.data.accessToken"}}}
### 测试用例类型
为每个接口生成以下类型的测试用例：

#### 1. 正向测试用例（Positive）
- 使用有效的必填参数
- 使用有效的可选参数
- 边界值测试（最小值、最大值）

#### 2. 负向测试用例（Negative）
- 缺少必填参数
- 参数类型错误
- 参数值超出范围
- 无效的参数值
- 权限不足测试

#### 3. 边界测试用例（Boundary）
- 参数长度边界测试
- 数值边界测试
- 特殊字符测试

## 生成规则

### 1. 文件命名规则
- **统一文件名**：`api_test_cases_${时间戳}.csv，时间戳格式为YYYYMMDDHHMMSS（如api_test_cases_20251020153028.csv）`
- **存放位置**：`test_cases/api_test_cases_${时间戳}.csv`
- **说明**：所有接口的测试用例统一生成到一个CSV文件中，便于管理和维护

### 2. 测试用例ID规则
- 格式：`TC{模块编号}{接口编号}{用例编号}`
- 示例：`TC001001`（用户模块01，登录接口01，用例01）
- **模块编号规则**：
  - 01: 登录认证模块
  - 02: 用户管理模块  
  - 03: 个人信息管理模块
  - 04: 用户注册模块

### 3. 参数处理规则
- JSON格式的参数使用双引号包围
- 特殊字符需要转义
- 空值用null表示
- 数组用JSON数组格式

### 4. 响应验证规则
- 包含状态码验证
- 包含关键字段验证
- 包含业务逻辑验证

## 使用示例

当用户提供接口文档时，按以下步骤生成CSV测试用例：

1. **解析接口文档**：提取接口基本信息
2. **设计测试场景**：根据参数要求设计正向、负向、边界测试
3. **创建目录结构**：如果test_cases目录不存在，先创建该目录
4. **生成统一CSV文件**：将所有接口的测试用例生成到`test_cases/all_api_test_cases.csv`
5. **验证完整性**：确保覆盖所有重要测试场景

### 生成流程说明
- 所有模块的接口测试用例都写入同一个CSV文件
- 按模块顺序组织测试用例（登录认证→用户管理→个人信息→用户注册）
- 每个模块内按接口顺序排列
- 每个接口内按测试类型排列（positive→negative→boundary）

## Python测试代码集成

生成的CSV文件将配合以下Python测试框架使用：

```# pytest + allure 示例代码结构
import pytest
import allure
import pandas as pd
import json
import time
from api_client import APIClient

# 动态读取test_cases下最新的CSV测试用例
def get_latest_test_case_file():
    import os
    test_dir = 'test_cases'
    files = [f for f in os.listdir(test_dir) if f.startswith('api_test_cases_') and f.endswith('.csv')]
    files.sort(reverse=True)
    return os.path.join(test_dir, files[0]) if files else None

@pytest.fixture
def test_data():
    csv_file = get_latest_test_case_file()
    if not csv_file:
        raise FileNotFoundError("未找到测试用例CSV文件")
    df = pd.read_csv(csv_file)
    # 解析JSON格式的前置/后置条件
    df['preconditions'] = df['preconditions'].apply(lambda x: json.loads(x) if pd.notna(x) else {})
    df['postconditions'] = df['postconditions'].apply(lambda x: json.loads(x) if pd.notna(x) else {})
    return df

@allure.feature("若依系统API测试")
@pytest.mark.parametrize("test_case_data", test_data.iterrows())
def test_api(test_case_data):
    """
    通用API测试方法，根据CSV中的测试用例数据执行测试
    """
    index, test_case = test_case_data
    
    # 根据test_case中的tags字段动态设置allure标签
    allure.dynamic.story(test_case['title'])
    allure.dynamic.title(test_case['title'])
    allure.dynamic.tag(*test_case['tags'].split(','))
    
    # 解析前置条件依赖和绑定参数
    pre_conditions = test_case['preconditions']
    # 处理依赖用例、绑定参数逻辑
    # ...
    
    # 解析后置条件断言和导出参数
    post_conditions = test_case['postconditions']
    # 执行断言、导出参数逻辑
    # ...
    
    # 根据method、url、headers、request_data执行API调用
    # 验证expected_status_code和expectedResult
    pass
```

## 质量标准

生成的CSV测试用例应满足：
- 测试覆盖率 > 90%
- 包含正向、负向、边界测试
- 测试用例可独立执行
- 参数化测试友好
- 支持allure报告生成

## 注意事项

1. **敏感信息处理**：测试数据中的密码等敏感信息使用占位符
2. **环境变量**：URL中的域名部分使用环境变量占位符
3. **依赖关系**：标明测试用例间的依赖关系
4. **数据清理**：标明需要数据清理的测试用例

````
