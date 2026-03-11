/**
 * 帧探·GameLens - 管理后台逻辑（API版本）
 */

const { createApp, ref, computed, onMounted } = Vue;

// API基础路径配置
const getAPIBaseURL = () => {
    // 开发环境：后端运行在 8080 端口
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        return 'http://localhost:8080/api';
    }
    // 生产环境：使用相对路径（需要 Nginx 等反向代理）
    return '/api';
};

const API_BASE = getAPIBaseURL();

createApp({
    setup() {
        // ==================== 状态管理 ====================
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

        // ==================== 计算属性 ====================
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

        // ==================== API调用 ====================
        async function loadVideos() {
            try {
                const response = await fetch(`${API_BASE}/videos`);
                const result = await response.json();

                if (result.success) {
                    videos.value = result.data;
                    console.log(`[Admin] 已加载 ${videos.value.length} 个视频`);
                } else {
                    addLog(`加载失败: ${result.error}`, 'error');
                }
            } catch (error) {
                addLog(`加载视频列表失败: ${error.message}`, 'error');
            }
        }

        async function loadStats() {
            try {
                const response = await fetch(`${API_BASE}/stats`);
                const result = await response.json();

                if (result.success) {
                    stats.value = result.data;
                }
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
                const response = await fetch(`${API_BASE}/videos`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url })
                });

                const result = await response.json();

                if (result.success) {
                    newVideoUrl.value = '';
                    addLog(result.message, 'success');
                    await loadVideos();
                    await loadStats();
                } else {
                    addLog(result.error, 'error');
                }
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
                const response = await fetch(`${API_BASE}/videos/bulk`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ urls: bulkVideoUrls.value })
                });

                const result = await response.json();

                if (result.success) {
                    bulkVideoUrls.value = '';
                    addLog(result.message, 'success');
                    await loadVideos();
                    await loadStats();
                } else {
                    addLog(result.error, 'error');
                }
            } catch (error) {
                addLog(`批量添加失败: ${error.message}`, 'error');
            }
        }

        async function removeVideo(index) {
            const video = filteredVideos.value[index];
            if (!confirm(`确定要删除视频 ${video.bvid} 吗？`)) {
                return;
            }

            // 找到实际索引
            const actualIndex = videos.value.findIndex(v => v.bvid === video.bvid);

            try {
                const response = await fetch(`${API_BASE}/videos/${actualIndex}`, {
                    method: 'DELETE'
                });

                const result = await response.json();

                if (result.success) {
                    addLog(`已删除视频: ${video.bvid}`, 'info');
                    await loadVideos();
                    await loadStats();
                } else {
                    addLog(result.error, 'error');
                }
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
                const response = await fetch(`${API_BASE}/parse/start`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });

                const result = await response.json();

                if (result.success) {
                    isParsing.value = true;
                    addLog('解析已开始...', 'info');
                    startPolling();
                } else {
                    addLog(result.error, 'error');
                }
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
                const response = await fetch(`${API_BASE}/system/check`);
                const result = await response.json();

                if (result.success) {
                    systemCheck.value = result.data;
                    addLog('系统检查完成', 'info');

                    // 显示检查结果摘要
                    const errors = result.data.errors || [];
                    if (errors.length > 0) {
                        addLog(`发现 ${errors.length} 个问题，请查看下方详情`, 'warning');
                    } else {
                        addLog('✓ 系统环境正常', 'success');
                    }
                } else {
                    addLog('系统检查失败', 'error');
                }
            } catch (error) {
                addLog(`系统检查出错: ${error.message}`, 'error');
                console.error('系统检查失败:', error);
            } finally {
                isChecking.value = false;
            }
        }

        
        async function viewFullLogs() {
            try {
                const response = await fetch(`${API_BASE}/parse/logs`);
                const result = await response.json();

                if (result.success) {
                    const logsContent = result.data.logs;

                    // 创建新窗口显示完整日志
                    const newWindow = window.open('', '_blank', 'width=800,height=600,scrollbars=yes');
                    if (newWindow) {
                        newWindow.document.write(`
                            <!DOCTYPE html>
                            <html>
                            <head>
                                <title>解析日志 - GameLens</title>
                                <style>
                                    body {
                                        font-family: 'Courier New', monospace;
                                        margin: 20px;
                                        background-color: #1a1a1a;
                                        color: #e0e0e0;
                                        white-space: pre-wrap;
                                        word-wrap: break-word;
                                    }
                                    .info { color: #e0e0e0; }
                                    .success { color: #4ade80; }
                                    .warning { color: #fbbf24; }
                                    .error { color: #f87171; }
                                </style>
                            </head>
                            <body>
                                <h2>解析日志 - ${result.data.file_path || ''}</h2>
                                <hr>
                                <pre>${logsContent.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>
                            </body>
                            </html>
                        `);
                        newWindow.document.close();
                    } else {
                        alert('无法打开新窗口，请检查浏览器设置');
                    }
                } else {
                    alert(`获取日志失败: ${result.error}`);
                }
            } catch (error) {
                alert(`获取日志失败: ${error.message}`);
            }
        }

        async function checkParseStatus() {
            try {
                const response = await fetch(`${API_BASE}/parse/status`);
                const result = await response.json();

                if (result.success) {
                    const status = result.data;
                    isParsing.value = status.is_parsing;

                    if (status.logs && status.logs.length > 0) {
                        // 合并新日志
                        const existingTimes = new Set(parseLogs.value.map(l => l.time + l.message));
                        status.logs.forEach(log => {
                            const key = log.time + log.message;
                            if (!existingTimes.has(key)) {
                                parseLogs.value.push(log);
                            }
                        });
                        // 只保留最近100条
                        if (parseLogs.value.length > 100) {
                            parseLogs.value = parseLogs.value.slice(0, 100);
                        }
                    }

                    if (!status.is_parsing && status.progress === 100) {
                        // 解析完成
                        stopPolling();
                        addLog('解析完成！正在刷新数据...', 'success');
                        await loadVideos();
                        await loadStats();
                    }
                }
            } catch (error) {
                console.error('检查状态失败:', error);
            }
        }

        let pollingTimer = null;

        function startPolling() {
            // 每2秒检查一次状态
            pollingTimer = setInterval(checkParseStatus, 2000);
        }

        function stopPolling() {
            if (pollingTimer) {
                clearInterval(pollingTimer);
                pollingTimer = null;
            }
        }

        // ==================== 工具函数 ====================
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

        // ==================== 生命周期 ====================
        onMounted(() => {
            loadVideos();
            loadStats();
        });

        // ==================== 返回 ====================
        return {
            videos,
            newVideoUrl,
            bulkVideoUrls,
            filter,
            currentPage,
            totalPages,
            paginatedVideos,
            filteredVideos,
            stats,
            videoStats: stats,  // 别名，保持与模板一致
            bulkCount,
            isParsing,
            isChecking,
            parseLogs,
            systemCheck,
            addSingleVideo,
            addBulkVideos,
            removeVideo,
            startParsing,
            parseSingle,
            checkSystem,
            viewFullLogs
        };
    }
}).mount('#app');
