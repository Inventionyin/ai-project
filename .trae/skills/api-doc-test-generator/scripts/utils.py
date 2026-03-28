#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用工具函数
供 api-doc-test-generator skill 的各个脚本使用
"""

import json
import re
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def read_json_file(file_path: Union[str, Path]) -> Optional[Dict]:
    """
    读取 JSON 文件并返回字典，如果文件不存在或格式错误返回 None
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"读取 JSON 文件失败: {e}", file=sys.stderr)
        return None


def write_json_file(data: Dict, file_path: Union[str, Path], indent: int = 2) -> bool:
    """
    将字典写入 JSON 文件，成功返回 True，失败返回 False
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        return True
    except Exception as e:
        print(f"写入 JSON 文件失败: {e}", file=sys.stderr)
        return False


def read_markdown_file(file_path: Union[str, Path]) -> Optional[str]:
    """
    读取 Markdown 文件内容，返回字符串，失败返回 None
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError as e:
        print(f"读取 Markdown 文件失败: {e}", file=sys.stderr)
        return None


def write_text_file(content: str, file_path: Union[str, Path]) -> bool:
    """
    将文本内容写入文件，成功返回 True
    """
    try:
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"写入文本文件失败: {e}", file=sys.stderr)
        return False


def get_timestamp(format_str: str = "%Y%m%d%H%M%S") -> str:
    """
    返回当前时间戳字符串，默认为 YYYYMMDDHHMMSS
    """
    return datetime.now().strftime(format_str)


def replace_variables(template: str, variables: Dict[str, str]) -> str:
    """
    将模板字符串中的 ${变量名} 替换为 variables 中对应的值
    支持嵌套变量（变量值中还可包含变量）
    注意：不会循环替换，只做一轮替换
    """
    if not variables:
        return template

    def replacer(match):
        var_name = match.group(1)
        return variables.get(var_name, match.group(0))  # 未找到则保留原样

    pattern = re.compile(r'\$\{([^}]+)\}')
    return pattern.sub(replacer, template)


def replace_variables_recursive(obj: Any, variables: Dict[str, str]) -> Any:
    """
    递归替换对象（字符串、字典、列表）中的 ${var} 占位符
    """
    if isinstance(obj, str):
        return replace_variables(obj, variables)
    elif isinstance(obj, dict):
        return {k: replace_variables_recursive(v, variables) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_variables_recursive(item, variables) for item in obj]
    else:
        return obj


def extract_by_jsonpath(data: Dict, jsonpath_expr: str) -> Any:
    """
    根据简单的 JSONPath 表达式从字典中提取值
    支持格式：
      - $.key           -> 获取顶层 key
      - $.key.subkey    -> 获取嵌套 key
      - $.list[0]       -> 获取列表索引（暂不支持）
      - $.list[*].key   -> 获取列表中所有对象的 key（暂不支持）
    本函数为简化版本，仅支持点号路径，不支持数组索引。
    若需要完整支持，可安装 jsonpath-ng 库并使用其功能。
    """
    if not jsonpath_expr.startswith('$.'):
        return None
    path = jsonpath_expr[2:]  # 去掉 $.
    parts = path.split('.')
    value = data
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
            if value is None:
                return None
        else:
            return None
    return value


def parse_json_string(s: str) -> Optional[Any]:
    """
    安全解析 JSON 字符串，失败返回 None
    """
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return None


def ensure_directory(path: Union[str, Path]) -> None:
    """
    确保目录存在，如果不存在则创建
    """
    Path(path).mkdir(parents=True, exist_ok=True)


def get_project_root(start_path: Optional[Union[str, Path]] = None) -> Path:
    """
    获取项目根目录（包含 .git 或 pom.xml 等标识文件）
    """
    start = Path(start_path).resolve() if start_path else Path.cwd()
    for parent in [start] + list(start.parents):
        if (parent / '.git').exists() or (parent / 'pom.xml').exists() or (parent / 'package.json').exists():
            return parent
    return start


def detect_language_and_framework(project_root: Path) -> tuple:
    """
    检测项目使用的语言和主要框架
    返回 (language, framework)
    """
    # Java
    if (project_root / 'pom.xml').exists():
        # 进一步检查框架（简单判断）
        if (project_root / 'src/main/java').exists():
            return 'java', 'spring-boot'
    if (project_root / 'build.gradle').exists():
        return 'java', 'spring-boot'

    # Node.js
    if (project_root / 'package.json').exists():
        # 读取 package.json 尝试判断框架
        pkg = read_json_file(project_root / 'package.json')
        if pkg:
            deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
            if 'express' in deps:
                return 'nodejs', 'express'
            if '@nestjs/core' in deps:
                return 'nodejs', 'nestjs'
            if 'fastify' in deps:
                return 'nodejs', 'fastify'
            if 'koa' in deps:
                return 'nodejs', 'koa'
        return 'nodejs', 'unknown'

    # Python
    if (project_root / 'requirements.txt').exists() or (project_root / 'pyproject.toml').exists():
        # 尝试检测框架
        if (project_root / 'manage.py').exists():
            return 'python', 'django'
        if (project_root / 'app.py').exists() and 'fastapi' in open(project_root / 'app.py').read():
            return 'python', 'fastapi'
        return 'python', 'flask'  # 默认猜测

    # Go
    if (project_root / 'go.mod').exists():
        return 'go', 'gin'  # 默认猜测

    # C#
    if (project_root / '*.csproj').exists():
        return 'csharp', 'aspnetcore'

    return 'unknown', 'unknown'


def log_info(msg: str) -> None:
    """打印信息日志（带时间戳）"""
    print(f"[{get_timestamp('%Y-%m-%d %H:%M:%S')}] INFO: {msg}")


def log_error(msg: str) -> None:
    """打印错误日志"""
    print(f"[{get_timestamp('%Y-%m-%d %H:%M:%S')}] ERROR: {msg}", file=sys.stderr)