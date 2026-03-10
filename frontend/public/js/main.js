/**
 * 帧探·GameLens - Vue 应用主逻辑（优化版）
 */

// 导入配置和工具函数
import { CONFIG, formatTimestamp, formatSimilarity, getSimilarityColor } from './config.js';

const { createApp, ref, onMounted } = Vue;

createApp({
    setup() {
        // 状态管理
        const uploadedImage = ref(null);
        const isProcessing = ref(false);
        const isModelLoading = ref(true);
        const isDragOver = ref(false);
        const results = ref([]);
        const videoList = ref([]);  // 改为只存储视频列表，不含帧数据
        const errorMessage = ref('');
        const fileInput = ref(null);

        // 搜索关键词状态
        const searchKeyword = ref('');
        const keywordExamples = ref(['第8章', 'BOSS战', '时间守护者', '天穹护卫', '回到过去']);

        // 视频播放器状态
        const showVideoPlayer = ref(false);
        const currentVideoUrl = ref('');
        const currentBvid = ref('');
        const currentSeconds = ref(0);

        // 上传的图片对象（用于后续匹配）
        const uploadedImageFile = ref(null);

        /**
         * 初始化应用
         */
        onMounted(async () => {
            try {
                console.log('[App] 正在初始化...');

                // 快速加载：只加载视频列表（不含帧数据）
                await loadVideoList();

                console.log('[App] ✓ 初始化完成');
                isModelLoading.value = false;
            } catch (error) {
                console.error('[App] 初始化失败:', error);
                errorMessage.value = '初始化失败: ' + error.message;
                isModelLoading.value = false;
            }
        });

        /**
         * 加载视频列表（轻量级，不含帧数据）
         */
        async function loadVideoList() {
            try {
                console.log('[App] 正在加载视频列表...');
                const response = await fetch(`${CONFIG.api.baseURL}/videos`);

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const result = await response.json();

                if (result.success) {
                    videoList.value = result.data;
                    console.log(`[App] ✓ 视频列表加载完成，共 ${videoList.value.length} 个视频`);
                } else {
                    throw new Error(result.error || '加载视频列表失败');
                }
            } catch (error) {
                console.error('[App] 视频列表加载失败:', error);
                throw error;
            }
        }

        /**
         * 触发文件选择对话框
         */
        function triggerFileInput() {
            fileInput.value?.click();
        }

        /**
         * 处理文件选择
         */
        async function handleFileSelect(event) {
            const file = event.target.files?.[0];
            if (file) {
                await processFile(file);
            }
        }

        /**
         * 处理拖拽上传
         */
        async function handleDrop(event) {
            isDragOver.value = false;
            const file = event.dataTransfer.files?.[0];
            if (file) {
                await processFile(file);
            }
        }

        /**
         * 处理上传的文件
         */
        async function processFile(file) {
            // 清除之前的错误和结果
            errorMessage.value = '';
            results.value = [];

            // 验证文件
            const validation = validateFile(file);
            if (!validation.valid) {
                errorMessage.value = validation.error;
                return;
            }

            // 显示预览
            uploadedImage.value = URL.createObjectURL(file);
            uploadedImageFile.value = file;

            // 自动开始匹配
            await startMatching();
        }

        /**
         * 开始匹配流程（服务端匹配）
         */
        async function startMatching() {
            // 清除之前的错误和结果
            errorMessage.value = '';
            results.value = [];

            if (!uploadedImageFile.value) {
                errorMessage.value = '请先上传游戏截图';
                return;
            }

            isProcessing.value = true;

            try {
                console.log('[App] 正在上传图片进行匹配...');

                // 将图片转换为 Base64
                const base64Image = await fileToBase64(uploadedImageFile.value);

                // 发送到后端进行匹配
                const response = await fetch(`${CONFIG.api.baseURL}/match`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        image: base64Image,
                        max_results: CONFIG.matching.topK || 5
                    })
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const result = await response.json();

                if (result.success) {
                    if (result.data.matches && result.data.matches.length > 0) {
                        // 处理匹配结果，补充视频信息
                        results.value = result.data.matches.map(match => {
                            // 从 videoList 中查找视频信息
                            const videoInfo = videoList.value.find(v => v.bvid === match.bvid);
                            return {
                                ...match,
                                video: videoInfo || {
                                    bvid: match.bvid,
                                    title: '未知视频',
                                    author: '未知UP主'
                                }
                            };
                        });
                        console.log(`[App] ✓ 匹配完成，找到 ${results.value.length} 个结果`);
                    } else {
                        errorMessage.value = '未找到匹配的视频片段，请尝试更清晰的截图';
                    }
                } else {
                    throw new Error(result.error || '匹配失败');
                }
            } catch (error) {
                console.error('[App] 匹配失败:', error);
                errorMessage.value = '匹配失败: ' + error.message;
            } finally {
                isProcessing.value = false;
            }
        }

        /**
         * 将文件转换为 Base64
         */
        function fileToBase64(file) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => {
                    // 移除 data:image/xxx;base64, 前缀
                    const base64 = reader.result.split(',')[1];
                    resolve(base64);
                };
                reader.onerror = reject;
                reader.readAsDataURL(file);
            });
        }

        /**
         * 验证上传的文件
         */
        function validateFile(file) {
            // 检查文件类型
            if (!CONFIG.ui.allowedFormats.includes(file.type)) {
                return {
                    valid: false,
                    error: '不支持的文件格式，请上传 JPG、PNG 或 WebP 图片'
                };
            }

            // 检查文件大小
            const maxSize = CONFIG.ui.maxFileSize * 1024 * 1024;
            if (file.size > maxSize) {
                return {
                    valid: false,
                    error: `文件过大，请上传小于 ${CONFIG.ui.maxFileSize}MB 的图片`
                };
            }

            return { valid: true };
        }

        /**
         * 清除图片
         */
        function clearImage() {
            uploadedImage.value = null;
            results.value = [];
            errorMessage.value = '';
            if (fileInput.value) {
                fileInput.value.value = '';
            }
        }

        /**
         * 跳转到B站视频
         */
        function jumpToVideo(bvid, seconds) {
            currentBvid.value = bvid;
            currentSeconds.value = seconds;
            // 使用B站嵌入式播放器URL
            currentVideoUrl.value = `https://player.bilibili.com/player.html?bvid=${bvid}&page=1&t=${seconds}&high_quality=1&autoplay=1`;
            showVideoPlayer.value = true;
        }

        /**
         * 关闭视频播放器
         */
        function closeVideoPlayer() {
            showVideoPlayer.value = false;
            currentVideoUrl.value = '';
        }

        /**
         * 在B站官网打开视频
         */
        function openExternalPlayer() {
            const url = `https://www.bilibili.com/video/${currentBvid.value}?t=${currentSeconds.value}`;
            window.open(url, '_blank');
        }

        /**
         * 获取完整的图片URL（指向后端服务器）
         */
        function getFullImageUrl(imagePath) {
            if (!imagePath) return '';
            // 如果已经是完整URL，直接返回
            if (imagePath.startsWith('http://') || imagePath.startsWith('https://')) {
                return imagePath;
            }
            // 拼接后端服务器地址
            return `${CONFIG.backendBaseURL}${imagePath}`;
        }

        // 返回模板需要的变量和方法
        return {
            uploadedImage,
            isProcessing,
            isModelLoading,
            isDragOver,
            results,
            errorMessage,
            fileInput,
            searchKeyword,
            keywordExamples,
            triggerFileInput,
            handleFileSelect,
            handleDrop,
            clearImage,
            startMatching,
            jumpToVideo,
            closeVideoPlayer,
            openExternalPlayer,
            showVideoPlayer,
            currentVideoUrl,
            formatTimestamp,
            formatSimilarity,
            getSimilarityColor,
            getFullImageUrl
        };
    }
}).mount('#app');
