# 用户中心模块接口文档

## 1. 用户认证

### 1.1 用户注册
- **描述**: 新用户注册接口
- **方法**: `POST`
- **路径**: `/api/v1/auth/register`
- **Headers**:
  - `Content-Type`: `application/json`
- **请求体 (Body)**:
```json
{
  "username": "testuser",
  "password": "password123",
  "email": "test@example.com"
}
```
- **预期响应 (200)**:
```json
{
  "code": 0,
  "message": "注册成功",
  "data": {
    "userId": "12345"
  }
}
```

### 1.2 用户登录
- **描述**: 已有用户登录获取 Token
- **方法**: `POST`
- **路径**: `/api/v1/auth/login`
- **Headers**:
  - `Content-Type`: `application/json`
- **请求体 (Body)**:
```json
{
  "username": "testuser",
  "password": "password123"
}
```
- **预期响应 (200)**:
```json
{
  "code": 0,
  "message": "登录成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

## 2. 用户信息管理

### 2.1 获取当前用户信息
- **描述**: 获取当前登录用户的详细信息
- **方法**: `GET`
- **路径**: `/api/v1/users/me`
- **Headers**:
  - `Authorization`: `Bearer <token>`
- **预期响应 (200)**:
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "12345",
    "username": "testuser",
    "email": "test@example.com",
    "role": "user"
  }
}
```

### 2.2 更新用户信息
- **描述**: 更新用户的基本资料（不含密码）
- **方法**: `PUT`
- **路径**: `/api/v1/users/me`
- **Headers**:
  - `Authorization`: `Bearer <token>`
  - `Content-Type`: `application/json`
- **请求体 (Body)**:
```json
{
  "nickname": "测试用户",
  "avatar": "https://example.com/avatar.jpg"
}
```
- **预期响应 (200)**:
```json
{
  "code": 0,
  "message": "更新成功"
}
```

### 2.3 删除用户账号
- **描述**: 注销当前用户账号
- **方法**: `DELETE`
- **路径**: `/api/v1/users/me`
- **Headers**:
  - `Authorization`: `Bearer <token>`
- **预期响应 (200)**:
```json
{
  "code": 0,
  "message": "账号已注销"
}
```