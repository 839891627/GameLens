# 🚀 快速开始

5 分钟上手 GameLens！

## 安装

```bash
# 1. 安装依赖
pip install -r gamelens/scripts/requirements.txt

# 2. 安装 FFmpeg
# Ubuntu/Debian
sudo apt install ffmpeg
# macOS
brew install ffmpeg
```

## 启动

```bash
# 启动服务器
python -m gamelens

# 或使用脚本
./start.sh
```

## 访问

打开浏览器：
- **主页**: http://localhost:5000
- **管理后台**: http://localhost:5000/admin.html

## 使用

1. 进入管理后台
2. 添加 B 站视频链接
3. 点击"开始解析"
4. 等待完成
5. 上传截图测试匹配功能

## 常见问题

**Q: 检查环境**
```bash
python -m gamelens check
```

**Q: 更换端口**
```bash
python -m gamelens --port 8000
```

**Q: 查看日志**
```bash
tail -f server.log
```

详细文档请查看 [README](../README.md) 和 [docs/](./)
