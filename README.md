# 帧探·GameLens 🎮

> 一图即搜，秒懂攻略 - 手游截图智能匹配攻略视频工具

![Version](https://img.shields.io/badge/version-1.0--MVP-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Architecture](https://img.shields.io/badge/architecture-Frontend%2FBackend%20Separated-orange)

---

## 🎯 项目简介

**帧探·GameLens** 是一款采用**前后端分离架构**的智能攻略匹配工具。

### 核心特性

- ✅ **前后端分离** - 独立部署，灵活扩展
- ✅ **AI 视觉匹配** - MobileNet V2 图像识别
- ✅ **自动视频解析** - 一键下载并处理视频
- ✅ **精准时间定位** - 直接跳转到对应时间点
- ✅ **纯前端匹配** - 用户截图不上传，保护隐私

---

## 📁 项目结构

```
gamelens/
├── backend/                   # 后端服务
│   ├── gamelens/              # Python 包
│   │   ├── server.py          # Flask API 服务器
│   │   ├── scripts/           # 工具脚本
│   │   └── ...
│   └── data/                  # 数据目录
│
├── frontend/                  # 前端应用
│   ├── public/                # 静态文件
│   │   ├── index.html         # 主页
│   │   └── admin.html         # 管理后台
│   └── src/                   # 源文件
│       ├── css/               # 样式
│       └── js/                # 脚本
│
├── docs/                      # 文档
└── start.sh                   # 启动脚本
```

---

## 🚀 快速开始

### 一键启动（推荐）

```bash
./start.sh
```

这会自动启动：
- 后端 API 服务（端口 5000）
- 前端静态服务器（端口 8000）

### 分别启动

**后端：**
```bash
cd backend
python -m gamelens
```

**前端：**
```bash
cd frontend
python -m http.server 8000 --directory public
```

### 访问应用

- **主页**: http://localhost:8000
- **管理后台**: http://localhost:8000/admin.html
- **API 文档**: http://localhost:5000/api

---

## 🛠️ 技术栈

### 后端
- **Python 3.8+** - 编程语言
- **Flask** - Web 框架
- **TensorFlow** - AI 模型
- **yt-dlp** - 视频下载
- **OpenCV** - 视频处理

### 前端
- **Vue 3** - 前端框架
- **TensorFlow.js** - 图像特征提取
- **MobileNet V2** - 视觉模型
- **CSS3** - 样式

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

### Nginx 配置

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /path/to/gamelens/frontend/public;
    }

    # 后端 API
    location /api {
        proxy_pass http://localhost:5000;
    }
}
```

详细部署指南请查看 [docs/FRONTEND-BACKEND-SEPARATION.md](docs/FRONTEND-BACKEND-SEPARATION.md)

---

## 📚 文档

- [快速开始](docs/QUICKSTART.md)
- [技术架构](docs/Technical-Architecture.md)
- [前后端分离说明](docs/FRONTEND-BACKEND-SEPARATION.md)
- [部署指南](docs/DEPLOYMENT-GUIDE.md)

---

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

<div align="center">

**Made with ❤️ by GameLens Team**

</div>
