# 🚀 快速开始

5 分钟上手 GameLens！

## 安装

```bash
# 1. 安装 Python 依赖
cd backend
pip install -r requirements.txt

# 2. 安装 FFmpeg
# Ubuntu/Debian
sudo apt install ffmpeg
# macOS
brew install ffmpeg
```

## 启动

### 生产模式（推荐）

```bash
# 一键启动（使用构建后的前端）
./start.sh
```

访问：
- **主页**: http://localhost:8000
- **管理后台**: http://localhost:8000/admin.html
- **后端 API**: http://localhost:8080/api

### 开发模式（支持热更新）

```bash
# 需要先安装前端依赖
cd frontend
npm install

# 启动开发模式
./start.sh dev
```

访问：
- **主页**: http://localhost:3000
- **管理后台**: http://localhost:3000/admin.html
- **后端 API**: http://localhost:8080/api

### 分别启动

```bash
./start.sh backend   # 仅启动后端
./start.sh frontend  # 仅启动前端（生产模式）
```

## 使用

1. 进入管理后台（`/admin.html`）
2. 添加 B 站视频链接
3. 点击"开始解析"
4. 等待完成
5. 上传截图测试匹配功能

## 常见问题

**检查环境**
```bash
cd backend
python -m gamelens check
```

**查看日志**
```bash
tail -f logs/backend.log
tail -f logs/frontend.log
```

**停止服务**
```bash
./start.sh stop
```

**重新构建前端**
```bash
./start.sh rebuild
```

详细文档请查看 [README](../README.md) 和 [PRD](./PRD.md)