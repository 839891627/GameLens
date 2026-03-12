# 帧探·GameLens 🎮

> 一图即搜，秒懂攻略 - 手游截图智能匹配攻略视频工具

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Architecture](https://img.shields.io/badge/architecture-Frontend%2FBackend%20Separated-orange)

---

## 🎯 项目简介

**帧探·GameLens** 是一款采用**前后端分离架构**的智能攻略匹配工具。

### 核心特性

- ✅ **AI 视觉匹配** - 图像相似度匹配
- ✅ **自动视频解析** - 一键下载并处理视频
- ✅ **精准时间定位** - 直接跳转到对应时间点
- ✅ **服务端匹配** - 更快的处理速度
- ✅ **向量化检索** - FAISS 向量数据库支持

---

## 📁 项目结构

```
gamelens/
├── backend/                   # 后端服务
│   ├── gamelens/              # Python 包
│   │   ├── api/               # API 路由
│   │   ├── core/              # 核心业务逻辑
│   │   ├── services/          # 服务层
│   │   ├── utils/             # 工具函数
│   │   ├── cli.py             # 命令行工具
│   │   └── __main__.py        # 包入口
│   ├── scripts/               # 数据准备脚本
│   └── data/                  # 数据目录
│
├── frontend/                  # 前端应用
│   ├── src/                   # 源文件
│   │   ├── css/               # 样式
│   │   └── js/                # 脚本
│   ├── dist/                  # 构建输出
│   ├── index.html             # 主页
│   ├── admin.html             # 管理后台
│   ├── package.json           # Vite 配置
│   └── vite.config.js         # 构建配置
│
├── docs/                      # 文档
├── logs/                      # 日志目录
└── start.sh                   # 启动脚本
```

---

## 🚀 快速开始

### 前置要求

- Python 3.8+
- Node.js 16+ (仅开发/构建需要)

### 一键启动（推荐）

```bash
./start.sh
```

### 分别启动

**后端：**
```bash
cd backend
python -m gamelens
```

**前端（开发模式）：**
```bash
cd frontend
npm install
npm run dev
```

**前端（生产模式）：**
```bash
cd frontend
npm run build
cd ..
./start.sh frontend    # 使用构建后的文件
```

### 访问应用

- **主页**: http://localhost:8000
- **管理后台**: http://localhost:8000/admin.html
- **API**: http://localhost:8080/api

---

## 🛠️ 技术栈

### 后端
- **Python 3.8+** - 编程语言
- **Flask** - Web 框架
- **FAISS** - 向量数据库
- **TensorFlow** - AI 模型
- **yt-dlp** - 视频下载
- **OpenCV** - 视频处理

### 前端
- **Vue 3** - 前端框架
- **Vite** - 构建工具
- **CSS3** - 样式
- **Google Fonts** - 字体

---

## 📖 使用指南

### 用户端

1. 打开主页
2. 上传游戏截图
3. 查看匹配结果
4. 跳转观看攻略

### 管理端

1. 进入管理后台
2. 添加 B 站视频链接
3. 点击"开始解析"
4. 等待自动处理完成

---

## 🌐 生产部署

### 前端部署

```bash
cd frontend
npm install
npm run build
# dist/ 目录为生产文件
```

### 后端部署

```bash
cd backend
python -m pip install -r requirements.txt
python -m gamelens
```

### Nginx 配置

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /path/to/gamelens/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API
    location /api {
        proxy_pass http://localhost:8080;
    }
}
```

---

## 📚 文档

- [快速开始](docs/QUICKSTART.md)
- [产品需求文档](docs/PRD.md)
- [端口说明](docs/PORT-CLARIFICATION.md)

---

## 🤝 贡献

欢迎贡献！

---

## 📄 许可证

MIT License

---

<div align="center">

**Made with ❤️ by GameLens Team**

</div>
