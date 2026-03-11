# 前端部署说明

## 目录结构

```
frontend/
├── public/           # 静态文件
│   ├── index.html
│   └── admin.html
└── src/              # 源文件
    ├── css/
    └── js/
```

## 本地开发

### 启动前端服务器

```bash
# 方式1：使用 Python（推荐）
cd frontend
python -m http.server 8000 --directory public

# 方式2：使用 Node.js
npx serve public -p 8000
```

访问：http://localhost:8000

### 启动后端 API

```bash
cd backend
python -m gamelens
```

API 地址：http://localhost:8080/api

## 生产部署

### 方式1：Nginx 静态托管

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /path/to/gamelens/frontend/public;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 代理
    location /api {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 视频索引文件代理
    location /data {
        proxy_pass http://localhost:8080;
    }
}
```

### 方式2：Vercel/Netlify

**Vercel:**
```bash
# 安装 Vercel CLI
npm i -g vercel

# 部署
cd frontend
vercel --prod
```

**Netlify:**
```bash
# 拖拽 frontend/public 目录到 Netlify
```

### 方式3：CDN

将 frontend/public 目录上传到：
- 阿里云 OSS
- 腾讯云 COS
- AWS S3 + CloudFront

## 配置说明

### API 地址配置

在 `src/js/config.js` 中配置 API 地址：

```javascript
// 开发环境
const API_BASE = 'http://localhost:8080/api';

// 生产环境（通过 Nginx 代理）
const API_BASE = '/api';
```

### 环境变量

创建 `frontend/public/js/env.js`：

```javascript
window.GAMELENS_CONFIG = {
    API_BASE: '/api',  // 或 'https://api.yourdomain.com/api'
};
```

## 注意事项

1. **跨域问题**：后端已配置 CORS，支持跨域请求
2. **视频索引**：开发时需要配置代理访问后端数据
3. **API 超时**：默认30秒，可在 config.js 中调整
