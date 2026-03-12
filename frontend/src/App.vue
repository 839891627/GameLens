/**
 * 帧探·GameLens - 主页面应用组件
 */

<script setup>
import { ref, onMounted } from 'vue';
import { CONFIG } from './config.js';
import api from './api/index.js';
import './styles/main.css';

// 状态
const uploadedImage = ref(null);
const isProcessing = ref(false);
const isModelLoading = ref(true);
const isDragOver = ref(false);
const results = ref([]);
const videoList = ref([]);
const errorMessage = ref('');
const fileInput = ref(null);
const showVideoPlayer = ref(false);
const currentVideoUrl = ref('');
const currentBvid = ref('');
const currentSeconds = ref(0);
const uploadedImageFile = ref(null);

// 初始化
onMounted(async () => {
  try {
    console.log('[App] 正在初始化...');
    videoList.value = await api.video.getVideos();
    console.log(`[App] ✓ 视频列表加载完成，共 ${videoList.value.length} 个视频`);
  } catch (error) {
    console.error('[App] 初始化失败:', error);
    errorMessage.value = '初始化失败: ' + error.message;
  } finally {
    isModelLoading.value = false;
  }
});

// 文件处理
function triggerFileInput() {
  fileInput.value?.click();
}

async function handleFileSelect(event) {
  const file = event.target.files?.[0];
  if (file) await processFile(file);
}

async function handleDrop(event) {
  isDragOver.value = false;
  const file = event.dataTransfer.files?.[0];
  if (file) await processFile(file);
}

async function processFile(file) {
  errorMessage.value = '';
  results.value = [];

  if (!CONFIG.ui.allowedFormats.includes(file.type)) {
    errorMessage.value = '不支持的文件格式，请上传 JPG、PNG 或 WebP 图片';
    return;
  }

  const maxSize = CONFIG.ui.maxFileSize * 1024 * 1024;
  if (file.size > maxSize) {
    errorMessage.value = `文件过大，请上传小于 ${CONFIG.ui.maxFileSize}MB 的图片`;
    return;
  }

  uploadedImage.value = URL.createObjectURL(file);
  uploadedImageFile.value = file;
  await startMatching();
}

async function startMatching() {
  errorMessage.value = '';
  results.value = [];

  if (!uploadedImageFile.value) {
    errorMessage.value = '请先上传游戏截图';
    return;
  }

  isProcessing.value = true;

  try {
    const base64Image = await fileToBase64(uploadedImageFile.value);
    const matches = await api.match.matchImage(base64Image, CONFIG.matching.topK || 5);

    if (matches.length > 0) {
      results.value = matches.map(match => {
        const videoInfo = videoList.value.find(v => v.bvid === match.bvid);
        return {
          ...match,
          video: videoInfo || { bvid: match.bvid, title: '未知视频', author: '未知UP主' }
        };
      });
    } else {
      errorMessage.value = '未找到匹配的视频片段，请尝试更清晰的截图';
    }
  } catch (error) {
    errorMessage.value = '匹配失败: ' + error.message;
  } finally {
    isProcessing.value = false;
  }
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function clearImage() {
  uploadedImage.value = null;
  results.value = [];
  errorMessage.value = '';
  if (fileInput.value) fileInput.value.value = '';
}

function jumpToVideo(bvid, seconds) {
  currentBvid.value = bvid;
  currentSeconds.value = seconds;
  currentVideoUrl.value = `https://player.bilibili.com/player.html?bvid=${bvid}&page=1&t=${seconds}&high_quality=1&autoplay=1`;
  showVideoPlayer.value = true;
}

function closeVideoPlayer() {
  showVideoPlayer.value = false;
  currentVideoUrl.value = '';
}

function openExternalPlayer() {
  window.open(`https://www.bilibili.com/video/${currentBvid.value}?t=${currentSeconds.value}`, '_blank');
}

function getFullImageUrl(imagePath) {
  if (!imagePath) return '';
  if (imagePath.startsWith('http://') || imagePath.startsWith('https://')) return imagePath;
  return `${CONFIG.backendBaseURL}${imagePath}`;
}

function formatTimestamp(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function formatSimilarity(similarity) {
  return `${(similarity * 100).toFixed(1)}%`;
}

function getSimilarityColor(similarity) {
  if (similarity >= 0.8) return '#10b981';
  if (similarity >= 0.6) return '#f59e0b';
  return '#ef4444';
}
</script>

<template>
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

  <!-- 视频播放器弹窗 -->
  <div v-if="showVideoPlayer" class="video-modal" @click.self="closeVideoPlayer">
    <div class="video-modal-content">
      <div class="video-modal-header">
        <h3>⟡ 观看攻略视频</h3>
        <button @click="closeVideoPlayer" class="close-modal-btn">
          <span>✕</span>
        </button>
      </div>
      <div class="video-player-wrapper">
        <iframe
          :src="currentVideoUrl"
          class="video-player"
          scrolling="no"
          border="0"
          frameborder="no"
          framespacing="0"
          allowfullscreen="true"
          allow="autoplay; fullscreen">
        </iframe>
      </div>
      <div class="video-modal-footer">
        <button @click="openExternalPlayer" class="external-player-btn">
          <span class="icon">↗</span>
          <span>在B站打开</span>
        </button>
      </div>
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
        <a href="/admin.html" class="admin-link">
          <span>⚡</span>
          <span>控制台</span>
        </a>
      </div>
    </div>
  </nav>

  <!-- 主内容区 -->
  <main class="main">
    <div class="container">
      <!-- 英雄区域 -->
      <section class="hero-section">
        <div class="hero-content">
          <div class="hero-badge">
            <span class="badge-dot"></span>
            <span>AI 驱动 · 精准匹配</span>
          </div>
          <h1 class="hero-title">
            <span class="title-line">帧探</span>
            <span class="title-accent">·</span>
            <span class="title-line">GameLens</span>
          </h1>
          <p class="hero-subtitle">上传游戏截图，智能匹配攻略视频</p>
        </div>
      </section>

      <!-- 上传区域 -->
      <section class="upload-section" :class="{ 'has-image': uploadedImage }">
        <div v-if="!uploadedImage"
             class="upload-zone"
             :class="{ 'drag-over': isDragOver }"
             @dragover.prevent="isDragOver = true"
             @dragleave.prevent="isDragOver = false"
             @drop.prevent="handleDrop"
             @click="triggerFileInput">
          <div class="upload-content">
            <div class="upload-icon">
              <div class="icon-ring"></div>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="17 8 12 3 7 8"></polyline>
                <line x1="12" y1="3" x2="12" y2="15"></line>
              </svg>
            </div>
            <h2 class="upload-title">拖拽或点击上传截图</h2>
            <p class="upload-hint">支持 JPG、PNG、WebP 格式 · 最大 10MB</p>
          </div>
          <input ref="fileInput" type="file" accept="image/jpeg,image/png,image/webp" @change="handleFileSelect" style="display: none">
        </div>

        <!-- 图片预览 -->
        <div v-else class="preview-container">
          <div class="preview-header">
            <span class="preview-label">已上传截图</span>
            <button @click="clearImage" class="clear-preview-btn">
              <span>✕</span>
              <span>重新上传</span>
            </button>
          </div>
          <div class="preview-image-wrapper">
            <img :src="uploadedImage" alt="上传的游戏截图" class="preview-image">
            <div class="preview-overlay">
              <div class="scan-line"></div>
            </div>
          </div>

          <!-- 处理状态 -->
          <div v-if="isProcessing" class="processing-status">
            <div class="processing-loader">
              <div class="loader-ring"></div>
              <div class="loader-core"></div>
            </div>
            <p>AI 正在分析图片...</p>
          </div>
        </div>
      </section>

      <!-- 结果展示区域 -->
      <section v-if="results.length > 0" class="results-section">
        <div class="results-header">
          <h2 class="results-title">
            <span class="title-icon">◉</span>
            <span>匹配结果</span>
            <span class="results-count">{{ results.length }}</span>
          </h2>
        </div>

        <div class="results-list">
          <div v-for="(result, index) in results"
               :key="index"
               class="result-card">
            <div class="result-rank">
              <span class="rank-number">{{ index + 1 }}</span>
              <span class="rank-decoration"></span>
            </div>

            <div class="result-thumbnail">
              <img :src="getFullImageUrl(result.frame.image_path)" :alt="`匹配帧 ${index + 1}`">
              <div class="thumbnail-overlay">
                <span class="overlay-icon">▶</span>
              </div>
            </div>

            <div class="result-content">
              <h3 class="result-video-title">{{ result.video.title }}</h3>
              <p class="result-author">
                <span class="author-icon">◆</span>
                <span>{{ result.video.author }}</span>
              </p>

              <div class="result-meta">
                <div class="similarity-bar">
                  <div class="similarity-track">
                    <div class="similarity-fill" :style="{ width: result.similarity + '%' }"></div>
                  </div>
                  <span class="similarity-value">{{ formatSimilarity(result.similarity) }}</span>
                </div>

                <div class="time-badge">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <polyline points="12 6 12 12 16 14"></polyline>
                  </svg>
                  <span>{{ formatTimestamp(result.frame.seconds) }}</span>
                </div>
              </div>
            </div>

            <div class="result-action">
              <button @click="jumpToVideo(result.video.bvid, result.frame.seconds)" class="watch-btn">
                <span class="btn-icon">▶</span>
                <span>观看</span>
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- 使用指南 -->
      <section v-else-if="!uploadedImage && !isModelLoading" class="guide-section">
        <h2 class="guide-title">使用指南</h2>
        <div class="guide-steps">
          <div class="guide-step">
            <div class="step-number">
              <span class="number-inner">1</span>
              <div class="step-connector"></div>
            </div>
            <div class="step-content">
              <div class="step-icon">📸</div>
              <h3 class="step-title">上传游戏截图</h3>
              <p class="step-description">截取当前游戏画面并上传</p>
            </div>
          </div>
          <div class="guide-step">
            <div class="step-number">
              <span class="number-inner">2</span>
              <div class="step-connector"></div>
            </div>
            <div class="step-content">
              <div class="step-icon">🔍</div>
              <h3 class="step-title">AI 智能分析</h3>
              <p class="step-description">系统自动识别并匹配视频库</p>
            </div>
          </div>
          <div class="guide-step">
            <div class="step-number">
              <span class="number-inner">3</span>
            </div>
            <div class="step-content">
              <div class="step-icon">▶️</div>
              <h3 class="step-title">观看攻略视频</h3>
              <p class="step-description">直接跳转到对应时间点</p>
            </div>
          </div>
        </div>
      </section>

      <!-- 初始化加载状态 -->
      <div v-if="isModelLoading" class="model-loading">
        <p>正在初始化系统...</p>
      </div>

      <!-- 错误提示 -->
      <div v-if="errorMessage" class="error-toast">
        <div class="error-icon">⚠</div>
        <div class="error-content">
          <strong>错误</strong>
          <p>{{ errorMessage }}</p>
        </div>
        <button @click="errorMessage = ''" class="error-close">✕</button>
      </div>
    </div>
  </main>

  <!-- 页脚 -->
  <footer class="footer">
    <div class="container">
      <div class="footer-content">
        <div class="footer-brand">
          <span class="footer-symbol">◈</span>
          <span>GAMELENS</span>
        </div>
        <div class="footer-info">
          <p>基于图像相似度的手游攻略智能匹配工具</p>
          <p class="footer-note">当前支持：波斯王子：失落的王冠</p>
        </div>
      </div>
      <div class="footer-bottom">
        <span>Beta v1.0</span>
        <span>·</span>
        <span>更多游戏开发中...</span>
      </div>
    </div>
  </footer>
</template>

<style scoped>
/* 组件特定样式 */
</style>