# 智能招聘系统后端

基于 FastAPI 构建的智能招聘系统后端服务，支持用户认证、候选人管理、职位管理、面试安排等功能。

## 技术栈

- **框架**: FastAPI
- **数据库**: PostgreSQL + SQLAlchemy (异步)
- **认证**: JWT (PyJWT)
- **缓存**: Redis + fastapi-cache2
- **密码加密**: Argon2
- **数据库迁移**: Alembic

## 项目结构

```
my_backend/
├── alembic/               # 数据库迁移
├── core/                  # 核心功能模块
│   ├── auth.py           # JWT 认证处理
│   └── cache.py          # Redis 缓存
├── dependencies/          # FastAPI 依赖注入
├── models/               # SQLAlchemy 数据模型
├── repository/           # 数据仓库层
├── routers/              # API 路由
├── schemas/              # Pydantic 数据模式
├── settings/             # 配置文件
├── main.py               # 应用入口
└── init_data.py          # 初始化数据脚本
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

修改 `settings/setting.env` 文件，配置数据库和 Redis 连接信息：

```env
DB_USERNAME=hr_user
DB_PASSWORD=your_password
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=hr_db

REDIS_HOST=127.0.0.1
REDIS_PORT=6379

JWT_SECRET_KEY=your_secret_key
```

### 3. 数据库迁移

```bash
# 生成迁移文件
alembic revision --autogenerate -m "init model"

# 执行迁移
alembic upgrade head
```

### 4. 初始化数据

```bash
python init_data.py
```

### 5. 启动服务

```bash
uvicorn main:app --reload
```

服务启动后访问：
- API 文档 (Swagger UI): http://127.0.0.1:8000/docs
- API 文档 (ReDoc): http://127.0.0.1:8000/redoc

## API 接口

### 基础接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/` | 根路由测试 | 否 |
| GET | `/hello/{name}` | 测试接口 | 否 |

### 用户接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/user/login` | 用户登录 | 否 |

#### 用户登录

**请求体**:
```json
{
  "email": "boss@qq.com",
  "password": "123456"
}
```

**响应体**:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "user": {
    "id": "xxx",
    "username": "Boss",
    "email": "boss@qq.com",
    "realname": "黄老板",
    "status": "ACTIVE",
    "is_superuser": true,
    "is_hr": false,
    "department": {
      "id": "xxx",
      "name": "人事部"
    }
  }
}
```

## 数据模型

### 用户相关

- **UserModel**: 用户表，包含用户名、邮箱、密码、部门、状态等字段
- **DepartmentModel**: 部门表
- **DingdingUserModel**: 钉钉用户关联表

### 招聘相关

- **PositionModel**: 职位表，包含职位名称、薪资范围、学历要求等
- **CandidateModel**: 候选人表，包含个人信息、工作经历、状态等
- **ResumeModel**: 简历表
- **CandidateAIScoreModel**: AI 评分表
- **InterviewModel**: 面试表

### 候选人状态流转

```
已投递 → AI筛选 → 待面试 → 面试结果 → 入职/拒绝
```

状态枚举：
- `APPLICATION`: 已投递
- `AI_FILTER_PASSED`: AI筛选通过
- `AI_FILTER_FAILED`: AI筛选失败
- `WAITING_FOR_INTERVIEW`: 待面试
- `REFUSED_INTERVIEW`: 拒绝面试
- `INTERVIEW_PASSED`: 面试通过
- `INTERVIEW_REJECTED`: 面试未通过
- `HIRED`: 已入职
- `REJECTED`: 已拒绝

## 认证说明

系统使用 JWT 双 Token 认证机制：

- **Access Token**: 用于访问受保护资源，默认有效期 365 天
- **Refresh Token**: 用于刷新 Access Token，默认有效期 365 天

请求受保护接口时，需在请求头中携带 Token：

```
Authorization: Bearer {access_token}
```

## 预置数据

### 部门

人事部、技术部、运营部、市场部、财务部、法务部、行政部、客服部

### 用户

| 用户名 | 邮箱 | 密码 | 角色 |
|--------|------|------|------|
| Boss | boss@qq.com | 123456 | 超级用户 |
| hr | hr@qq.com | 123456 | 普通用户 |
| tech | tech@qq.com | 123456 | 普通用户 |

## 开发说明

### 添加新路由

1. 在 `routers/` 目录创建路由文件
2. 在 `main.py` 中注册路由

### 添加新模型

1. 在 `models/` 目录创建模型文件
2. 在 `models/__init__.py` 中导出
3. 生成迁移文件并执行迁移

### 添加新接口

1. 定义 Schema (请求/响应)
2. 创建 Repository 方法
3. 在 Router 中实现接口逻辑

## 许可证

MIT
