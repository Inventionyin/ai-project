import json
from typing import Dict, List, Any
from rule_parser import RuleParser

class APIDocParser:
    """接口文档解析器，模拟解析接口文档（实际可对接代码仓库）"""
    def __init__(self, rule_parser: RuleParser):
        self.rule_parser = rule_parser
        self.mock_api_data = {
            "登录认证模块": {
                "接口列表": [
                    {
                        "api_name": "用户登录",
                        "method": "POST",
                        "url": "/api/login",
                        "params": [
                            {"name": "username", "type": "string", "required": True, "description": "用户名"},
                            {"name": "password", "type": "string", "required": True, "description": "密码"}
                        ],
                        "response_example": '{"code":200,"msg":"登录成功","data":{"token":"xxx"}}',
                        "permission": "无需权限",
                        "error_codes": [
                            {"code": 10001, "msg": "用户名不存在"},
                            {"code": 10002, "msg": "密码错误"}
                        ]
                    },
                    {
                        "api_name": "用户登出",
                        "method": "POST",
                        "url": "/api/logout",
                        "params": [
                            {"name": "token", "type": "string", "required": True, "description": "用户令牌"}
                        ],
                        "response_example": '{"code":200,"msg":"登出成功"}',
                        "permission": "登录用户",
                        "error_codes": [
                            {"code": 10003, "msg": "令牌无效"}
                        ]
                    }
                ],
                "language": "Java Spring Boot"
            },
            "用户管理模块": {
                "接口列表": [
                    {
                        "api_name": "获取用户列表",
                        "method": "GET",
                        "url": "/api/users/list",
                        "params": [
                            {"name": "page", "type": "int", "required": False, "default": 1, "description": "页码"},
                            {"name": "size", "type": "int", "required": False, "default": 10, "description": "每页条数"}
                        ],
                        "response_example": '{"code":200,"msg":"成功","data":{"list":[],"total":0}}',
                        "permission": "管理员",
                        "error_codes": [
                            {"code": 20001, "msg": "权限不足"}
                        ]
                    },
                    {
                        "api_name": "新增用户",
                        "method": "POST",
                        "url": "/api/users/add",
                        "params": [
                            {"name": "username", "type": "string", "required": True, "description": "用户名"},
                            {"name": "email", "type": "string", "required": True, "description": "邮箱"},
                            {"name": "role_id", "type": "int", "required": True, "description": "角色ID"}
                        ],
                        "response_example": '{"code":200,"msg":"新增成功"}',
                        "permission": "管理员",
                        "error_codes": [
                            {"code": 20002, "msg": "用户名已存在"},
                            {"code": 20003, "msg": "邮箱格式错误"}
                        ]
                    }
                ],
                "language": "Java Spring Boot"
            },
            "个人信息管理模块": {
                "接口列表": [
                    {
                        "api_name": "获取个人信息",
                        "method": "GET",
                        "url": "/api/user/info",
                        "params": [],
                        "response_example": '{"code":200,"msg":"成功","data":{"id":1,"username":"admin","email":"admin@test.com"}}',
                        "permission": "登录用户",
                        "error_codes": []
                    }
                ],
                "language": "Python FastAPI"
            },
            "用户注册模块": {
                "接口列表": [
                    {
                        "api_name": "用户注册",
                        "method": "POST",
                        "url": "/api/register",
                        "params": [
                            {"name": "username", "type": "string", "required": True, "description": "用户名"},
                            {"name": "password", "type": "string", "required": True, "description": "密码"},
                            {"name": "email", "type": "string", "required": True, "description": "邮箱"}
                        ],
                        "response_example": '{"code":200,"msg":"注册成功"}',
                        "permission": "无需权限",
                        "error_codes": [
                            {"code": 40001, "msg": "用户名已存在"},
                            {"code": 40002, "msg": "密码长度不足"}
                        ]
                    }
                ],
                "language": "Node.js Express"
            }
        }

    def parse_api_doc(self, module_name: str, language: str = "auto") -> Dict[str, Any]:
        """解析指定模块的接口文档"""
        # 模拟从代码仓库解析，实际可替换为真实的代码搜索逻辑
        if module_name not in self.mock_api_data:
            raise ValueError(f"模块{module_name}不存在，支持的模块：{list(self.mock_api_data.keys())}")
        
        api_data = self.mock_api_data[module_name]
        if language != "auto" and language != api_data["language"]:
            print(f"警告：指定语言{language}与模块实际语言{api_data['language']}不匹配")
        
        return api_data

    def get_api_list(self, module_name: str) -> List[Dict[str, Any]]:
        """获取指定模块的接口列表"""
        api_doc = self.parse_api_doc(module_name)
        return api_doc["接口列表"]