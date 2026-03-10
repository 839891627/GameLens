# 帧探·GameLens 技术架构文档

**版本**: v1.0-MVP
**更新日期**: 2025-03-10
**技术负责人**: Claude

---

## 一、技术栈概览

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    用户浏览器                            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐      ┌──────────────┐                │
│  │   Vue 3      │ ───▶ │ TensorFlow.js│                │
│  │   前端框架    │      │   图像特征提取 │                │
│  └──────────────┘      └──────────────┘                │
│         │                       │                        │
│         ▼                       ▼                        │
│  ┌──────────────────────────────────────┐              │
│  │     本地数据层                        │              │
│  │  • video_index.json (视频帧特征库)    │              │
│  │  • IndexedDB (可选缓存)              │              │
│  └──────────────────────────────────────┘              │
│                           │                             │
│                           ▼                             │
│  ┌──────────────────────────────────────┐              │
│  │     外部服务 (可选)                   │              │
│  │  • 阿里云百炼 API (场景理解)          │              │
│  │  • 智谱AI API (语义增强)              │              │
│  └──────────────────────────────────────┘              │
│                                                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              数据准备 (离线/一次性)                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  B站视频 ──▶ Python脚本 ──▶ 抽帧 ──▶ 特征提取 ──▶ JSON索引 │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 1.2 技术选型

| 层级 | 技术选择 | 理由 |
|------|---------|------|
| **前端框架** | Vue 3 (CDN版) | 轻量、响应式、学习成本低 |
| **图像处理** | TensorFlow.js + MobileNet V2 | 纯前端、14MB轻量模型 |
| **样式** | 原生CSS + CSS Variables | 简单直接、无需构建工具 |
| **数据存储** | JSON文件 + IndexedDB | MVP阶段足够、易于部署 |
| **视频处理** | Python + yt-dlp + FFmpeg | 成熟稳定、自动化 |
| **可选AI增强** | 阿里云百炼 / 智谱AI | 提供API密钥、可按需使用 |

---

## 二、核心模块设计

### 2.1 图像特征提取模块

**模型**: MobileNet V2 (特征提取模式)

```javascript
// js/imageMatcher.js
class ImageMatcher {
  constructor() {
    this.model = null;
    this.featureDimension = 1024;
  }

  async init() {
    // 加载MobileNet模型
    this.model = await mobilenet.load({
      version: 2,
      alpha: 1.0
    });
  }

  async extractFeature(imageElement) {
    // 返回1024维特征向量
    const embeddings = await this.model.infer(imageElement, true);
    return embeddings.dataSync(); // Float32Array
  }

  cosineSimilarity(vec1, vec2) {
    let dotProduct = 0;
    let norm1 = 0, norm2 = 0;

    for (let i = 0; i < vec1.length; i++) {
      dotProduct += vec1[i] * vec2[i];
      norm1 += vec1[i] ** 2;
      norm2 += vec2[i] ** 2;
    }

    return dotProduct / (Math.sqrt(norm1) * Math.sqrt(norm2));
  }

  match(queryFeature, videoIndex) {
    const results = [];

    for (const video of videoIndex.videos) {
      for (const frame of video.frames) {
        const similarity = this.cosineSimilarity(
          queryFeature,
          new Float32Array(frame.feature)
        );

        results.push({
          video,
          frame,
          similarity
        });
      }
    }

    // 按相似度降序排序
    return results
      .sort((a, b) => b.similarity - a.similarity)
      .slice(0, 5); // 返回Top 5
  }
}
```

### 2.2 数据索引格式

**video_index.json**:
```json
{
  "version": "1.0",
  "generated_at": "2025-03-10T10:00:00Z",
  "total_frames": 612,
  "total_videos": 5,
  "videos": [
    {
      "bvid": "BV1xx411c7mD",
      "title": "波斯王子：失落的王冠 - 第1章完美通关",
      "author": "攻略UP主",
      "duration": 620,
      "frames": [
        {
          "timestamp": "00:05",
          "seconds": 5,
          "image_path": "data/video_frames/BV1xx411c7mD/frame_001.jpg",
          "feature": [0.012, 0.034, ..., 0.089]
        }
      ]
    }
  ]
}
```

### 2.3 Vue应用结构

```javascript
// js/main.js
const { createApp, ref, computed } = Vue;

createApp({
  setup() {
    // 状态
    const uploadedImage = ref(null);
    const isProcessing = ref(false);
    const isModelLoading = ref(true);
    const results = ref([]);
    const videoIndex = ref(null);
    const matcher = new ImageMatcher();

    // 生命周期
    onMounted(async () => {
      await matcher.init();
      isModelLoading.value = false;

      videoIndex.value = await fetch('./data/video_index.json')
        .then(r => r.json());
    });

    // 方法
    const handleFileSelect = async (file) => {
      uploadedImage.value = URL.createObjectURL(file);
      isProcessing.value = true;

      const img = await loadImage(uploadedImage.value);
      const feature = await matcher.extractFeature(img);
      results.value = matcher.match(feature, videoIndex.value);

      isProcessing.value = false;
    };

    const jumpToVideo = (bvid, seconds) => {
      const url = `https://player.bilibili.com/player.html?bvid=${bvid}&t=${seconds}`;
      window.open(url, '_blank');
    };

    return {
      uploadedImage,
      isProcessing,
      isModelLoading,
      results,
      handleFileSelect,
      jumpToVideo
    };
  }
}).mount('#app');
```

---

## 三、数据处理流程

### 3.1 离线数据准备（Python）

**脚本**: `scripts/build_video_index.py`

```python
#!/usr/bin/env python3
"""
视频索引构建脚本
流程: 下载视频 → 抽帧 → 提取特征 → 生成JSON
"""
import yt_dlp
import cv2
import tensorflow as tf
import json
from pathlib import Path
from tqdm import tqdm

# 配置
FRAME_INTERVAL = 5  # 每5秒抽一帧
OUTPUT_DIR = Path("data/video_frames")
INDEX_FILE = Path("data/video_index.json")

def download_videos(url_list):
    """使用yt-dlp下载B站视频"""
    videos = []

    for url in url_list:
        ydl_opts = {
            'format': 'best[ext=mp4]',
            'outtmpl': 'downloads/%(id)s.%(ext)s'
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            videos.append({
                'bvid': info['id'],
                'title': info['title'],
                'author': info['uploader'],
                'duration': info['duration'],
                'path': f"downloads/{info['id']}.mp4"
            })

    return videos

def extract_frames(video_info):
    """使用OpenCV抽取视频帧"""
    cap = cv2.VideoCapture(video_info['path'])
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    frames = []
    frame_dir = OUTPUT_DIR / video_info['bvid']
    frame_dir.mkdir(parents=True, exist_ok=True)

    frame_interval = fps * FRAME_INTERVAL

    for frame_count in tqdm(range(0, total_frames, int(frame_interval)),
                           desc=f"提取帧: {video_info['bvid']}"):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count)
        ret, frame = cap.read()

        if ret:
            frame_path = frame_dir / f"frame_{len(frames)+1:03d}.jpg"
            cv2.imwrite(str(frame_path), frame)

            timestamp = f"{frame_count//fps//60:02d}:{frame_count//fps%60:02d}"

            frames.append({
                "timestamp": timestamp,
                "seconds": frame_count // fps,
                "image_path": str(frame_path)
            })

    cap.release()
    return frames

def extract_features_batch(frames):
    """批量提取图像特征"""
    # 加载MobileNet模型
    model = tf.keras.applications.MobileNetV2(
        include_top=False,
        pooling='avg',
        weights='imagenet'
    )

    features = []

    for frame in tqdm(frames, desc="提取特征"):
        img = tf.keras.preprocessing.image.load_img(
            frame['image_path'],
            target_size=(224, 224)
        )
        img_array = tf.keras.preprocessing.image.img_to_array(img)
        img_array = tf.keras.applications.mobilenet_v2.preprocess_input(img_array)
        img_array = tf.expand_dims(img_array, 0)

        feature = model.predict(img_array, verbose=0)[0]
        frame['feature'] = feature.tolist()
        features.append(frame)

    return features

def build_index(video_list_file):
    """主函数：构建视频索引"""
    # 1. 读取视频列表
    with open(video_list_file) as f:
        urls = [line.strip() for line in f if line.strip()]

    # 2. 下载视频
    videos = download_videos(urls)

    # 3. 处理每个视频
    for video in videos:
        print(f"\n处理视频: {video['title']}")
        frames = extract_frames(video)
        frames = extract_features_batch(frames)
        video['frames'] = frames

    # 4. 生成索引
    index = {
        "version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "total_frames": sum(len(v['frames']) for v in videos),
        "total_videos": len(videos),
        "videos": videos
    }

    # 5. 保存
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 索引构建完成: {INDEX_FILE}")
    print(f"  总视频数: {index['total_videos']}")
    print(f"  总帧数: {index['total_frames']}")

if __name__ == "__main__":
    build_index("data/videos.txt")
```

### 3.2 依赖安装

**requirements.txt**:
```
yt-dlp>=2023.0.0
opencv-python>=4.8.0
tensorflow>=2.13.0
tqdm>=4.65.0
numpy>=1.24.0
Pillow>=10.0.0
```

---

## 四、可选AI增强模块

### 4.1 阿里云百炼集成

```javascript
// js/ai/dashscope.js
export class DashScopeClient {
  constructor(apiKey) {
    this.apiKey = apiKey;
    this.endpoint = 'https://dashscope.aliyuncs.com/api/v1/services/vision/modal-analysis';
  }

  async analyzeImage(imageBase64) {
    const response = await fetch(this.endpoint, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        image: imageBase64,
        tasks: ['scene_classification', 'object_detection']
      })
    });

    return response.json();
  }
}
```

**使用场景**:
- 识别游戏场景类型（战斗/解谜/跑图）
- 提取画面中的关键元素（BOSS、道具）
- 作为视觉匹配的辅助验证

### 4.2 智谱AI集成

```javascript
// js/ai/zhipu.js
export class ZhipuClient {
  constructor(apiKey) {
    this.apiKey = apiKey;
    this.endpoint = 'https://open.bigmodel.cn/api/paas/v4/chat/completions';
  }

  async understandGameScene(imageBase64) {
    const response = await fetch(this.endpoint, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'glm-4v',
        messages: [
          {
            role: 'user',
            content: [
              {
                type: 'image_url',
                image_url: { url: imageBase64 }
              },
              {
                type: 'text',
                text: '分析这个游戏截图，描述场景类型、主要敌人、环境特点'
              }
            ]
          }
        ]
      })
    });

    return response.json();
  }
}
```

---

## 五、部署方案

### 5.1 部署架构（纯静态）

```
┌────────────────────────────────────────┐
│         GitHub Pages / Vercel          │
│         (静态文件托管)                  │
├────────────────────────────────────────┤
│  index.html                            │
│  css/style.css                         │
│  js/main.js                            │
│  js/imageMatcher.js                    │
│  data/video_index.json                 │
└────────────────────────────────────────┘
         │
         ▼
    用户浏览器
```

**优点**:
- ✅ 零服务器成本
- ✅ CDN加速
- ✅ 易于部署

### 5.2 文件大小预估

| 文件 | 大小 | 说明 |
|------|------|------|
| index.html | ~5KB | 主页面 |
| style.css | ~10KB | 样式文件 |
| TensorFlow.js | ~1MB | CDN加载 |
| MobileNet模型 | ~14MB | 首次加载后缓存 |
| video_index.json | ~2MB | 视频特征索引 |
| **首屏总加载** | ~3MB | 模型缓存后减至1.5MB |

---

## 六、性能优化

### 6.1 模型加载优化

```javascript
// 预加载提示
const model = await mobilenet.load();
console.log('✓ 模型加载完成');

// 使用Service Worker缓存
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js');
}
```

### 6.2 匹配计算优化

```javascript
// 使用Web Worker避免阻塞UI
const worker = new Worker('js/matcher-worker.js');
worker.postMessage({ queryFeature, videoIndex });

worker.onmessage = (e) => {
  results.value = e.data;
};
```

### 6.3 数据懒加载

```javascript
// 按需加载视频帧图片
const loadImage = (path) => {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.src = path;
  });
};
```

---

## 七、安全与隐私

### 7.1 隐私保护
- ✅ 所有图片处理在浏览器本地完成
- ✅ 不上传用户截图到服务器
- ✅ 不收集用户行为数据

### 7.2 API密钥管理
```javascript
// js/config.js
export const CONFIG = {
  dashscope: {
    apiKey: import.meta.env.DASHSCOPE_API_KEY
  },
  zhipu: {
    apiKey: import.meta.env.ZHIPU_API_KEY
  }
};

// .env文件（不提交到git）
DASHSCOPE_API_KEY=your_key_here
ZHIPU_API_KEY=your_key_here
```

---

## 八、监控与日志

### 8.1 前端监控
```javascript
// 简单的错误上报
window.addEventListener('error', (e) => {
  console.error('[GameLens Error]', e.message);
  // 可选：发送到分析服务
});

// 性能监控
performance.mark('model-load-start');
await model.load();
performance.mark('model-load-end');
performance.measure('model-load', 'model-load-start', 'model-load-end');
```

---

## 九、技术风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| TensorFlow.js兼容性 | 中 | 提供降级方案或浏览器提示 |
| 视频索引过大 | 中 | 按需加载、分片加载 |
| 模型加载失败 | 高 | 提供重试机制、错误提示 |
| 匹配准确率低 | 高 | 增加训练数据、调整相似度阈值 |

---

## 十、后续技术优化方向

1. **模型量化**: 使用TensorFlow.js模型量化工具减小模型体积
2. **向量数据库**: 数据量增大后引入Faiss等向量检索库
3. **WebGL加速**: 利用WebGL加速图像处理
4. **PWA支持**: 支持离线使用、桌面安装
