# 端口使用说明（前后端分离）

## 📡 正确的端口分配

### 后端 API - 端口 5000
**用途**: 纯 API 服务，不提供 HTML 页面

```
http://localhost:5000/api/videos          # 视频列表 API
http://localhost:5000/api/parse/start     # 启动解析 API
http://localhost:5000/api/system/check    # 系统检查 API
```

### 前端服务 - 端口 8000
**用途**: 静态文件服务，提供 HTML 页面

```
http://localhost:8000/                    # 主页
http://localhost:8000/admin.html          # 管理后台
```

---

## 🚀 启动方式

### 一键启动（推荐）
```bash
./start.sh
```
选择 `1) 前后端一起启动`

### 手动启动

**后端:**
```bash
cd backend
python -m gamelens
```

**前端:**
```bash
cd frontend
python -m http.server 8000 --directory public
```

---

## ⚠️ 常见错误

### ❌ 错误：直接访问 5000 端口看页面
```
http://localhost:5000/           # 404 Not Found
http://localhost:5000/admin.html # 404 Not Found
```

### ✅ 正确：访问 8000 端口看页面
```
http://localhost:8000/           # 主页 ✅
http://localhost:8000/admin.html # 管理后台 ✅
```

---

## 🔌 前后端通信

前端通过 HTTP API 调用后端：

```javascript
// 前端配置（frontend/src/js/config.js）
const API_BASE = 'http://localhost:5000/api';

// API 调用示例
fetch(`${API_BASE}/videos`)
  .then(res => res.json())
  .then(data => console.log(data));
```

---

## 📊 架构示意

```
用户浏览器
    ↓
http://localhost:8000         ← 前端静态文件服务器
    ↓
加载 index.html / admin.html
    ↓
JavaScript 通过 API 调用后端
    ↓
http://localhost:5000/api    ← 后端 API 服务器
```

---

## 🎯 快速检查

### 检查后端是否运行
```bash
curl http://localhost:5000/api/health
```

应该返回：
```json
{"success": true, "message": "GameLens API is running", "version": "1.0.0-mvp"}
```

### 检查前端是否运行
```bash
curl http://localhost:8000/
```

应该返回 HTML 页面

---

**总结：5000 只给 API 用，看页面要去 8000！** ✅
