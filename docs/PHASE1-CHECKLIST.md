# Phase 1: 环境准备 - 完成指南

## ✅ 已创建的文件

### 脚本文件
- ✓ `scripts/build_video_index.py` - 视频索引构建主脚本
- ✓ `scripts/check_env.py` - 环境检查脚本
- ✓ `scripts/requirements.txt` - Python依赖列表

### 配置文件
- ✓ `js/config.js` - 前端配置文件
- ✓ `data/videos.txt` - 视频链接列表（待填充）
- ✓ `.env.example` - 环境变量示例

### 目录结构
```
gamelens/
├── css/                    # ✓ 已创建
├── js/                     # ✓ 已创建
│   └── config.js           # ✓ 已创建
├── data/                   # ✓ 已创建
│   ├── videos.txt          # ✓ 已创建（需添加链接）
│   └── video_frames/       # ✓ 已创建
├── scripts/                # ✓ 已创建
│   ├── build_video_index.py
│   ├── check_env.py
│   └── requirements.txt
└── docs/                   # ✓ 已创建
```

---

## 📋 待完成的步骤

### 步骤 1: 安装Python依赖

```bash
# 进入项目目录
cd /Users/arvin/Documents/claude/gamelens

# 安装依赖
pip install -r scripts/requirements.txt
```

**依赖说明**：
- `yt-dlp` - 下载B站视频
- `opencv-python` - 视频抽帧
- `tensorflow` - 图像特征提取
- `numpy` - 数值计算
- `pillow` - 图像处理
- `tqdm` - 进度条
- `python-dotenv` - 环境变量管理

**预计安装时间**: 3-5分钟（TensorFlow较大）

---

### 步骤 2: 准备视频列表

#### 2.1 在B站搜索攻略视频

搜索关键词：`波斯王子 失落的王冠 攻略`

#### 2.2 选择5个高质量视频

选择标准：
- ✓ 播放量 > 10万
- ✓ 覆盖主要BOSS战
- ✓ 包含解谜关卡
- ✓ 视频时长 5-15分钟

#### 2.3 编辑视频列表

```bash
# 打开编辑
open -a TextEdit data/videos.txt

# 或使用命令行编辑器
nano data/videos.txt
# 或
vim data/videos.txt
```

#### 2.4 添加视频链接示例

```
# 第1-3章新手攻略
https://www.bilibili.com/video/BV1xxxxx

# 第5章解谜详解
https://www.bilibili.com/video/BV1yyyyy

# 第8章BOSS战打法
https://www.bilibili.com/video/BV1zzzzz

# 第12章最终攻略
https://www.bilibili.com/video/BV1aaaaa

# 全流程速通
https://www.bilibili.com/video/BV1bbbbb
```

---

### 步骤 3: 运行索引构建

```bash
# 验证环境
python scripts/check_env.py

# 构建视频索引（约需10-20分钟）
python scripts/build_video_index.py
```

**执行流程**：
1. Phase 1: 下载视频（5-10分钟）
2. Phase 2: 提取视频帧（2-5分钟）
3. Phase 3: 提取图像特征（3-8分钟）
4. Phase 4: 生成索引（1分钟）

**输出文件**：
- `data/video_index.json` - 视频特征索引（~2MB）
- `data/video_frames/BVxxxxx/` - 抽取的帧图片

---

## 🔍 验证结果

### 检查生成的文件

```bash
# 查看索引文件
ls -lh data/video_index.json

# 查看帧目录
ls -la data/video_frames/

# 预览索引内容
head -50 data/video_index.json
```

### 预期输出示例

```json
{
  "version": "1.0",
  "generated_at": "2025-03-10T...",
  "config": {
    "frame_interval": 5,
    "feature_dimension": 1280
  },
  "total_videos": 5,
  "total_frames": 612,
  "videos": [
    {
      "bvid": "BV1xx411c7mD",
      "title": "波斯王子：失落的王冠 - 第1章攻略",
      "author": "攻略UP主",
      "duration": 620,
      "frames": [
        {
          "timestamp": "00:05",
          "seconds": 5,
          "image_path": "data/video_frames/BV1xx411c7mD/frame_000005.jpg",
          "feature": [0.012, 0.034, ...]
        }
      ]
    }
  ]
}
```

---

## ⚠️ 常见问题

### Q1: yt-dlp下载失败
**解决方案**：
```bash
# 更新yt-dlp
pip install --upgrade yt-dlp

# 或使用代理
export http_proxy=http://127.0.0.1:7890
python scripts/build_video_index.py
```

### Q2: TensorFlow安装失败
**解决方案**：
```bash
# macOS使用虚拟环境
python3 -m venv venv
source venv/bin/activate
pip install -r scripts/requirements.txt
```

### Q3: 视频无法播放
**原因**: 部分B站视频有地区限制
**解决**: 选择其他无限制的视频

---

## 🎯 Phase 1 完成标准

- [ ] Python依赖安装成功
- [ ] `videos.txt` 包含至少5个视频链接
- [ ] `video_index.json` 生成成功（>1MB）
- [ ] `video_frames/` 包含帧图片
- [ ] 环境检查全部通过

```bash
# 最终验证
python scripts/check_env.py
```

---

## 📊 预计耗时

| 步骤 | 时间 |
|------|------|
| 安装依赖 | 3-5分钟 |
| 选择视频 | 5-10分钟 |
| 下载视频 | 5-10分钟 |
| 抽帧处理 | 2-5分钟 |
| 特征提取 | 3-8分钟 |
| **总计** | **20-40分钟** |

---

## 🚀 下一步

Phase 1 完成后，进入 **Phase 2: 前端开发**

```bash
# 开始Phase 2
# 1. 创建 index.html
# 2. 实现 Vue应用
# 3. 实现图像匹配模块
# 4. 添加样式
```

---

**准备就绪后，告诉我进入Phase 2！**
