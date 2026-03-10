# 帧探·GameLens - 项目概览

本文档帮助你快速了解项目结构和开发计划。

---

## 📋 文档导航

| 文档 | 说明 | 适合人群 |
|------|------|---------|
| [README.md](../README.md) | 项目介绍、快速开始 | 所有人 |
| [PRD.md](PRD.md) | 产品需求文档 | 产品经理、开发者 |
| [Technical-Architecture.md](Technical-Architecture.md) | 技术架构文档 | 开发者 |
| 本文档 | 项目概览、开发计划 | 开发者 |

---

## 🎯 项目目标

开发一个MVP产品，验证核心假设：
> **玩家能否通过上传游戏截图，找到匹配的攻略视频并精准跳转到对应时间点？**

### MVP范围
- ⏱️ 开发周期：1-2周
- 🎮 支持游戏：1款（波斯王子：失落的王冠）
- 📺 视频数量：5个精选攻略视频
- 💻 技术栈：纯前端（Vue3 + TensorFlow.js）

---

## 📂 目录结构说明

```
gamelens/
├── index.html              # 主页面（用户入口）
├── css/                    # 样式文件
│   └── style.css
├── js/                     # JavaScript代码
│   ├── main.js            # Vue应用主逻辑
│   ├── imageMatcher.js    # 图像匹配核心模块
│   └── config.js          # 配置文件
├── data/                   # 数据目录
│   ├── videos.txt         # 视频链接列表（需手动创建）
│   ├── videos.txt.example # 视频链接示例
│   ├── video_index.json   # 生成的视频特征索引
│   └── video_frames/      # 抽取的关键帧图片
├── scripts/                # Python数据准备脚本
│   ├── build_video_index.py  # 主脚本
│   └── requirements.txt      # Python依赖
├── docs/                   # 文档目录
│   ├── PRD.md                     # 产品需求文档
│   ├── Technical-Architecture.md  # 技术架构文档
│   └── PROJECT-OVERVIEW.md        # 本文档
├── .env.example            # 环境变量示例
├── .gitignore              # Git忽略配置
└── README.md               # 项目说明
```

---

## 🔨 开发步骤

### Phase 1: 环境准备 ⏱️ 30分钟

```bash
# 1. 安装Python依赖
pip install -r scripts/requirements.txt

# 2. 准备视频列表
# 在B站搜索"波斯王子 失落的王冠 攻略"
# 选择5个高质量视频，复制链接到 data/videos.txt

# 3. 运行数据构建脚本
python scripts/build_video_index.py
```

**输出**：
- `data/video_index.json` - 视频特征索引
- `data/video_frames/` - 抽取的帧图片

---

### Phase 2: 前端开发 ⏱️ 4-6小时

#### 2.1 创建基础HTML (`index.html`)

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>帧探·GameLens - 手游攻略智能匹配</title>
  <link rel="stylesheet" href="css/style.css">
</head>
<body>
  <div id="app">
    <!-- Vue应用挂载点 -->
  </div>

  <!-- CDN依赖 -->
  <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@latest"></script>
  <script src="https://cdn.jsdelivr.net/npm/@tensorflow-models/mobilenet@latest"></script>

  <!-- 应用代码 -->
  <script src="js/config.js"></script>
  <script src="js/imageMatcher.js"></script>
  <script src="js/main.js"></script>
</body>
</html>
```

#### 2.2 实现图像匹配模块 (`js/imageMatcher.js`)

```javascript
export class ImageMatcher {
  async init() {
    this.model = await mobilenet.load();
  }

  async extractFeature(imageElement) {
    return await this.model.infer(imageElement, true);
  }

  cosineSimilarity(vec1, vec2) {
    // 计算余弦相似度
  }

  match(queryFeature, videoIndex) {
    // 匹配并返回Top K结果
  }
}
```

#### 2.3 实现Vue应用 (`js/main.js`)

```javascript
const { createApp, ref, onMounted } = Vue;

createApp({
  setup() {
    const uploadedImage = ref(null);
    const isProcessing = ref(false);
    const results = ref([]);

    const handleFileSelect = async (file) => {
      // 处理文件上传和匹配
    };

    return { uploadedImage, isProcessing, results, handleFileSelect };
  }
}).mount('#app');
```

#### 2.4 添加样式 (`css/style.css`)

```css
/* 基础样式 */
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  margin: 0;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
}

/* 上传区域 */
.upload-zone {
  /* 拖拽上传样式 */
}

/* 结果卡片 */
.result-card {
  /* 匹配结果样式 */
}
```

---

### Phase 3: 测试与优化 ⏱️ 2-3小时

#### 测试清单

- [ ] 上传不同场景的截图（BOSS战、解谜、跑图）
- [ ] 验证匹配结果的准确性
- [ ] 测试视频跳转功能
- [ ] 检查加载性能
- [ ] 移动端基本可用性测试

#### 优化方向

1. **性能优化**
   - 预加载模型
   - 懒加载视频索引
   - 使用Web Worker

2. **用户体验**
   - 添加加载动画
   - 显示匹配进度
   - 优化错误提示

---

## 🧪 测试用例

### 用例1：BOSS战场景

**输入**：第8章BOSS战截图
**预期**：
- Top 1 匹配度 > 70%
- 时间点误差 < 30秒
- 视频内容确实是该BOSS战

### 用例2：解谜场景

**输入**：第5章解谜关卡截图
**预期**：
- Top 3 匹配度 > 80%
- 包含解谜步骤的视频

### 用例3：普通场景

**输入**：跑图/普通战斗截图
**预期**：
- 能返回相关结果
- 即使匹配度较低，也能给出参考

---

## 📊 成功指标

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| BOSS战Top 1准确率 | > 70% | 20个测试用例 |
| 解谜Top 3准确率 | > 80% | 20个测试用例 |
| 页面加载时间 | < 10秒 | Chrome DevTools |
| 匹配响应时间 | < 3秒 | 性能监控 |

---

## 🚀 部署

### 静态托管（推荐）

| 平台 | 说明 | 命令 |
|------|------|------|
| GitHub Pages | 免费、简单 | `gh-pages` 分支 |
| Vercel | 自动部署 | `vercel deploy` |
| Netlify | 拖拽部署 | 上传到Netlify |

### 本地预览

```bash
# Python
python -m http.server 8000

# Node.js
npx serve

# 访问
open http://localhost:8000
```

---

## 🎓 学习资源

### TensorFlow.js
- [官方文档](https://www.tensorflow.org/js)
- [MobileNet教程](https://www.tensorflow.org/js/models?hl=zh-cn#mobile-net)

### Vue 3
- [官方文档](https://cn.vuejs.org/)
- [Composition API](https://cn.vuejs.org/guide/extras/composition-api-faq.html)

### 视频处理
- [yt-dlp文档](https://github.com/yt-dlp/yt-dlp)
- [OpenCV教程](https://docs.opencv.org/4.x/)

---

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 发起 Pull Request

---

## 📮 反馈

有任何问题或建议，请：
- 提交 [Issue](https://github.com/yourusername/gamelens/issues)
- 发送邮件至: your.email@example.com

---

<div align="center">

**帧探·GameLens Team**

© 2025 GameLens. All rights reserved.

</div>
