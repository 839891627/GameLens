/**
 * 帧探·GameLens - Vue 应用主逻辑
 */

// 导入配置和工具函数
import { CONFIG, formatTimestamp, formatSimilarity, getSimilarityColor } from './config.js';
import { ImageMatcher } from './imageMatcher.js';

const { createApp, ref, onMounted, computed } = Vue;

createApp({
    setup() {
        // 状态管理
        const uploadedImage = ref(null);
        const isProcessing = ref(false);
        const isModelLoading = ref(true);
        const isDragOver = ref(false);
        const results = ref([]);
        const videoIndex = ref(null);
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
                // 初始化图像匹配器
                await new ImageMatcher().init();
                isModelLoading.value = false;

                // 加载视频索引
                await loadVideoIndex();
            } catch (error) {
                console.error('[App] 初始化失败:', error);
                errorMessage.value = '初始化失败: ' + error.message;
                isModelLoading.value = false;
            }
        });

        /**
         * 加载视频索引
         */
        async function loadVideoIndex() {
            try {
                console.log('[App] 正在加载视频索引...');
                const response = await fetch(CONFIG.paths.videoIndex);

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const index = await response.json();
                videoIndex.value = index;

                console.log('[App] ✓ 视频索引加载完成');
                console.log(`[App]   - 视频数: ${index.total_videos}`);
                console.log(`[App]   - 总帧数: ${index.total_frames}`);
            } catch (error) {
                console.error('[App] 视频索引加载失败:', error);
                throw new Error('视频索引加载失败，请确保数据文件存在');
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
         * 根据关键词筛选视频帧
         */
        function filterVideosByKeyword(keyword) {
            if (!keyword || !keyword.trim()) {
                return videoIndex.value;
            }

            const searchTerm = keyword.toLowerCase().trim();
            const filteredVideos = [];
            const totalFrames = { original: 0, filtered: 0 };

            for (const video of videoIndex.value.videos) {
                // 检查视频标题是否包含关键词
                const titleMatch = video.title.toLowerCase().includes(searchTerm);
                const authorMatch = video.author.toLowerCase().includes(searchTerm);

                if (titleMatch || authorMatch) {
                    // 保留整个视频的所有帧
                    filteredVideos.push({
                        ...video,
                        frames: video.frames
                    });
                    totalFrames.filtered += video.frames.length;
                }
                totalFrames.original += video.frames.length;
            }

            console.log(`[App] 关键词筛选: "${keyword}"`);
            console.log(`[App]   - 原始帧数: ${totalFrames.original}`);
            console.log(`[App]   - 筛选后帧数: ${totalFrames.filtered}`);

            if (totalFrames.filtered === 0) {
                errorMessage.value = `未找到与"${keyword}"相关的视频，请尝试其他关键词`;
                return null;
            }

            // 返回筛选后的索引
            return {
                ...videoIndex.value,
                videos: filteredVideos,
                total_frames: totalFrames.filtered
            };
        }

        /**
         * 开始匹配流程（视觉匹配）
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
                // 视觉匹配（对所有视频）
                const img = await loadImage(uploadedImage.value);
                const matcher = new ImageMatcher();
                const matchResults = await matcher.matchAsync(img, videoIndex.value);

                if (matchResults.length === 0) {
                    errorMessage.value = '未找到匹配的视频片段，请尝试更清晰的截图';
                } else {
                    results.value = matchResults;
                    console.log(`[App] ✓ 匹配完成，找到 ${matchResults.length} 个结果`);
                }
            } catch (error) {
                console.error('[App] 匹配失败:', error);
                errorMessage.value = '匹配失败: ' + error.message;
            } finally {
                isProcessing.value = false;
            }
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
         * 加载图片
         */
        function loadImage(src) {
            return new Promise((resolve, reject) => {
                const img = new Image();
                img.onload = () => resolve(img);
                img.onerror = () => reject(new Error('图片加载失败'));
                img.src = src;
            });
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
            getSimilarityColor
        };
    }
}).mount('#app');
