# 启动 GameLens 后端服务器

后端服务器提供自动视频解析功能，无需手动执行脚本。

## 安装依赖

```bash
pip install -r scripts/requirements.txt
```

## 启动服务器

```bash
python server.py
```

服务器启动后访问：
- 主页: http://localhost:5000
- 管理后台: http://localhost:5000/admin.html

## 功能特性

✅ **自动解析** - 添加视频链接后，点击"开始解析"自动下载和处理
✅ **实时日志** - 查看解析进度和日志输出
✅ **视频管理** - 添加、删除视频链接
✅ **状态监控** - 查看已处理/待处理视频统计

## 使用流程

1. 启动服务器: `python server.py`
2. 打开管理后台: http://localhost:5000/admin.html
3. 添加B站视频链接
4. 点击"开始解析"按钮
5. 等待自动处理完成（会自动下载、抽帧、提取特征）
6. 返回主页测试图片匹配功能

## API 接口

- `GET /api/videos` - 获取视频列表
- `POST /api/videos` - 添加单个视频
- `POST /api/videos/bulk` - 批量添加视频
- `DELETE /api/videos/<index>` - 删除视频
- `GET /api/stats` - 获取统计信息
- `POST /api/parse/start` - 开始解析
- `GET /api/parse/status` - 获取解析状态
