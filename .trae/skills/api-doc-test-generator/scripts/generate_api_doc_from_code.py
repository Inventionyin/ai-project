#!/usr/bin/env python3
"""
根据代码生成接口文档
"""

import argparse
import os
import json
from pathlib import Path

def detect_language_framework(project_root):
    """检测项目语言和框架"""
    if (project_root / 'pom.xml').exists():
        return 'java', 'spring-boot'
    elif (project_root / 'package.json').exists():
        # 进一步检测框架
        return 'nodejs', 'express'
    elif (project_root / 'requirements.txt').exists():
        return 'python', 'fastapi'
    elif (project_root / 'go.mod').exists():
        return 'go', 'gin'
    else:
        return 'unknown', 'unknown'

def find_controller_files(project_root, module_name, language, framework):
    """根据模块名查找控制器文件"""
    # 根据语言和框架，使用不同的搜索模式
    if language == 'java' and framework == 'spring-boot':
        # 搜索 *Controller.java，名称包含 module_name
        pattern = f"**/*{module_name}*Controller.java"
        return list(project_root.glob(pattern))
    elif language == 'nodejs':
        # 搜索 routes 或 controllers 目录
        pass
    # 其他语言类似...
    return []

def parse_java_controller(file_path):
    """解析 Java Spring Boot 控制器，提取接口信息"""
    # 这里简化处理，实际需要解析 AST
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # 使用正则提取 @RequestMapping, @GetMapping 等
    # 返回接口列表
    pass

def generate_markdown_doc(apis, module_name):
    """生成 Markdown 格式的接口文档"""
    doc = f"# {module_name} 模块接口文档\n\n"
    for api in apis:
        doc += f"## {api['name']}\n\n"
        doc += f"**接口描述：** {api.get('description', '')}\n\n"
        doc += f"**请求 URL：** `{api['method']} {api['url']}`\n\n"
        doc += "**请求参数：**\n"
        doc += "| 参数名 | 类型 | 位置 | 必填 | 描述 |\n"
        doc += "|--------|------|------|------|------|\n"
        for param in api.get('params', []):
            doc += f"| {param['name']} | {param['type']} | {param['in']} | {param['required']} | {param['description']} |\n"
        doc += "\n**响应示例：**\n"
        doc += f"```json\n{json.dumps(api.get('response_example', {}), indent=2, ensure_ascii=False)}\n```\n\n"
    return doc

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--module', required=True, help='模块名称')
    parser.add_argument('--project-root', default='.', help='项目根目录')
    parser.add_argument('--output', default='doc/API.md', help='输出文件路径')
    args = parser.parse_args()

    project_root = Path(args.project_root)
    language, framework = detect_language_framework(project_root)
    controller_files = find_controller_files(project_root, args.module, language, framework)

    all_apis = []
    for file in controller_files:
        apis = parse_java_controller(file)  # 根据语言选择解析器
        all_apis.extend(apis)

    doc_content = generate_markdown_doc(all_apis, args.module)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(doc_content)

    print(f"文档已生成: {output_path}")

if __name__ == '__main__':
    main()