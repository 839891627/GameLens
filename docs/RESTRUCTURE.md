# 项目结构重构方案

## 建议的新结构

```
gamelens/
├── README.md                    # 主文档（整合现有文档）
├── QUICKSTART.md                # 快速开始指南
├── start.py                     # 统一启动入口
│
├── .gitignore                   # Git 忽略规则
├── .env.example                 # 环境变量示例
│
├── public/                      # 前端静态文件
│   ├── index.html
│   ├── admin.html
│   ├── css/
│   │   ├── style.css
│   │   └── admin.css
│   └── js/
│       ├── main.js
│       ├── config.js
│       ├── imageMatcher.js
│       └── admin-api.js        # 删除 admin.js
│
├── server/                      # 后端服务器
│   ├── __init__.py
│   ├── app.py                   # 主服务器（重命名 server.py）
│   ├── routes/                  # 路由模块
│   │   ├── __init__.py
│   │   ├── videos.py
│   │   └── parse.py
│   ├── services/                # 业务逻辑
│   │   ├── __init__.py
│   │   └── video_service.py
│   └── requirements.txt         # 服务器依赖
│
├── scripts/                     # 数据处理脚本
│   ├── build_video_index.py
│   ├── check_env.py
│   └── requirements.txt         # 脚本依赖
│
├── data/                        # 数据目录
│   ├── videos.txt
│   ├── video_index.json
│   └── video_frames/
│
├── docs/                        # 文档
│   ├── API.md                   # API 文档
│   ├── DEPLOYMENT.md            # 部署指南
│   ├── DEVELOPMENT.md           # 开发指南
│   ├── PRD.md
│   └── Technical-Architecture.md
│
└── tests/                       # 测试（新增）
    ├── __init__.py
    ├── test_api.py
    └── test_matching.py
```

## 清理操作

### 1. 删除重复/冗余文件
```bash
# 删除重复的服务器文件
rm -rf server/

# 删除未使用的 admin.js
rm js/admin.js

# 删除重复的文档
rm ADMIN-GUIDE.md ADMIN-README.md
rm SERVER-GUIDE.md
```

### 2. 整合文档
- 将 `README.md`、`DEPLOYMENT.md`、`SERVER-DEPLOY.md` 整合
- 创建简洁的 `QUICKSTART.md`
- 将详细文档移到 `docs/`

### 3. 创建统一启动脚本
- `start.py` - 根据参数启动前端或后端
- `start.sh` - Shell 脚本快捷启动

### 4. 模块化后端
- 将 `server.py` 拆分为多个模块
- 使用 Flask Blueprint 组织路由

## 优势

✅ **清晰的结构** - 一目了然的目录布局
✅ **避免重复** - 删除冗余文件
✅ **易于维护** - 模块化的代码组织
✅ **专业规范** - 符合 Python 项目标准
✅ **便于部署** - 统一的启动方式

## 执行步骤

1. 备份当前项目
2. 创建新目录结构
3. 移动和重命名文件
4. 更新导入路径
5. 测试功能完整性
6. 更新文档
