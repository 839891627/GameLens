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

// 计算属性 - 修复负数问题
const displayStats = computed(() => {
  const total = stats.value.total || 0;
  const processed = stats.value.processed || 0;
  const pending = Math.max(0, total - processed);
  return { total, processed, pending };
});

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
  const pending = displayStats.value.pending;
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

    const newWindow = window.open('', '_blank', 'width=900,height=700,scrollbars=yes');
    if (newWindow) {
      newWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
          <title>解析日志 - GameLens</title>
          <style>
            body {
              font-family: 'Rajdhani', 'Courier New', monospace;
              background: #0a0a0f;
              color: #f0f0f5;
              margin: 0;
              padding: 20px;
            }
            h2 { color: #00f0ff; margin-bottom: 10px; text-shadow: 0 0 10px #00f0ff; }
            pre {
              background: #12121a;
              padding: 20px;
              border-radius: 12px;
              overflow-x: auto;
              font-size: 12px;
              line-height: 1.5;
              border: 1px solid rgba(0, 240, 255, 0.1);
            }
          </style>
        </head>
        <body>
          <h2>解析日志</h2>
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

function formatNumber(num) {
  return num >= 1000 ? (num / 1000).toFixed(1) + 'k' : num.toString();
}
</script>

<template>
  <div class="admin-console">
    <!-- 背景动画 -->
    <div class="bg-animation">
      <div class="grid-overlay"></div>
      <div class="floating-particles">
        <div class="particle" style="left: 10%; top: 20%; animation-delay: 0s;"></div>
        <div class="particle" style="left: 30%; top: 60%; animation-delay: -2s;"></div>
        <div class="particle" style="left: 50%; top: 30%; animation-delay: -4s;"></div>
        <div class="particle" style="left: 70%; top: 70%; animation-delay: -6s;"></div>
        <div class="particle" style="left: 90%; top: 40%; animation-delay: -8s;"></div>
      </div>
      <div class="glow-orbs">
        <div class="orb orb-1"></div>
        <div class="orb orb-2"></div>
        <div class="orb orb-3"></div>
      </div>
    </div>

    <!-- 导航栏 -->
    <nav class="navbar">
      <div class="container">
        <div class="nav-left">
          <div class="logo">
            <span class="logo-symbol">◈</span>
            <span class="logo-text">GAMELENS</span>
          </div>
          <span class="version">v1.0</span>
        </div>
        <div class="nav-right">
          <div class="stats-bar">
            <div class="stat-item">
              <span class="stat-label">总数</span>
              <span class="stat-value">{{ formatNumber(displayStats.total) }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">已解析</span>
              <span class="stat-value processed">{{ formatNumber(displayStats.processed) }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">待处理</span>
              <span class="stat-value pending">{{ formatNumber(displayStats.pending) }}</span>
            </div>
          </div>
        </div>
        <div class="nav-right">
          <a href="/" class="admin-link">
            <span>🏠</span>
            <span>返回首页</span>
          </a>
        </div>
      </div>
    </nav>

    <!-- 主内容区 -->
    <main class="console-main">
      <div class="content-grid">
        <!-- 左侧：操作面板 -->
        <div class="operations-panel">
          <!-- 快速操作 -->
          <section class="panel-section">
            <h3 class="section-header">
              <span class="header-icon">⚡</span>
              <span>快捷操作</span>
            </h3>

            <div class="action-grid">
              <button
                @click="startParsing"
                class="action-card primary-action"
                :disabled="isParsing || displayStats.pending === 0"
              >
                <div class="action-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="5 3 19 12 5 21 5 3"/>
                  </svg>
                </div>
                <div class="action-content">
                  <span class="action-title">批量解析</span>
                  <span class="action-desc">{{ displayStats.pending }} 个视频</span>
                </div>
                <div v-if="isParsing" class="action-status">
                  <span class="spinner"></span>
                </div>
              </button>

              <button
                @click="checkSystem"
                class="action-card system-check"
                :disabled="isChecking"
              >
                <div class="action-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <path d="M12 6v6l4 2"/>
                  </svg>
                </div>
                <div class="action-content">
                  <span class="action-title">系统检查</span>
                  <span class="action-desc">验证环境依赖</span>
                </div>
              </button>
            </div>
          </section>

          <!-- 添加视频 -->
          <section class="panel-section">
            <h3 class="section-header">
              <span class="header-icon">➕</span>
              <span>添加视频</span>
            </h3>

            <div class="add-section">
              <div class="input-row">
                <input
                  v-model="newVideoUrl"
                  type="text"
                  placeholder="粘贴 B站视频链接..."
                  @keyup.enter="addSingleVideo"
                  class="video-input"
                >
                <button @click="addSingleVideo" class="add-btn">添加</button>
              </div>

              <div class="bulk-area">
                <textarea
                  v-model="bulkVideoUrls"
                  placeholder="批量添加（每行一个链接）&#10;https://www.bilibili.com/video/BV..."
                  rows="4"
                  class="bulk-input"
                ></textarea>
                <button @click="addBulkVideos" class="bulk-btn">
                  批量添加 ({{ bulkCount }})
                </button>
              </div>
            </div>
          </section>
        </div>

        <!-- 右侧：视频列表 -->
        <div class="videos-panel">
          <section class="panel-section">
            <div class="list-header">
              <h3 class="section-header">
                <span class="header-icon">📼</span>
                <span>视频库</span>
                <span class="count-badge">{{ filteredVideos.length }}</span>
              </h3>

              <div class="filter-tabs">
                <button
                  v-for="tab in [
                    { key: 'all', label: '全部' },
                    { key: 'pending', label: '待处理' },
                    { key: 'processed', label: '已解析' }
                  ]"
                  :key="tab.key"
                  @click="filter = tab.key"
                  :class="['tab-btn', { active: filter === tab.key }]"
                >
                  {{ tab.label }}
                </button>
              </div>
            </div>

            <div class="video-list">
              <div
                v-for="(video, index) in paginatedVideos"
                :key="index"
                class="video-row"
                :class="{ processed: video.processed, pending: !video.processed }"
              >
                <div class="row-status">
                  <div class="status-dot" :class="video.processed ? 'processed' : 'pending'"></div>
                </div>

                <div class="row-main">
                  <div class="video-bvid">
                    <code>{{ video.bvid }}</code>
                  </div>
                  <div v-if="video.title" class="video-title">
                    {{ video.title }}
                  </div>
                </div>

                <div class="row-actions">
                  <button
                    v-if="!video.processed"
                    @click="startParsing"
                    class="icon-btn process"
                    title="解析"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <polygon points="5 3 19 12 5 21 5 3"/>
                    </svg>
                  </button>
                  <button
                    @click="removeVideo(index)"
                    class="icon-btn delete"
                    title="删除"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <line x1="18" y1="6" x2="6" y2="18"/>
                      <line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                  </button>
                </div>
              </div>

              <!-- 空状态 -->
              <div v-if="paginatedVideos.length === 0" class="empty-state">
                <div class="empty-icon">📂</div>
                <h3>暂无视频</h3>
                <p>添加 B站视频链接开始使用</p>
              </div>

              <!-- 分页 -->
              <div v-if="totalPages > 1" class="pagination">
                <button
                  @click="currentPage--"
                  :disabled="currentPage === 1"
                  class="page-btn"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="15 18 9 12 15 6"/>
                  </svg>
                </button>
                <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
                <button
                  @click="currentPage++"
                  :disabled="currentPage === totalPages"
                  class="page-btn"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="9 18 15 12 9 18"/>
                  </svg>
                </button>
              </div>
            </div>
          </section>

          <!-- 日志面板 -->
          <section v-if="parseLogs.length > 0 || systemCheck" class="panel-section logs-section">
            <h3 class="section-header">
              <span class="header-icon">📋</span>
              <span>{{ systemCheck ? '系统检查' : '操作日志' }}</span>
              <button v-if="!systemCheck && parseLogs.length > 0" @click="viewFullLogs" class="view-all-btn">
                查看全部
              </button>
            </h3>

            <!-- 系统检查结果 -->
            <div v-if="systemCheck" class="system-check">
              <div class="check-section">
                <h4 class="check-title">Python 环境</h4>
                <div class="check-item" :class="{ ok: systemCheck.python, fail: !systemCheck.python }">
                  <span class="check-label">版本</span>
                  <span class="check-value">{{ systemCheck.python_version || 'N/A' }}</span>
                  <span class="check-mark">{{ systemCheck.python ? '✓' : '✗' }}</span>
                </div>
              </div>

              <div class="check-section" v-if="systemCheck.dependencies">
                <h4 class="check-title">依赖包</h4>
                <div
                  v-for="(status, dep) in systemCheck.dependencies"
                  :key="dep"
                  class="check-item"
                  :class="{ ok: status, fail: !status }"
                >
                  <span class="check-label">{{ dep }}</span>
                  <span class="check-mark">{{ status ? '✓' : '✗' }}</span>
                </div>
              </div>

              <div v-if="systemCheck.errors && systemCheck.errors.length" class="errors-section">
                <h4 class="errors-title">错误信息</h4>
                <ul class="errors-list">
                  <li v-for="(error, i) in systemCheck.errors" :key="i">{{ error }}</li>
                </ul>
              </div>
            </div>

            <!-- 日志列表 -->
            <div v-else class="logs-list">
              <div
                v-for="(log, i) in parseLogs"
                :key="i"
                :class="['log-item', `log-${log.type}`]"
              >
                <span class="log-time">{{ log.time }}</span>
                <span class="log-msg">{{ log.message }}</span>
              </div>
            </div>
          </section>
        </div>
      </div>
    </main>

    <!-- 底部状态栏 -->
    <footer class="console-footer">
      <div class="footer-left">
        <span class="status-dot online"></span>
        <span class="status-text">已连接</span>
      </div>
      <div class="footer-right">
        <span class="version">GameLens v1.0.0</span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
/* 组件特定样式 */
</style>