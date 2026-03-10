# 帧探·GameLens - API服务器使用指南

## 🚀 快速启动

### 方法1：使用启动脚本（推荐）

```bash
./start-server.sh
```

### 方法2：手动启动

```bash
# 1. 安装依赖
pip3 install -r server/requirements.txt

# 2. 启动服务器
python3 server/server.py
```

## 📱 访问地址

启动后访问以下地址：

- **主页**: http://localhost:8000
- **管理后台**: http://localhost:8000/admin.html
- **API统计**: http://localhost:8000/api/stats

## ⚙️ 管理后台功能

### 1. 添加视频

**单个添加**：
1. 在输入框中粘贴B站视频链接
2. 点击"添加"按钮或按回车
3. 自动保存到 `data/videos.txt`

**批量添加**：
1. 在文本框中粘贴多个链接（每行一个）
2. 点击"批量添加"按钮
3. 自动保存并显示添加结果

### 2. 一键解析

1. 点击"开始解析"按钮
2. 后台自动运行解析脚本
3. 实时显示解析日志
4. 解析完成后自动刷新数据

**解析过程**：
- ✅ 下载视频
- ✅ 抽取关键帧（每5秒）
- ✅ 提取图像特征（MobileNetV2）
- ✅ 生成/更新索引文件

### 3. 实时监控

解析过程中可以实时查看：
- 当前步骤
- 进度百分比
- 详细日志输出

### 4. 筛选和查看

- **全部**：查看所有视频
- **待解析**：只看未处理的视频
- **已解析**：只看已处理的视频

## 🔌 API 接口

### GET /api/videos
获取视频列表

**响应**：
```json
{
  "success": true,
  "data": [
    {
      "url": "https://www.bilibili.com/video/BV1xx411c7mD",
      "bvid": "BV1xx411c7mD",
      "processed": false
    }
  ]
}
```

### POST /api/videos
添加单个视频

**请求**：
```json
{
  "url": "https://www.bilibili.com/video/BV1xx411c7mD"
}
```

### POST /api/videos/bulk
批量添加视频

**请求**：
```json
{
  "urls": "https://www.bilibili.com/video/BV1xx411c7mD\nhttps://www.bilibili.com/video/BV1yy411c7mD"
}
```

### DELETE /api/videos/:index
删除视频（index为视频在列表中的索引）

### POST /api/parse/start
开始解析所有待处理视频

### GET /api/parse/status
获取解析状态

**响应**：
```json
{
  "success": true,
  "data": {
    "is_parsing": false,
    "progress": 100,
    "current_step": "解析完成",
    "logs": [...],
    "error": null
  }
}
```

### GET /api/stats
获取统计信息

**响应**：
```json
{
  "success": true,
  "data": {
    "total": 11,
    "processed": 11,
    "pending": 0
  }
}
```

## 📊 工作流程

```
1. 打开管理后台
   ↓
2. 添加B站视频链接
   ↓
3. 点击"开始解析"
   ↓
4. 实时查看解析进度
   ↓
5. 解析完成后自动刷新
   ↓
6. 返回主页开始使用
```

## ⚠️ 注意事项

1. **端口占用**：默认使用 5000 端口，如需修改请编辑 `server/server.py`
2. **解析时间**：首次解析需要下载 MobileNet 模型（约8秒）
3. **磁盘空间**：每个视频约产生 50-100MB 数据
4. **网络要求**：下载视频需要稳定的网络连接

## 🔧 故障排查

### 服务器无法启动
```bash
# 检查端口占用
lsof -i :5000

# 杀死占用进程
kill -9 <PID>
```

### 解析失败
```bash
# 检查日志
cat data/video_index.json

# 手动运行脚本
python3 scripts/build_video_index.py
```

### 依赖安装失败
```bash
# 使用国内镜像
pip3 install -r server/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 🚀 生产部署

详见 [DEPLOYMENT.md](DEPLOYMENT.md)
