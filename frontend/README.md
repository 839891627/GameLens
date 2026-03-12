# 帧探·GameLens 前端

基于 Vue 3 + Vite 构建的现代化前端应用，提供游戏截图智能匹配功能。

## 目录结构

```
frontend/
├── index.html           # 主页面入口
├── admin.html           # 管理控制台入口
├── vite.config.js       # Vite 配置文件
├── package.json         # 依赖配置
├── src/                 # 源代码目录
│   ├── css/
│   │   ├── style.css    # 主页面样式
│   │   └── admin.css    # 管理控制台样式
│   └── js/
│       ├── main.js      # 主页面逻辑
│       ├── admin-api.js # 管理控制台逻辑
│       └── config.js    # 配置文件
└── dist/                # 构建输出目录（已 gitignore）
```

## 开发

### 安装依赖

```bash
cd frontend
npm install
```

### 启动开发服务器

```bash
npm run dev
```

访问：http://localhost:3000

### 构建生产版本

```bash
npm run build
```

构建产物输出到 `dist/` 目录。

### 预览构建结果

```bash
npm run preview
```

## 部署

### Nginx 静态托管

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /path/to/gamelens/frontend/dist;
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

### Vercel/Netlify

**Vercel:**
```bash
cd frontend
npm install -g vercel
vercel --prod
```

**Netlify:**
将 `frontend/dist` 目录拖拽到 Netlify 部署页面。

## 技术栈

- **框架**: Vue 3 (Composition API)
- **构建工具**: Vite 5
- **样式**: 原生 CSS
- **代码压缩**: Terser

## 配置说明

### API 地址

在 `src/js/config.js` 中配置 API 地址：

```javascript
// 开发环境
const API_BASE = '/api';

// 生产环境（如需要单独的后端域名）
// const API_BASE = 'https://api.yourdomain.com/api';
```

### Vite 配置

- 开发服务器端口：3000
- API 代理：`/api` → `http://localhost:8080`
- 输出目录：`dist/`
- 资源分类：`assets/`、`css/`、`fonts/`
- 生产构建自动移除 console.log

## 注意事项

1. **跨域问题**：开发环境已配置 Vite 代理，生产环境需 Nginx 代理
2. **缓存策略**：Vite 构建生成的文件名包含 hash，可利用浏览器缓存
3. **首屏加载**：Vue 按需加载，首屏体积优化至最小