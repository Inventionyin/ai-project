

### 2. scripts/generate_csv_from_api_doc.py（简化示例）


#!/usr/bin/env python3
"""
根据接口文档生成 CSV 测试用例
"""

import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path

def parse_api_doc(doc_path):
    """解析 Markdown 格式的接口文档，返回接口列表"""
    # 这里需要根据实际文档格式解析，假设文档按章节包含每个接口
    # 返回结构：[{ 'name': '登录', 'method': 'POST', 'url': '/api/login', ... }]
    pass

def generate_test_cases(apis):
    """根据接口列表生成测试用例（正向、负向、边界）"""
    test_cases = []
    for idx, api in enumerate(apis):
        # 生成正向用例
        test_cases.append({
            'test_case_id': f"TC{idx+1:03d}001",
            'feature': api.get('feature', ''),
            'title': f"{api['name']}_正常流程",
            'apiMethod': api['method'],
            'apiUrl': api['url'],
            'apiParams': json.dumps(api.get('params', {}), ensure_ascii=False),
            'expected_status_code': 200,
            'expectedResult': json.dumps(api.get('success_response', {}), ensure_ascii=False),
            'test_type': 'positive',
            'priority': 'P0',
            'status': 'DRAFT',
            'type': 'API',
            'preconditions': '{"dependsOn":[],"bind":{},"vars":{}}',
            'postconditions': '{"asserts":[],"exports":{}}',
            'tags': api.get('tags', '')
        })
        # 添加负向用例等...
    return test_cases

def write_csv(test_cases, output_dir):
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = f"api_test_cases_{timestamp}.csv"
    output_path = Path(output_dir) / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['test_case_id', 'feature', 'title', 'apiMethod', 'apiUrl',
                      'apiHeaders', 'apiParams', 'expected_status_code', 'expectedResult',
                      'test_type', 'priority', 'status', 'type', 'preconditions',
                      'postconditions', 'tags']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(test_cases)
    return output_path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--doc', required=True, help='接口文档路径')
    parser.add_argument('--output', default='test_cases', help='输出目录')
    args = parser.parse_args()

    apis = parse_api_doc(args.doc)
    test_cases = generate_test_cases(apis)
    output_file = write_csv(test_cases, args.output)
    print(f"CSV generated: {output_file}")

if __name__ == '__main__':
    main()