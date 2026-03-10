/**
 * 帧探·GameLens - 管理后台逻辑
 */

const { createApp, ref, computed, onMounted, watch } = Vue;

createApp({
    setup() {
        // ==================== 状态管理 ====================
        const videos = ref([]); // 视频列表
        const newVideoUrl = ref(''); // 新视频URL
        const bulkVideoUrls = ref(''); // 批量视频URLs
        const filter = ref('all'); // 过滤器: all, pending, processed
        const currentPage = ref(1); // 当前页
        const pageSize = 10; // 每页显示数量
        const isParsing = ref(false); // 是否正在解析
        const parseLogs = ref([]); // 解析日志

        // ==================== 计算属性 ====================
        // 过滤后的视频列表
        const filteredVideos = computed(() => {
            if (filter.value === 'pending') {
                return videos.value.filter(v => !v.processed);
            } else if (filter.value === 'processed') {
                return videos.value.filter(v => v.processed);
            }
            return videos.value;
        });

        // 总页数
        const totalPages = computed(() => {
            return Math.ceil(filteredVideos.value.length / pageSize);
        });

        // 当前页的视频
        const paginatedVideos = computed(() => {
            const start = (currentPage.value - 1) * pageSize;
            const end = start + pageSize;
            return filteredVideos.value.slice(start, end);
        });

        // 视频统计
        const videoStats = computed(() => {
            return {
                total: videos.value.length,
                processed: videos.value.filter(v => v.processed).length,
                pending: videos.value.filter(v => !v.processed).length
            };
        });

        // 批量添加的数量
        const bulkCount = computed(() => {
            if (!bulkVideoUrls.value) return 0;
            return bulkVideoUrls.value
                .split('\n')
                .filter(line => line.trim())
                .filter(line => isValidBilibiliUrl(line.trim()))
                .length;
        });

        // ==================== 工具函数 ====================
        // 提取BV号
        function getBvidFromUrl(url) {
            const match = url.match(/(BV[\w]+)/);
            return match ? match[1] : '';
        }

        // 验证B站链接
        function isValidBilibiliUrl(url) {
            return url.includes('bilibili.com/video/') && url.includes('BV');
        }

        // 格式化时间
        function formatTime(date) {
            return new Date(date).toLocaleTimeString('zh-CN');
        }

        // 添加日志
        function addLog(message, type = 'info') {
            parseLogs.value.unshift({
                time: formatTime(new Date()),
                message,
                type
            });
            // 只保留最近100条日志
            if (parseLogs.value.length > 100) {
                parseLogs.value = parseLogs.value.slice(0, 100);
            }
        }

        // ==================== 视频管理 ====================
        // 加载视频列表
        async function loadVideos() {
            try {
                // 读取 videos.txt
                const response = await fetch('data/videos.txt');
                const text = await response.text();
                const urls = text.split('\n')
                    .map(line => line.trim())
                    .filter(line => line && !line.startsWith('#'));

                // 读取 video_index.json 获取已处理的视频
                let processedBvids = new Set();
                try {
                    const indexResponse = await fetch('data/video_index.json');
                    const index = await indexResponse.json();
                    processedBvids = new Set(index.videos.map(v => v.bvid));
                } catch (e) {
                    console.log('No existing index found');
                }

                // 合并数据
                videos.value = urls.map(url => ({
                    url,
                    bvid: getBvidFromUrl(url),
                    processed: processedBvids.has(getBvidFromUrl(url)),
                    title: '' // 可以从 index 获取标题
                }));

                addLog(`已加载 ${urls.length} 个视频`, 'info');
            } catch (error) {
                addLog(`加载视频列表失败: ${error.message}`, 'error');
            }
        }

        // 添加单个视频
        async function addSingleVideo() {
            const url = newVideoUrl.value.trim();
            if (!url) {
                addLog('请输入视频链接', 'warning');
                return;
            }

            if (!isValidBilibiliUrl(url)) {
                addLog('无效的B站视频链接', 'error');
                return;
            }

            const bvid = getBvidFromUrl(url);
            if (videos.value.some(v => v.bvid === bvid)) {
                addLog(`视频 ${bvid} 已存在`, 'warning');
                return;
            }

            // 添加到列表
            videos.value.unshift({
                url,
                bvid,
                processed: false,
                title: ''
            });

            // 保存到 videos.txt
            await saveToVideosTxt();

            newVideoUrl.value = '';
            addLog(`已添加视频: ${bvid}`, 'success');
        }

        // 批量添加视频
        async function addBulkVideos() {
            if (!bulkVideoUrls.value.trim()) {
                addLog('请输入视频链接', 'warning');
                return;
            }

            const urls = bulkVideoUrls.value
                .split('\n')
                .map(line => line.trim())
                .filter(line => line && isValidBilibiliUrl(line));

            if (urls.length === 0) {
                addLog('没有有效的视频链接', 'warning');
                return;
            }

            let addedCount = 0;
            let skippedCount = 0;

            urls.forEach(url => {
                const bvid = getBvidFromUrl(url);
                if (!videos.value.some(v => v.bvid === bvid)) {
                    videos.value.unshift({
                        url,
                        bvid,
                        processed: false,
                        title: ''
                    });
                    addedCount++;
                } else {
                    skippedCount++;
                }
            });

            await saveToVideosTxt();

            bulkVideoUrls.value = '';
            addLog(`批量添加完成: 新增 ${addedCount} 个，跳过 ${skippedCount} 个`, 'success');
        }

        // 删除视频
        async function removeVideo(index) {
            const video = filteredVideos.value[index];
            if (!confirm(`确定要删除视频 ${video.bvid} 吗？`)) {
                return;
            }

            // 从列表中删除
            const actualIndex = videos.value.findIndex(v => v.bvid === video.bvid);
            if (actualIndex !== -1) {
                videos.value.splice(actualIndex, 1);
            }

            await saveToVideosTxt();
            addLog(`已删除视频: ${video.bvid}`, 'info');
        }

        // 保存到 videos.txt
        async function saveToVideosTxt() {
            try {
                const content = videos.value.map(v => v.url).join('\n');

                // 由于浏览器不能直接写文件，我们需要调用后端API
                // 这里提供一个简化的实现：生成下载
                const blob = new Blob([content], { type: 'text/plain' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'videos.txt';
                a.click();
                URL.revokeObjectURL(url);

                addLog('已生成新的 videos.txt 文件，请保存到 data/ 目录', 'info');
            } catch (error) {
                addLog(`保存失败: ${error.message}`, 'error');
            }
        }

        // ==================== 解析功能 ====================
        // 开始解析所有待处理视频
        async function startParsing() {
            const pendingVideos = videos.value.filter(v => !v.processed);
            if (pendingVideos.length === 0) {
                addLog('没有待解析的视频', 'warning');
                return;
            }

            if (!confirm(`确定要解析 ${pendingVideos.length} 个视频吗？这可能需要较长时间。`)) {
                return;
            }

            isParsing.value = true;
            addLog('开始解析视频...', 'info');

            // 生成命令提示
            const commands = generateParseCommands();
            showCommandModal(commands);
        }

        // 解析单个视频
        async function parseSingle(url) {
            const bvid = getBvidFromUrl(url);
            if (!confirm(`确定要解析视频 ${bvid} 吗？`)) {
                return;
            }

            addLog(`开始解析: ${bvid}`, 'info');

            // 生成单视频解析命令
            const command = `python scripts/build_video_index.py`;

            showCommandModal([{ title: `解析视频 ${bvid}`, command }]);
        }

        // 生成解析命令
        function generateParseCommands() {
            const commands = [];

            // 1. 先更新 videos.txt
            commands.push({
                title: '步骤 1: 更新视频列表',
                command: `# 将新生成的 videos.txt 保存到 data/ 目录`
            });

            // 2. 运行解析脚本
            commands.push({
                title: '步骤 2: 运行解析脚本',
                command: `cd /path/to/gamelens && python scripts/build_video_index.py`
            });

            // 3. 启动服务
            commands.push({
                title: '步骤 3: 启动前端服务',
                command: `python -m http.server 8000`
            });

            return commands;
        }

        // 显示命令模态框
        function showCommandModal(commands) {
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.8);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 9999;
                padding: 20px;
            `;

            modal.innerHTML = `
                <div style="
                    background: white;
                    border-radius: 16px;
                    padding: 30px;
                    max-width: 700px;
                    width: 100%;
                    max-height: 80vh;
                    overflow-y: auto;
                    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <h2 style="font-size: 1.5rem; margin: 0;">执行解析</h2>
                        <button id="closeModal" style="
                            background: none;
                            border: none;
                            font-size: 1.5rem;
                            cursor: pointer;
                            color: #718096;
                        ">✕</button>
                    </div>

                    <div style="margin-bottom: 20px;">
                        <p style="color: #718096; margin-bottom: 15px;">
                            请在终端中执行以下命令来解析视频：
                        </p>

                        ${commands.map((cmd, i) => `
                            <div style="margin-bottom: 15px;">
                                <div style="font-weight: 600; margin-bottom: 8px; color: #2d3748;">
                                    ${cmd.title}
                                </div>
                                <div style="
                                    background: #1a202c;
                                    color: #48bb78;
                                    padding: 15px;
                                    border-radius: 8px;
                                    font-family: 'Monaco', 'Consolas', monospace;
                                    font-size: 0.9rem;
                                    white-space: pre-wrap;
                                    word-break: break-all;
                                    position: relative;
                                ">
                                    ${cmd.command}
                                    <button class="copy-cmd" data-cmd="${cmd.command.replace(/`/g, '\\`')}" style="
                                        position: absolute;
                                        top: 10px;
                                        right: 10px;
                                        background: rgba(255,255,255,0.1);
                                        border: 1px solid rgba(255,255,255,0.2);
                                        color: white;
                                        padding: 6px 12px;
                                        border-radius: 6px;
                                        cursor: pointer;
                                        font-size: 0.8rem;
                                    ">复制</button>
                                </div>
                            </div>
                        `).join('')}
                    </div>

                    <div style="
                        background: #fef3c7;
                        border-left: 4px solid #f59e0b;
                        padding: 15px;
                        border-radius: 8px;
                        font-size: 0.9rem;
                        color: #92400e;
                    ">
                        <strong>提示：</strong>
                        <ul style="margin: 10px 0 0 20px; padding: 0;">
                            <li>解析完成后，刷新页面即可看到更新</li>
                            <li>首次解析需要下载MobileNet模型（约8秒）</li>
                            <li>解析时间取决于视频数量和长度</li>
                        </ul>
                    </div>

                    <button id="doneBtn" style="
                        width: 100%;
                        margin-top: 20px;
                        padding: 14px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        border: none;
                        border-radius: 10px;
                        font-size: 1rem;
                        font-weight: 600;
                        cursor: pointer;
                    ">知道了</button>
                </div>
            `;

            document.body.appendChild(modal);

            // 添加复制功能
            modal.querySelectorAll('.copy-cmd').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const cmd = e.target.dataset.cmd;
                    navigator.clipboard.writeText(cmd).then(() => {
                        e.target.textContent = '已复制!';
                        setTimeout(() => {
                            e.target.textContent = '复制';
                        }, 2000);
                    });
                });
            });

            // 关闭模态框
            const close = () => {
                document.body.removeChild(modal);
                isParsing.value = false;
            };

            modal.querySelector('#closeModal').addEventListener('click', close);
            modal.querySelector('#doneBtn').addEventListener('click', close);
            modal.addEventListener('click', (e) => {
                if (e.target === modal) close();
            });
        }

        // ==================== 生命周期 ====================
        onMounted(() => {
            loadVideos();
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
            videoStats,
            bulkCount,
            isParsing,
            parseLogs,
            addSingleVideo,
            addBulkVideos,
            removeVideo,
            startParsing,
            parseSingle
        };
    }
}).mount('#app');
