# 帧探·GameLens 🎮

> 一图即搜，秒懂攻略 - 手游截图智能匹配攻略视频工具

![Version](https://img.shields.io/badge/version-1.0--MVP-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 📖 项目简介

**帧探·GameLens** 是一款针对手游玩家的智能攻略匹配工具。玩家只需上传游戏截图，系统即可通过AI视觉技术，自动匹配最相关的攻略视频片段，并精准定位到视频的对应时间点。

### 核心价值

| 痛点 | GameLens解决方案 |
|------|-----------------|
| ❌ 不知道关卡名称怎么搜 | ✅ 截图即搜，无需输入 |
| ❌ 视频太长找不到重点 | ✅ 精准定位到对应时间点 |
| ❌ 需要切换应用查攻略 | ✅ 一键匹配，不中断游戏 |

---

## 🚀 快速开始

### 在线使用

```bash
# 即将上线
https://gamelens.example.com
```

### 本地运行

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/gamelens.git
cd gamelens

# 2. 直接打开（推荐使用本地服务器）
python -m http.server 8000
# 或
npx serve

# 3. 浏览器访问
open http://localhost:8000
```

### 部署到云服务器

📖 **详细部署指南请查看**: [DEPLOYMENT.md](DEPLOYMENT.md)

**快速部署**:

```bash
# 1. 准备数据文件
python scripts/build_video_index.py

# 2. 上传到服务器
scp -r . root@your-server:/var/www/gamelens/

# 3. 配置 Nginx（详见 DEPLOYMENT.md）
```

---

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/gamelens.git
cd gamelens

# 2. 直接打开（推荐使用本地服务器）
python -m http.server 8000
# 或
npx serve

# 3. 浏览器访问
open http://localhost:8000
```

---

## 📁 项目结构

```
gamelens/
├── index.html              # 主页面
├── css/
│   └── style.css          # 样式文件
├── js/
│   ├── main.js            # Vue应用主逻辑
│   ├── imageMatcher.js    # 图像匹配模块
│   └── config.js          # 配置文件
├── data/
│   ├── videos.txt         # 视频链接列表
│   ├── video_index.json   # 生成的视频特征索引
│   └── video_frames/      # 抽取的关键帧图片
├── scripts/               # 数据准备脚本
│   ├── build_video_index.py
│   └── requirements.txt
└── docs/                  # 项目文档
    ├── PRD.md
    └── Technical-Architecture.md
```

---

## 🛠️ 数据准备（首次运行）

### 1. 收集攻略视频

在 `data/videos.txt` 中添加B站视频链接（每行一个）：

```
https://www.bilibili.com/video/BV1xx411c7mD
https://www.bilibili.com/video/BV1yy411c7mD
https://www.bilibili.com/video/BV1zz411c7mD
https://www.bilibili.com/video/BV1aa411c7mD
https://www.bilibili.com/video/BV1bb411c7mD
```

### 2. 安装Python依赖

```bash
pip install -r scripts/requirements.txt
```

### 3. 运行数据构建脚本

```bash
python scripts/build_video_index.py
```

**脚本自动完成**：
- ✅ 下载视频
- ✅ 每5秒抽取一帧
- ✅ 提取图像特征向量
- ✅ 生成 `video_index.json`

---

## 🎯 使用方法

1. **打开网页** → 等待模型加载（首次约10秒）
2. **上传截图** → 拖拽或点击上传游戏截图
3. **查看结果** → 系统显示Top 5匹配结果
4. **跳转观看** → 点击按钮直接跳转到对应时间点

---

## 🧪 技术栈

| 技术 | 用途 |
|------|------|
| Vue 3 | 前端框架 |
| TensorFlow.js | 图像特征提取 |
| MobileNet V2 | 视觉特征模型 |
| Python + yt-dlp | 视频下载 |
| OpenCV + FFmpeg | 视频抽帧 |
| 阿里云百炼/智谱AI | 可选AI增强 |

---

## 📊 MVP范围

- ✅ 支持 **"波斯王子：失落的王冠"** 一款游戏
- ✅ 使用 **5个精选攻略视频** 建立特征库
- ✅ 纯前端实现，无需服务器
- ✅ 匹配准确率目标：Top 1 > 70%

---

## 🔧 配置说明

### API密钥（可选）

如果需要使用AI增强功能，创建 `.env` 文件：

```bash
# .env
DASHSCOPE_API_KEY=your_dashscope_key
ZHIPU_API_KEY=your_zhipu_key
```

### 模型配置

```javascript
// js/config.js
export const CONFIG = {
  model: {
    version: 2,
    alpha: 1.0
  },
  matching: {
    topK: 5,           // 返回Top K结果
    minSimilarity: 0.5  // 最低相似度阈值
  }
};
```

---

## 📈 性能指标

| 指标 | 目标值 |
|------|--------|
| 首屏加载 | < 3秒 |
| 模型加载 | < 8秒 |
| 匹配响应 | < 3秒 |
| 首次总加载 | < 10秒 |

---

## 🤝 贡献指南

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

### 开发流程

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📝 待办事项

- [ ] 完成前端页面开发
- [ ] 实现图像匹配核心逻辑
- [ ] 编写数据构建脚本
- [ ] 添加更多游戏支持
- [ ] 移动端适配
- [ ] 性能优化

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

---

## 🙏 致谢

- [TensorFlow.js](https://www.tensorflow.org/js) - 图像处理
- [Vue.js](https://vuejs.org/) - 前端框架
- [bilibili-api](https://nemo2011.github.io/bilibili-api/) - B站API文档

---

## 📞 联系方式

- 项目主页: [https://github.com/yourusername/gamelens](https://github.com/yourusername/gamelens)
- 问题反馈: [Issues](https://github.com/yourusername/gamelens/issues)

---

<div align="center">

**Made with ❤️ by GameLens Team**

</div>
