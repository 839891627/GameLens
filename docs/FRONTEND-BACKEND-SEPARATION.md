# 前后端分离架构方案

## 📊 当前架构（前后端混合）

### 问题分析
```
gamelens/
├── index.html          # 前端混在根目录
├── admin.html
├── css/
├── js/
└── gamelens/
    └── server.py       # Flask 托管静态文件
        app = Flask(__name__, static_folder='..')
```

**问题：**
- ❌ 前端和后端耦合在一起
- ❌ 无法独立部署前端
- ❌ 无法使用 CDN 加速
- ❌ 开发和部署不够灵活

---

## ✅ 前后端分离方案

### 方案 1：完全分离（推荐）

```
gamelens/
│
├── backend/                    # ⭐ 后端服务
│   ├── gamelens/
│   │   ├── __init__.py
│   │   ├── __main__.py
│   │   ├── cli.py
│   │   ├── server.py          # 纯 API 服务
│   │   ├── api/               # API 路由
│   │   │   ├── __init__.py
│   │   │   ├── videos.py
│   │   │   ├── parse.py
│   │   │   └── system.py
│   │   ├── services/
│   │   ├── scripts/
│   │   └── utils/
│   │
│   ├── data/                  # 后端数据
│   ├── downloads/
│   └── requirements.txt
│
├── frontend/                   # ⭐ 前端项目
│   ├── public/
│   │   ├── index.html
│   │   ├── admin.html
│   │   ├── favicon.ico
│   │   └── assets/
│   │       ├── images/
│   │       └── fonts/
│   │
│   ├── src/
│   │   ├── css/
│   │   │   ├── style.css
│   │   │   └── admin.css
│   │   │
│   │   ├── js/
│   │   │   ├── main.js
│   │   │   ├── config.js
│   │   │   ├── imageMatcher.js
│   │   │   └── admin-api.js
│   │   │
│   │   └── api/               # API 客户端
│   │       └── client.js
│   │
│   ├── package.json
│   ├── vite.config.js         # 或 webpack.config.js
│   └── README.md
│
├── README.md
├── docker-compose.yml         # 统一部署
└── .gitignore
```

### 方案 2：简洁分离（适合小型项目）

```
gamelens/
│
├── backend/                    # 后端
│   ├── gamelens/              # Python 包
│   │   ├── server.py          # 纯 API（无静态文件）
│   │   └── ...
│   └── data/
│
├── frontend/                   # 前端
│   ├── index.html
│   ├── admin.html
│   ├── css/
│   ├── js/
│   └── README.md
│
├── README.md
└── docker-compose.yml
```

---

## 🔧 实现步骤（方案1）

### 1. 创建目录结构

```bash
# 创建前后端目录
mkdir -p backend frontend
mkdir -p frontend/public frontend/src

# 移动后端文件
mv gamelens data downloads backend/

# 移动前端文件
mv index.html admin.html frontend/public/
mv css frontend/src/
mv js frontend/src/
```

### 2. 修改后端 server.py

**之前（托管静态文件）：**
```python
app = Flask(__name__, static_folder='.', static_url_path='')

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')
```

**之后（纯 API）：**
```python
app = Flask(__name__)  # 移除 static_folder

# 只保留 API 路由
@app.route('/api/videos', methods=['GET'])
def get_videos():
    # ...

# 移除所有静态文件路由
```

### 3. 修改前端 API 配置

**frontend/src/js/config.js**
```javascript
// 开发环境
const API_BASE = 'http://localhost:8080/api';

// 生产环境（根据部署方式调整）
// const API_BASE = '/api';  // 同域名
// const API_BASE = 'https://api.gamelens.com/api';  // 跨域

export const CONFIG = {
    api: {
        baseURL: API_BASE,
        timeout: 30000
    },
    // ...
};
```

### 4. 创建部署配置

**docker-compose.yml**
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8080:8080"
    volumes:
      - ./backend/data:/app/data
    environment:
      - FLASK_ENV=production

  frontend:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./frontend/dist:/usr/share/nginx/html
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - backend
```

---

## 🚀 部署方式

### 本地开发

**后端：**
```bash
cd backend
python -m gamelens
# 运行在 http://localhost:8080
```

**前端：**
```bash
cd frontend
# 方式1：使用静态服务器
python -m http.server 3000

# 方式2：使用 Vite 开发服务器
npm run dev
# 运行在 http://localhost:3000
```

### 生产部署

**选项1：独立部署**
```bash
# 后端部署到服务器
cd backend
python -m gamelens

# 前端部署到 CDN 或静态托管
cd frontend
npm run build
# 上传 dist/ 到 Nginx/Vercel/Netlify
```

**选项2：使用 Docker Compose**
```bash
docker-compose up -d
```

---

## 📊 方案对比

| 特性 | 当前混合 | 简洁分离 | 完全分离 |
|------|---------|---------|---------|
| **目录结构** | 混乱 | 清晰 | 专业 |
| **独立部署** | ❌ | ✅ | ✅ |
| **CDN 加速** | ❌ | ✅ | ✅ |
| **开发效率** | 低 | 中 | 高 |
| **团队协作** | 难 | 易 | 易 |
| **构建工具** | 无 | 可选 | Vite/Webpack |
| **适用规模** | 小型 | 中型 | 大型 |

---

## 🎯 推荐方案

### 当前项目（小型MVP）
推荐 **方案2：简洁分离**

优势：
- ✅ 简单清晰
- ✅ 改动最小
- ✅ 独立部署
- ✅ 易于维护

### 如果要扩展（中型项目）
迁移到 **方案1：完全分离**

优势：
- ✅ 使用现代构建工具
- ✅ 支持热重载
- ✅ 代码分割
- ✅ 生产优化

---

## 🔜 下一步

是否立即执行前后端分离？

1. **立即分离** - 我帮你重构目录和代码
2. **暂不分离** - 先完成功能，后续再优化

选择哪种方案？
