# CampusFlow Frontend

校园智能服务平台前端工程，基于 Vue 3 + Vite。

当前版本已经从单页助手升级为“模拟校园信息平台 + 内嵌智能体助手”：

- 教师管理员登录
- 普通学生登录
- 班级管理
- 课表维护与展示
- 天气信息展示
- 智能体助手与工具调用轨迹展示

## 本地运行

PowerShell 如果阻止 `npm.ps1`，请使用 `npm.cmd`：

```bash
npm.cmd install
npm.cmd run dev
```

浏览器访问：

```text
http://127.0.0.1:5173
```

## 接入后端

当前默认使用 Mock 数据。后端完成后，在项目根目录创建 `.env.local`：

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

前端会向后端发送：

```text
POST /api/chat
```

如果不配置 `VITE_API_BASE_URL`，继续使用本地 Mock 响应。

## 代码导读

如果你想快速看懂项目架构、Vue 语法和每个组件的代码含义，请阅读：

```text
docs/前端代码导读.md
```

平台化设计和前后端接口约定请阅读：

```text
docs/平台化架构说明.md
docs/前后端接口契约.md
```
