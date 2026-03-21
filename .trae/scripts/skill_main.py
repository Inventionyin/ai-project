import os
import sys
import json
import pandas as pd
from pathlib import Path
from rule_parser import RuleParser
from api_doc_parser import APIDocParser

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class APITestCaseGenerator:
    """API测试用例生成器（Skill核心逻辑）"""
    def __init__(self):
        # 初始化解析器
        self.rule_parser = RuleParser()
        self.api_parser = APIDocParser(self.rule_parser)
        # 初始化输出目录
        self.output_dir = self.rule_parser.csv_rules["file_path"]
        self.output_dir.mkdir(exist_ok=True)
        self.output_file = self.output_dir / self.rule_parser.csv_rules["file_name"]
        # 初始化用例计数器
        self.case_counter = {"positive": 1, "negative": 1, "boundary": 1}

    def generate_test_cases(self, module_name: str, language: str = "auto") -> str:
        """
        生成指定模块的测试用例
        :param module_name: 模块名称（如：登录认证模块）
        :param language: 语言框架（auto/Java Spring Boot/Python FastAPI等）
        :return: 生成的CSV文件路径
        """
        # 1. 获取模块接口列表
        api_list = self.api_parser.get_api_list(module_name)
        # 2. 获取模块编号
        module_code = self.rule_parser.csv_rules["module_codes"].get(module_name, "99")
        # 3. 获取CSV列名
        csv_columns = list(self.rule_parser.csv_rules["csv_columns"].keys())
        # 4. 生成测试用例
        all_test_cases = []
        for api_idx, api in enumerate(api_list, 1):
            api_code = f"{api_idx:02d}"  # 接口编号（两位）
            # 生成正向测试用例
            positive_cases = self._generate_positive_cases(module_code, api_code, api, module_name)
            all_test_cases.extend(positive_cases)
            # 生成负向测试用例
            negative_cases = self._generate_negative_cases(module_code, api_code, api, module_name)
            all_test_cases.extend(negative_cases)
            # 生成边界测试用例
            boundary_cases = self._generate_boundary_cases(module_code, api_code, api, module_name)
            all_test_cases.extend(boundary_cases)
        
        # 5. 写入CSV文件
        self._write_to_csv(all_test_cases, csv_columns)
        
        return str(self.output_file)

    def _generate_positive_cases(self, module_code: str, api_code: str, api: dict, module_name: str) -> list:
        """生成正向测试用例"""
        cases = []
        # 基础用例
        case_id = f"TC{module_code}{api_code}{self.case_counter['positive']:02d}"
        self.case_counter["positive"] += 1
        
        # 构造请求参数（有效参数）
        request_data = {}
        for param in api["params"]:
            if param["type"] == "string":
                request_data[param["name"]] = "test_" + param["name"]
            elif param["type"] == "int":
                request_data[param["name"]] = 100
            else:
                request_data[param["name"]] = None if "default" not in param else param["default"]
        
        case = {
            "test_case_id": case_id,
            "test_case_name": f"{api['api_name']}_正向_正常参数",
            "api_name": api["api_name"],
            "method": api["method"],
            "url": api["url"],
            "headers": json.dumps({"Content-Type": "application/json"}, ensure_ascii=False),
            "request_data": json.dumps(request_data, ensure_ascii=False),
            "expected_status_code": 200,
            "expected_response": api["response_example"],
            "test_type": "positive",
            "priority": "high",
            "description": f"验证{api['api_name']}正常功能（{module_name}）",
            "preconditions": "前置条件：" + ("用户已登录" if api["permission"] != "无需权限" else "无"),
            "postconditions": "后置条件：返回成功响应",
            "tags": f"{module_name.lower().replace('模块', '')},{api['api_name'].lower().replace(' ', '')},smoke"
        }
        cases.append(case)
        return cases

    def _generate_negative_cases(self, module_code: str, api_code: str, api: dict, module_name: str) -> list:
        """生成负向测试用例"""
        cases = []
        # 1. 缺少必填参数
        required_params = [p for p in api["params"] if p.get("required", False)]
        if required_params:
            param = required_params[0]
            case_id = f"TC{module_code}{api_code}{self.case_counter['negative']:02d}"
            self.case_counter["negative"] += 1
            
            # 构造请求参数（缺少必填参数）
            request_data = {}
            for p in api["params"]:
                if p["name"] != param["name"]:
                    request_data[p["name"]] = "test_" + p["name"] if p["type"] == "string" else 100
            
            # 构造预期响应
            error_code = api["error_codes"][0]["code"] if api["error_codes"] else 400
            expected_response = json.dumps({
                "code": error_code,
                "msg": f"缺少必填参数：{param['name']}"
            }, ensure_ascii=False)
            
            case = {
                "test_case_id": case_id,
                "test_case_name": f"{api['api_name']}_负向_缺少{param['name']}",
                "api_name": api["api_name"],
                "method": api["method"],
                "url": api["url"],
                "headers": json.dumps({"Content-Type": "application/json"}, ensure_ascii=False),
                "request_data": json.dumps(request_data, ensure_ascii=False),
                "expected_status_code": 400,
                "expected_response": expected_response,
                "test_type": "negative",
                "priority": "medium",
                "description": f"验证{api['api_name']}缺少必填参数{param['name']}的场景（{module_name}）",
                "preconditions": "无",
                "postconditions": "返回参数错误响应",
                "tags": f"{module_name.lower().replace('模块', '')},{api['api_name'].lower().replace(' ', '')},negative"
            }
            cases.append(case)
        
        # 2. 参数类型错误
        if api["params"]:
            param = api["params"][0]
            case_id = f"TC{module_code}{api_code}{self.case_counter['negative']:02d}"
            self.case_counter["negative"] += 1
            
            # 构造请求参数（类型错误）
            request_data = {}
            for p in api["params"]:
                if p["name"] == param["name"]:
                    # 类型错误值
                    if p["type"] == "int":
                        request_data[p["name"]] = "非数字字符串"
                    else:
                        request_data[p["name"]] = 999
                else:
                    request_data[p["name"]] = "test_" + p["name"] if p["type"] == "string" else 100
            
            # 构造预期响应
            error_code = api["error_codes"][1]["code"] if len(api["error_codes"]) > 1 else 400
            expected_response = json.dumps({
                "code": error_code,
                "msg": f"参数{param['name']}类型错误，预期{param['type']}"
            }, ensure_ascii=False)
            
            case = {
                "test_case_id": case_id,
                "test_case_name": f"{api['api_name']}_负向_{param['name']}类型错误",
                "api_name": api["api_name"],
                "method": api["method"],
                "url": api["url"],
                "headers": json.dumps({"Content-Type": "application/json"}, ensure_ascii=False),
                "request_data": json.dumps(request_data, ensure_ascii=False),
                "expected_status_code": 400,
                "expected_response": expected_response,
                "test_type": "negative",
                "priority": "medium",
                "description": f"验证{api['api_name']}参数{param['name']}类型错误的场景（{module_name}）",
                "preconditions": "无",
                "postconditions": "返回参数错误响应",
                "tags": f"{module_name.lower().replace('模块', '')},{api['api_name'].lower().replace(' ', '')},negative"
            }
            cases.append(case)
        
        return cases

    def _generate_boundary_cases(self, module_code: str, api_code: str, api: dict, module_name: str) -> list:
        """生成边界测试用例"""
        cases = []
        # 字符串长度边界
        string_params = [p for p in api["params"] if p["type"] == "string"]
        if string_params:
            param = string_params[0]
            case_id = f"TC{module_code}{api_code}{self.case_counter['boundary']:02d}"
            self.case_counter["boundary"] += 1
            
            # 构造请求参数（超长字符串）
            request_data = {}
            for p in api["params"]:
                if p["name"] == param["name"]:
                    request_data[p["name"]] = "a" * 1000  # 超长字符串
                else:
                    request_data[p["name"]] = "test_" + p["name"] if p["type"] == "string" else 100
            
            # 构造预期响应
            expected_response = json.dumps({
                "code": 30001,
                "msg": f"参数{param['name']}长度超出限制"
            }, ensure_ascii=False)
            
            case = {
                "test_case_id": case_id,
                "test_case_name": f"{api['api_name']}_边界_{param['name']}超长",
                "api_name": api["api_name"],
                "method": api["method"],
                "url": api["url"],
                "headers": json.dumps({"Content-Type": "application/json"}, ensure_ascii=False),
                "request_data": json.dumps(request_data, ensure_ascii=False),
                "expected_status_code": 400,
                "expected_response": expected_response,
                "test_type": "boundary",
                "priority": "medium",
                "description": f"验证{api['api_name']}参数{param['name']}长度超出限制的场景（{module_name}）",
                "preconditions": "无",
                "postconditions": "返回参数错误响应",
                "tags": f"{module_name.lower().replace('模块', '')},{api['api_name'].lower().replace(' ', '')},boundary"
            }
            cases.append(case)
        
        # 数值边界
        int_params = [p for p in api["params"] if p["type"] == "int"]
        if int_params:
            param = int_params[0]
            case_id = f"TC{module_code}{api_code}{self.case_counter['boundary']:02d}"
            self.case_counter["boundary"] += 1
            
            # 构造请求参数（超大数值）
            request_data = {}
            for p in api["params"]:
                if p["name"] == param["name"]:
                    request_data[p["name"]] = 999999999  # 超大数值
                else:
                    request_data[p["name"]] = "test_" + p["name"] if p["type"] == "string" else 100
            
            # 构造预期响应
            expected_response = json.dumps({
                "code": 30002,
                "msg": f"参数{param['name']}数值超出限制"
            }, ensure_ascii=False)
            
            case = {
                "test_case_id": case_id,
                "test_case_name": f"{api['api_name']}_边界_{param['name']}超大值",
                "api_name": api["api_name"],
                "method": api["method"],
                "url": api["url"],
                "headers": json.dumps({"Content-Type": "application/json"}, ensure_ascii=False),
                "request_data": json.dumps(request_data, ensure_ascii=False),
                "expected_status_code": 400,
                "expected_response": expected_response,
                "test_type": "boundary",
                "priority": "medium",
                "description": f"验证{api['api_name']}参数{param['name']}数值超出限制的场景（{module_name}）",
                "preconditions": "无",
                "postconditions": "返回参数错误响应",
                "tags": f"{module_name.lower().replace('模块', '')},{api['api_name'].lower().replace(' ', '')},boundary"
            }
            cases.append(case)
        
        return cases

    def _write_to_csv(self, test_cases: list, csv_columns: list):
        """写入CSV文件"""
        df = pd.DataFrame(test_cases, columns=csv_columns)
        # 追加模式，首次写入表头
        write_header = not self.output_file.exists()
        df.to_csv(
            self.output_file,
            mode="a",
            index=False,
            header=write_header,
            encoding="utf-8-sig"  # 支持中文
        )

def main():
    """Skill执行入口"""
    import argparse
    parser = argparse.ArgumentParser(description="API测试用例生成Skill")
    parser.add_argument("--module", required=True, help="模块名称（如：登录认证模块）")
    parser.add_argument("--language", default="auto", help="语言框架（如：Java Spring Boot）")
    args = parser.parse_args()

    try:
        generator = APITestCaseGenerator()
        csv_path = generator.generate_test_cases(args.module, args.language)
        print(f"✅ 测试用例生成成功！文件路径：{csv_path}")
    except Exception as e:
        print(f"❌ 生成失败：{str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()