/**
 * 帧探·GameLens - API 服务封装
 */

import { CONFIG } from '../config.js';

/**
 * 通用请求方法
 */
async function request(url, options = {}) {
  const { method = 'GET', headers = {}, body } = options;

  try {
    const response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...headers
      },
      body: body ? JSON.stringify(body) : null
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || '请求失败');
    }

    return data.data;
  } catch (error) {
    console.error('[API Error]', error);
    throw error;
  }
}

/**
 * API 服务对象
 */
export const api = {
  /**
   * 视频相关 API
   */
  video: {
    // 获取视频列表
    getVideos() {
      return request(`${CONFIG.api.baseURL}/videos`);
    },

    // 获取完整视频索引（包含帧数据）
    getVideoIndex() {
      return request(`${CONFIG.api.baseURL}/videos/index`);
    },

    // 添加单个视频
    addVideo(url) {
      return request(`${CONFIG.api.baseURL}/videos`, {
        method: 'POST',
        body: { url }
      });
    },

    // 批量添加视频
    addBulkVideos(urls) {
      return request(`${CONFIG.api.baseURL}/videos/bulk`, {
        method: 'POST',
        body: { urls }
      });
    },

    // 删除视频
    deleteVideo(index) {
      return request(`${CONFIG.api.baseURL}/videos/${index}`, {
        method: 'DELETE'
      });
    }
  },

  /**
   * 匹配相关 API
   */
  match: {
    // 图片匹配
    async matchImage(imageBase64, maxResults = 5) {
      const data = await request(`${CONFIG.api.baseURL}/match`, {
        method: 'POST',
        body: {
          image: imageBase64,
          max_results: maxResults
        }
      });

      return data.matches || [];
    }
  },

  /**
   * 解析相关 API
   */
  parse: {
    // 开始解析
    startParse() {
      return request(`${CONFIG.api.baseURL}/parse/start`, {
        method: 'POST'
      });
    },

    // 获取解析状态
    getParseStatus() {
      return request(`${CONFIG.api.baseURL}/parse/status`);
    },

    // 获取解析日志
    getParseLogs() {
      return request(`${CONFIG.api.baseURL}/parse/logs`);
    }
  },

  /**
   * 系统相关 API
   */
  system: {
    // 获取统计信息
    getStats() {
      return request(`${CONFIG.api.baseURL}/stats`);
    },

    // 系统检查
    checkSystem() {
      return request(`${CONFIG.api.baseURL}/system/check`);
    }
  }
};

// 默认导出整个 API 对象
export default api;