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

```bash
# 回到项目根目录
cd ..

# 一键启动（推荐）
./start.sh

# 或分别启动
./start.sh backend   # 仅启动后端
./start.sh frontend  # 仅启动前端
```

## 访问

打开浏览器：
- **主页**: http://localhost:8000
- **管理后台**: http://localhost:8000/admin.html
- **后端 API**: http://localhost:8080/api

## 使用

1. 进入管理后台 (`/admin.html`)
2. 添加 B 站视频链接
3. 点击"开始解析"
4. 等待完成
5. 上传截图测试匹配功能

## 常见问题

**Q: 检查环境**
```bash
./start.sh backend
```

**Q: 查看日志**
```bash
tail -f logs/backend.log
tail -f logs/frontend.log
```

**Q: 停止服务**
```bash
./start.sh stop
```
python -m gamelens --port 8000
```

**Q: 查看日志**
```bash
tail -f server.log
```

详细文档请查看 [README](../README.md) 和 [docs/](./)
