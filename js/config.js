/**
 * 帧探·GameLens - 前端配置文件
 *
 * 此文件包含应用的全局配置项
 */

export const CONFIG = {
  // ==================== API配置 ====================
  // 可选的AI增强API（如果不配置，将使用纯本地MobileNet匹配）

  // 阿里云百炼API
  dashscope: {
    apiKey: '',
    enabled: false,
    endpoint: 'https://dashscope.aliyuncs.com/api/v1/services/vision/modal-analysis'
  },

  // 智谱AI API
  zhipu: {
    apiKey: '',
    enabled: false,
    endpoint: 'https://open.bigmodel.cn/api/paas/v4/chat/completions'
  },

  // ==================== 匹配配置 ====================
  matching: {
    // 返回的匹配结果数量
    topK: 5,

    // 最低相似度阈值 (0-1)
    minSimilarity: 0.5,

    // 特征向量维度
    featureDimension: 1280
  },

  // ==================== 模型配置 ====================
  model: {
    // TensorFlow.js CDN
    tfjsUrl: 'https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@latest',

    // MobileNet模型配置
    mobilenet: {
      version: 2,
      alpha: 1.0  // 模型大小参数: 0.25, 0.50, 0.75, 1.0
    }
  },

  // ==================== 数据路径 ====================
  paths: {
    // 视频索引文件
    videoIndex: './data/video_index.json',

    // 视频帧图片基础路径
    framesBase: './data/video_frames'
  },

  // ==================== UI配置 ====================
  ui: {
    // 上传文件大小限制 (MB)
    maxFileSize: 10,

    // 支持的图片格式
    allowedFormats: ['image/jpeg', 'image/png', 'image/webp'],

    // 最小图片尺寸
    minImageSize: 400,

    // 加载超时时间 (毫秒)
    loadTimeout: 30000
  },

  // ==================== B站播放器配置 ====================
  bilibili: {
    // 新窗口打开嵌入式播放器（推荐）
    openVideo: (bvid, seconds) => {
      // 使用B站嵌入式播放器，支持精确时间跳转
      const url = `https://player.bilibili.com/player.html?bvid=${bvid}&page=1&t=${seconds}&high_quality=1&danmaku=0`;
      window.open(url, '_blank', 'width=1280,height=720');
    },

    // 或者：在当前页面打开官网（备选）
    openVideoWeb: (bvid, seconds) => {
      const url = `https://www.bilibili.com/video/${bvid}?t=${seconds}`;
      window.open(url, '_blank');
    }
  },

  // ==================== 调试配置 ====================
  debug: {
    // 是否启用调试模式
    enabled: false,

    // 是否显示详细日志
    verboseLogging: true,

    // 性能监控
    performanceMonitoring: true
  }
};

// ==================== 工具函数 ====================

/**
 * 格式化时间戳 (秒 -> MM:SS)
 */
export function formatTimestamp(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

/**
 * 格式化相似度分数 (0-1 -> 百分比)
 */
export function formatSimilarity(similarity) {
  return `${(similarity * 100).toFixed(1)}%`;
}

/**
 * 计算颜色 (根据相似度分数)
 */
export function getSimilarityColor(similarity) {
  if (similarity >= 0.8) return '#10b981';  // 绿色 - 高匹配
  if (similarity >= 0.6) return '#f59e0b';  // 橙色 - 中匹配
  return '#ef4444';                          // 红色 - 低匹配
}
