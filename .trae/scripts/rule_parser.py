import re
from pathlib import Path

class RuleParser:
    """Rule文件解析器，提取规则中的结构化信息"""
    def __init__(self, rule_dir: str = "./rules"):
        self.rule_dir = Path(rule_dir)
        self.csv_rules = self.load_csv_rules()
        self.doc_rules = self.load_doc_rules()

    def load_csv_rules(self):
        """加载CSV生成规则"""
        rule_file = self.rule_dir / "api-test-csv-generator.md"
        if not rule_file.exists():
            raise FileNotFoundError(f"CSV规则文件不存在：{rule_file}")
        
        with open(rule_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 解析CSV列名
        csv_columns = self._parse_csv_columns(content)
        # 解析模块编号规则
        module_codes = self._parse_module_codes(content)
        # 解析测试用例类型
        test_types = self._parse_test_types(content)

        return {
            "csv_columns": csv_columns,
            "module_codes": module_codes,
            "test_types": test_types,
            "file_name": "all_api_test_cases.csv",
            "file_path": self.rule_dir.parent / "test_cases"
        }

    def load_doc_rules(self):
        """加载接口文档解析规则"""
        rule_file = self.rule_dir / "generate-api-case.md"
        if not rule_file.exists():
            raise FileNotFoundError(f"文档规则文件不存在：{rule_file}")
        
        with open(rule_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 解析语言识别规则
        lang_detect = self._parse_language_detection(content)
        # 解析框架特征
        framework_features = self._parse_framework_features(content)

        return {
            "language_detection": lang_detect,
            "framework_features": framework_features,
            "search_keywords": self._parse_search_keywords(content)
        }

    def _parse_csv_columns(self, content: str) -> dict:
        """解析CSV列名规则"""
        pattern = r"\| 列名 \| 描述 \| 示例 \|[\s\S]*?\|------\|------\|------\|[\s\S]*?((?:\|.*?\|.*?\|.*?\|\n)+)"
        match = re.search(pattern, content)
        if not match:
            return {}
        
        table_content = match.group(1)
        rows = table_content.strip().split("\n")
        columns = {}
        for row in rows:
            if row.startswith("|"):
                parts = [p.strip() for p in row.split("|") if p.strip()]
                if len(parts) >= 2:
                    columns[parts[0]] = parts[1]
        return columns

    def _parse_module_codes(self, content: str) -> dict:
        """解析模块编号规则"""
        pattern = r"模块编号规则：[\s\S]*?(\| 模块名称 \| 模块编号 \|[\s\S]*?\|------\|------\|[\s\S]*?(?:\|.*?\|.*?\|\n)+)"
        match = re.search(pattern, content)
        if not match:
            return {
                "登录认证模块": "01",
                "用户管理模块": "02",
                "个人信息管理模块": "03",
                "用户注册模块": "04"
            }
        
        table_content = match.group(1)
        rows = table_content.strip().split("\n")
        module_codes = {}
        for row in rows:
            if row.startswith("|") and "|" in row:
                parts = [p.strip() for p in row.split("|") if p.strip()]
                if len(parts) >= 2:
                    module_codes[parts[0]] = parts[1]
        return module_codes

    def _parse_test_types(self, content: str) -> list:
        """解析测试用例类型"""
        pattern = r"测试用例类型[\s\S]*?#### 1. 正向测试用例[\s\S]*?#### 2. 负向测试用例[\s\S]*?#### 3. 边界测试用例"
        if re.search(pattern, content):
            return ["positive", "negative", "boundary"]
        return []

    def _parse_language_detection(self, content: str) -> dict:
        """解析语言识别规则"""
        pattern = r"自动识别策略[\s\S]*?```([\s\S]*?)```"
        match = re.search(pattern, content)
        if not match:
            return {}
        
        lines = match.group(1).strip().split("\n")
        lang_rules = {}
        for line in lines:
            line = line.strip()
            if "->" in line:
                key, value = line.split("->")
                lang_rules[key.strip("- ").strip()] = value.strip()
        return lang_rules

    def _parse_framework_features(self, content: str) -> dict:
        """解析框架特征规则"""
        pattern = r"框架特征识别[\s\S]*?```([\s\S]*?)```"
        match = re.search(pattern, content)
        if not match:
            return {}
        
        lines = match.group(1).strip().split("\n")
        framework_rules = {}
        current_lang = ""
        for line in lines:
            line = line.strip()
            if line.endswith(":") and not line.startswith("-"):
                current_lang = line[:-1]
                framework_rules[current_lang] = []
            elif line.startswith("-") and current_lang:
                framework_rules[current_lang].append(line.strip("- ").strip())
        return framework_rules

    def _parse_search_keywords(self, content: str) -> dict:
        """解析代码搜索关键词"""
        pattern = r"语言特定搜索关键词[\s\S]*?```([\s\S]*?)```"
        match = re.search(pattern, content)
        if not match:
            return {}
        
        lines = match.group(1).strip().split("\n")
        search_rules = {}
        current_lang = ""
        for line in lines:
            line = line.strip()
            if line.endswith(":") and not line.startswith("-"):
                current_lang = line[:-1]
                search_rules[current_lang] = {"控制器": [], "服务/路由": []}
            elif line.startswith("-") and current_lang:
                if "控制器:" in line or "路由:" in line or "服务:" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        key = parts[0].strip("- ").strip()
                        value = parts[1].strip()
                        if key in search_rules[current_lang]:
                            search_rules[current_lang][key].append(value)
                        else:
                            search_rules[current_lang][key] = [value]
        return search_rules