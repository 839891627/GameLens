# 🎮 GameLens 管理后台 - 快速开始

## 📦 已创建的文件

```
gamelens/
├── server/
│   ├── server.py          # Flask API服务器
│   └── requirements.txt   # Python依赖
├── js/
│   ├── admin.js           # 原版（纯前端）
│   └── admin-api.js       # API版本（使用后端）
├── admin.html            # 管理后台页面
├── start-server.sh       # 启动脚本
└── ADMIN-GUIDE.md        # 详细文档
```

## 🚀 三步启动

### 1. 安装依赖
```bash
pip3 install -r server/requirements.txt
```

### 2. 启动服务器
```bash
# 方式1：使用脚本（推荐）
./start-server.sh

# 方式2：直接运行
python3 server/server.py
```

### 3. 打开管理后台
```
http://localhost:8000/admin.html
```

## ✨ 核心功能

- ✅ **添加视频**：单个/批量添加B站链接
- ✅ **一键解析**：点击按钮自动下载并解析
- ✅ **实时监控**：查看解析进度和日志
- ✅ **视频管理**：查看、删除已添加的视频
- ✅ **数据统计**：总视频数、已解析、待解析

## 🎯 使用流程

```
打开管理后台
    ↓
添加视频链接（可批量）
    ↓
点击"开始解析"
    ↓
实时查看进度和日志
    ↓
解析完成！
    ↓
返回主页开始使用
```

## 📊 API功能对比

| 功能 | 纯前端版本 | API版本 ✨ |
|------|-----------|-----------|
| 添加视频 | 需手动编辑文件 | ✅ 网页操作 |
| 一键解析 | 需手动运行命令 | ✅ 点击按钮 |
| 实时进度 | ❌ 不支持 | ✅ 自动更新 |
| 日志查看 | ❌ 不支持 | ✅ 实时显示 |

## 🔗 地址说明

- **主页**: http://localhost:8000 或 http://localhost:8000/index.html
- **管理后台**: http://localhost:8000/admin.html
- **API端点**: http://localhost:8000/api/*

## 💡 提示

1. 端口 8000 被占用？修改 `server/server.py` 中的 `port=8000`
2. 想用原来的静态服务器？使用 `python -m http.server 8000`
3. 详细文档请查看 `ADMIN-GUIDE.md`

---

**现在就可以一键管理视频了！** 🎉
