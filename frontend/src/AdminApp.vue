/**
 * 帧探·GameLens - 管理控制台组件
 */

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import './styles/admin.css';
import api from './api/index.js';

// 状态
const videos = ref([]);
const newVideoUrl = ref('');
const bulkVideoUrls = ref('');
const filter = ref('all');
const currentPage = ref(1);
const pageSize = 10;
const isParsing = ref(false);
const isChecking = ref(false);
const parseLogs = ref([]);
const stats = ref({ total: 0, processed: 0, pending: 0 });
const systemCheck = ref(null);

let pollingTimer = null;

// 计算属性
const filteredVideos = computed(() => {
  if (filter.value === 'pending') {
    return videos.value.filter(v => !v.processed);
  } else if (filter.value === 'processed') {
    return videos.value.filter(v => v.processed);
  }
  return videos.value;
});

const totalPages = computed(() => {
  return Math.ceil(filteredVideos.value.length / pageSize);
});

const paginatedVideos = computed(() => {
  const start = (currentPage.value - 1) * pageSize;
  const end = start + pageSize;
  return filteredVideos.value.slice(start, end);
});

const bulkCount = computed(() => {
  if (!bulkVideoUrls.value) return 0;
  return bulkVideoUrls.value
    .split('\n')
    .filter(line => line.trim())
    .filter(line => line.includes('bilibili.com/video/') && line.includes('BV'))
    .length;
});

// 初始化
onMounted(async () => {
  await loadVideos();
  await loadStats();
});

onUnmounted(() => {
  stopPolling();
});

// API 调用
async function loadVideos() {
  try {
    videos.value = await api.video.getVideos();
    console.log(`[Admin] 已加载 ${videos.value.length} 个视频`);
  } catch (error) {
    addLog(`加载失败: ${error.message}`, 'error');
  }
}

async function loadStats() {
  try {
    stats.value = await api.system.getStats();
  } catch (error) {
    console.error('加载统计失败:', error);
  }
}

async function addSingleVideo() {
  const url = newVideoUrl.value.trim();
  if (!url) {
    addLog('请输入视频链接', 'warning');
    return;
  }

  try {
    await api.video.addVideo(url);
    newVideoUrl.value = '';
    addLog(`已添加视频: ${extractBvid(url)}`, 'success');
    await loadVideos();
    await loadStats();
  } catch (error) {
    addLog(`添加失败: ${error.message}`, 'error');
  }
}

async function addBulkVideos() {
  if (!bulkVideoUrls.value.trim()) {
    addLog('请输入视频链接', 'warning');
    return;
  }

  try {
    await api.video.addBulkVideos(bulkVideoUrls.value);
    bulkVideoUrls.value = '';
    addLog(`批量添加完成`, 'success');
    await loadVideos();
    await loadStats();
  } catch (error) {
    addLog(`批量添加失败: ${error.message}`, 'error');
  }
}

async function removeVideo(index) {
  const video = filteredVideos.value[index];
  if (!confirm(`确定要删除视频 ${video.bvid} 吗？`)) {
    return;
  }

  const actualIndex = videos.value.findIndex(v => v.bvid === video.bvid);

  try {
    await api.video.deleteVideo(actualIndex);
    addLog(`已删除视频: ${video.bvid}`, 'info');
    await loadVideos();
    await loadStats();
  } catch (error) {
    addLog(`删除失败: ${error.message}`, 'error');
  }
}

async function startParsing() {
  const pending = stats.value.pending;
  if (pending === 0) {
    addLog('没有待解析的视频', 'warning');
    return;
  }

  if (!confirm(`确定要解析 ${pending} 个视频吗？这可能需要较长时间。`)) {
    return;
  }

  try {
    await api.parse.startParse();
    isParsing.value = true;
    addLog('解析已开始...', 'info');
    startPolling();
  } catch (error) {
    addLog(`启动解析失败: ${error.message}`, 'error');
  }
}

async function parseSingle(url) {
  const bvid = extractBvid(url);
  if (!confirm(`确定要解析视频 ${bvid} 吗？`)) {
    return;
  }

  addLog(`开始解析: ${bvid}`, 'info');
  // 单个解析暂不支持，提示用户使用一键解析
  alert('单个解析功能开发中，请使用"一键解析"功能');
}

async function checkSystem() {
  isChecking.value = true;
  systemCheck.value = null;
  addLog('开始检查系统环境...', 'info');

  try {
    systemCheck.value = await api.system.checkSystem();
    addLog('系统检查完成', 'info');

    const errors = systemCheck.value.errors || [];
    if (errors.length > 0) {
      addLog(`发现 ${errors.length} 个问题`, 'warning');
    } else {
      addLog('✓ 系统环境正常', 'success');
    }
  } catch (error) {
    addLog(`系统检查出错: ${error.message}`, 'error');
  } finally {
    isChecking.value = false;
  }
}

async function viewFullLogs() {
  try {
    const data = await api.parse.getParseLogs();
    const logsContent = data.logs;

    const newWindow = window.open('', '_blank', 'width=800,height=600,scrollbars=yes');
    if (newWindow) {
      newWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head><title>解析日志</title></head>
        <body style="font-family: monospace; background: #1a1a1a; color: #e0e0e0;">
          <h2>解析日志</h2>
          <hr>
          <pre>${logsContent.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>
        </body>
        </html>
      `);
      newWindow.document.close();
    }
  } catch (error) {
    alert(`获取日志失败: ${error.message}`);
  }
}

async function checkParseStatus() {
  try {
    const status = await api.parse.getParseStatus();
    isParsing.value = status.is_parsing;

    if (status.logs && status.logs.length > 0) {
      const existingTimes = new Set(parseLogs.value.map(l => l.time + l.message));
      status.logs.forEach(log => {
        const key = log.time + log.message;
        if (!existingTimes.has(key)) {
          parseLogs.value.push(log);
        }
      });
      if (parseLogs.value.length > 100) {
        parseLogs.value = parseLogs.value.slice(0, 100);
      }
    }

    if (!status.is_parsing && status.progress === 100) {
      stopPolling();
      addLog('解析完成！正在刷新数据...', 'success');
      await loadVideos();
      await loadStats();
    }
  } catch (error) {
    console.error('检查状态失败:', error);
  }
}

function startPolling() {
  pollingTimer = setInterval(checkParseStatus, 2000);
}

function stopPolling() {
  if (pollingTimer) {
    clearInterval(pollingTimer);
    pollingTimer = null;
  }
}

// 工具函数
function extractBvid(url) {
  const match = url.match(/(BV[\w]+)/);
  return match ? match[1] : '';
}

function addLog(message, type = 'info') {
  parseLogs.value.unshift({
    time: new Date().toLocaleTimeString('zh-CN'),
    message,
    type
  });
  if (parseLogs.value.length > 100) {
    parseLogs.value = parseLogs.value.slice(0, 100);
  }
}
</script>

<template>
  <div id="app">
    <!-- 顶部导航 -->
    <header class="header">
      <div class="header-container">
        <div class="header-brand">
          <div class="brand-logo">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
              <polyline points="2 17 12 22 22 17"></polyline>
              <polyline points="2 12 12 17 22 12"></polyline>
            </svg>
          </div>
          <div class="brand-text">
            <span class="brand-name">GAMELENS</span>
            <span class="brand-version">Console</span>
          </div>
        </div>

        <div class="header-stats">
          <div class="header-stat">
            <span class="stat-label">视频库</span>
            <span class="stat-value">{{ stats.total || 0 }}</span>
          </div>
          <div class="header-stat">
            <span class="stat-label">已解析</span>
            <span class="stat-value">{{ stats.processed || 0 }}</span>
          </div>
          <div class="header-stat">
            <span class="stat-label">待处理</span>
            <span class="stat-value">{{ stats.pending || 0 }}</span>
          </div>
        </div>

        <div class="header-nav">
          <a href="/" class="nav-link">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="19" y1="12" x2="5" y2="12"></line>
              <polyline points="12 19 5 12 12 5"></polyline>
            </svg>
            <span>返回主页</span>
          </a>
        </div>
      </div>
    </header>

    <!-- 主内容 -->
    <main class="main">
      <div class="main-container">
        <!-- 快速操作卡片 -->
        <section class="actions-grid">
          <div class="action-card stat-card">
            <div class="card-header">
              <div class="card-icon primary">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
                  <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
                  <line x1="12" y1="22.08" x2="12" y2="12"></line>
                </svg>
              </div>
              <div class="card-title">视频库概览</div>
            </div>
            <div class="stat-grid">
              <div class="stat-block">
                <span class="stat-number">{{ stats.total || 0 }}</span>
                <span class="stat-desc">总数</span>
              </div>
              <div class="stat-divider"></div>
              <div class="stat-block">
                <span class="stat-number success">{{ stats.processed || 0 }}</span>
                <span class="stat-desc">已解析</span>
              </div>
              <div class="stat-divider"></div>
              <div class="stat-block">
                <span class="stat-number warning">{{ stats.pending || 0 }}</span>
                <span class="stat-desc">待处理</span>
              </div>
            </div>
          </div>

          <div class="action-card primary-action">
            <div class="card-header">
              <div class="card-icon accent">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polygon points="5 3 19 12 5 21 5 3"></polygon>
                </svg>
              </div>
              <div class="card-title">批量解析</div>
            </div>
            <div class="action-content">
              <p class="action-desc">解析所有待处理视频并提取关键帧</p>
              <button @click="startParsing" class="btn-primary" :disabled="isParsing">
                <span v-if="!isParsing">开始解析</span>
                <span v-else>
                  <span class="btn-spinner"></span>
                  <span>解析中...</span>
                </span>
              </button>
            </div>
          </div>

          <div class="action-card">
            <div class="card-header">
              <div class="card-icon info">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <line x1="12" y1="16" x2="12" y2="12"></line>
                  <line x1="12" y1="8" x2="12.01" y2="8"></line>
                </svg>
              </div>
              <div class="card-title">系统检查</div>
            </div>
            <div class="action-content">
              <p class="action-desc">检查服务器环境和依赖配置</p>
              <button @click="checkSystem" class="btn-secondary" :disabled="isChecking">
                <span v-if="!isChecking">检查系统</span>
                <span v-else>
                  <span class="btn-spinner"></span>
                  <span>检查中...</span>
                </span>
              </button>
            </div>
          </div>
        </section>

        <!-- 添加视频区域 -->
        <section class="content-section">
          <div class="section-header">
            <h2 class="section-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
              </svg>
              添加视频
            </h2>
          </div>

          <div class="add-methods">
            <!-- 单个添加 -->
            <div class="add-method">
              <div class="method-label">
                <span class="label-number">01</span>
                <h3>单个添加</h3>
              </div>
              <div class="method-content">
                <div class="input-group">
                  <input
                    v-model="newVideoUrl"
                    type="text"
                    class="text-input"
                    placeholder="粘贴B站视频链接，如：https://www.bilibili.com/video/BV1xx411c7mD"
                    @keyup.enter="addSingleVideo"
                  >
                  <button @click="addSingleVideo" class="btn-add">添加</button>
                </div>
              </div>
            </div>

            <!-- 批量添加 -->
            <div class="add-method">
              <div class="method-label">
                <span class="label-number">02</span>
                <h3>批量添加</h3>
              </div>
              <div class="method-content">
                <textarea
                  v-model="bulkVideoUrls"
                  class="textarea-input"
                  placeholder="批量添加视频链接（每行一个）&#10;https://www.bilibili.com/video/BV1xx411c7mD&#10;https://www.bilibili.com/video/BV1yy411c7mD"
                  rows="5"
                ></textarea>
                <button @click="addBulkVideos" class="btn-bulk">
                  批量添加 ({{ bulkCount }} 个链接)
                </button>
              </div>
            </div>
          </div>
        </section>

        <!-- 视频列表 -->
        <section class="content-section">
          <div class="section-header">
            <h2 class="section-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="8" y1="6" x2="21" y2="6"></line>
                <line x1="8" y1="12" x2="21" y2="12"></line>
                <line x1="8" y1="18" x2="21" y2="18"></line>
                <line x1="3" y1="6" x2="3.01" y2="6"></line>
                <line x1="3" y1="12" x2="3.01" y2="12"></line>
                <line x1="3" y1="18" x2="3.01" y2="18"></line>
              </svg>
              视频列表
              <span class="section-count">{{ filteredVideos.length }}</span>
            </h2>
            <div class="filter-group">
              <button @click="filter = 'all'" :class="['filter-btn', { active: filter === 'all' }]">全部</button>
              <button @click="filter = 'pending'" :class="['filter-btn', { active: filter === 'pending' }]">待解析</button>
              <button @click="filter = 'processed'" :class="['filter-btn', { active: filter === 'processed' }]">已解析</button>
            </div>
          </div>

          <div class="video-list" v-if="paginatedVideos.length > 0">
            <div
              v-for="(video, index) in paginatedVideos"
              :key="index"
              class="video-item"
              :class="{ processed: video.processed, pending: !video.processed }"
            >
              <div class="video-status">
                <span v-if="video.processed" class="status-badge success">
                  <span class="status-dot"></span>
                  已解析
                </span>
                <span v-else class="status-badge warning">
                  <span class="status-dot"></span>
                  待解析
                </span>
              </div>

              <div class="video-info">
                <div class="video-url">{{ video.url }}</div>
                <div class="video-meta">
                  <span class="meta-item">
                    <span class="meta-label">BVID:</span>
                    <code class="meta-value">{{ video.bvid }}</code>
                  </span>
                  <span v-if="video.title" class="meta-item">
                    <span class="meta-label">标题:</span>
                    <span class="meta-value">{{ video.title }}</span>
                  </span>
                </div>
              </div>

              <div class="video-actions">
                <button
                  v-if="!video.processed"
                  @click="parseSingle(video.url)"
                  class="btn-icon-btn"
                  title="解析此视频"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="5 3 19 12 5 21 5 3"></polygon>
                  </svg>
                </button>
                <button
                  @click="removeVideo(index)"
                  class="btn-icon-btn danger"
                  title="删除"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                  </svg>
                </button>
              </div>
            </div>
          </div>

          <!-- 空状态 -->
          <div v-else class="empty-state">
            <div class="empty-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
                <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
              </svg>
            </div>
            <h3>暂无视频</h3>
            <p>添加视频链接开始使用</p>
          </div>

          <!-- 分页 -->
          <div v-if="totalPages > 1" class="pagination">
            <button
              @click="currentPage--"
              :disabled="currentPage === 1"
              class="page-btn"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="15 18 9 12 15 6"></polyline>
              </svg>
            </button>
            <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
            <button
              @click="currentPage++"
              :disabled="currentPage === totalPages"
              class="page-btn"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="9 18 15 12 15 18"></polyline>
              </svg>
            </button>
          </div>
        </section>

        <!-- 日志/系统检查 -->
        <section v-if="parseLogs.length > 0 || systemCheck" class="content-section logs-section">
          <div class="section-header">
            <h2 class="section-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="4 17 10 11 4 5"></polyline>
                <line x1="12" y1="19" x2="20" y2="19"></line>
              </svg>
              <span v-if="systemCheck">系统检查结果</span>
              <span v-else>解析日志</span>
            </h2>
            <button v-if="!systemCheck && parseLogs.length > 0" @click="viewFullLogs" class="btn-text">
              查看完整日志
            </button>
          </div>

          <!-- 系统检查结果 -->
          <div v-if="systemCheck" class="system-check-panel">
            <div class="check-group">
              <h3 class="check-group-title">Python 环境</h3>
              <div class="check-item" :class="{ ok: systemCheck.python, fail: !systemCheck.python }">
                <span class="check-label">Python 版本</span>
                <span class="check-value">{{ systemCheck.python_version || '未安装' }}</span>
                <span class="check-status">{{ systemCheck.python ? '✓' : '✗' }}</span>
              </div>
            </div>

            <div class="check-group">
              <h3 class="check-group-title">依赖包</h3>
              <div v-for="(status, dep) in systemCheck.dependencies" :key="dep" class="check-item" :class="{ ok: status, fail: !status }">
                <span class="check-label">{{ dep }}</span>
                <span class="check-status">{{ status ? '✓' : '✗' }}</span>
              </div>
            </div>

            <div v-if="systemCheck.errors && systemCheck.errors.length > 0" class="check-errors">
              <h4>错误信息</h4>
              <ul>
                <li v-for="(error, index) in systemCheck.errors" :key="index">{{ error }}</li>
              </ul>
            </div>
          </div>

          <!-- 解析日志 -->
          <div v-else class="logs-panel">
            <div
              v-for="(log, index) in parseLogs"
              :key="index"
              :class="['log-entry', `log-${log.type}`]"
            >
              <span class="log-time">{{ log.time }}</span>
              <span class="log-message">{{ log.message }}</span>
            </div>
          </div>
        </section>
      </div>
    </main>

    <!-- 页脚 -->
    <footer class="footer">
      <div class="footer-container">
        <p>GameLens 管理控制台 · Beta v1.0</p>
      </div>
    </footer>
  </div>
</template>

<style scoped>
/* 组件特定样式 */
</style>