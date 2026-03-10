/**
 * 帧探·GameLens - 图像匹配核心模块
 * 使用 MobileNet 提取图像特征并进行相似度匹配
 */

class ImageMatcher {
    constructor() {
        this.model = null;
        this.featureDimension = 1280; // MobileNetV2 特征维度
        this.isModelLoaded = false;
    }

    /**
     * 初始化模型
     */
    async init() {
        if (this.isModelLoaded) return;

        try {
            console.log('[ImageMatcher] 正在加载 MobileNet 模型...');
            this.model = await mobilenet.load({
                version: 2,
                alpha: 1.0
            });
            this.isModelLoaded = true;
            console.log('[ImageMatcher] ✓ MobileNet 模型加载完成');
        } catch (error) {
            console.error('[ImageMatcher] ✗ 模型加载失败:', error);
            throw new Error('模型加载失败，请刷新页面重试');
        }
    }

    /**
     * 提取图像特征向量
     * @param {HTMLImageElement} imageElement - 图片元素
     * @returns {Float32Array} - 1280维特征向量
     */
    async extractFeature(imageElement) {
        if (!this.isModelLoaded) {
            await this.init();
        }

        try {
            // 使用 MobileNet 的激活值作为特征（embedding模式）
            const embeddings = await this.model.infer(imageElement, true);

            // 转换为 Float32Array 并返回
            const feature = embeddings.dataSync();
            return new Float32Array(feature);
        } catch (error) {
            console.error('[ImageMatcher] 特征提取失败:', error);
            throw new Error('特征提取失败，请确保图片格式正确');
        }
    }

    /**
     * 计算余弦相似度
     * @param {Float32Array} vec1 - 向量1
     * @param {Float32Array} vec2 - 向量2
     * @returns {number} - 相似度 (0-1)
     */
    cosineSimilarity(vec1, vec2) {
        let dotProduct = 0;
        let norm1 = 0;
        let norm2 = 0;

        for (let i = 0; i < vec1.length; i++) {
            dotProduct += vec1[i] * vec2[i];
            norm1 += vec1[i] ** 2;
            norm2 += vec2[i] ** 2;
        }

        const magnitude = Math.sqrt(norm1) * Math.sqrt(norm2);

        // 避免除以零
        if (magnitude === 0) return 0;

        return dotProduct / magnitude;
    }

    /**
     * 匹配查询图像与视频索引
     * @param {Float32Array} queryFeature - 查询图像特征
     * @param {Object} videoIndex - 视频索引对象
     * @param {number} topK - 返回前K个结果
     * @param {number} minSimilarity - 最低相似度阈值
     * @returns {Array} - 匹配结果数组
     */
    match(queryFeature, videoIndex, topK = 5, minSimilarity = 0.5) {
        const results = [];

        // 遍历所有视频的所有帧
        for (const video of videoIndex.videos) {
            for (const frame of video.frames) {
                // 将特征数组转换回 Float32Array
                const frameFeature = new Float32Array(frame.feature);

                // 计算相似度
                const similarity = this.cosineSimilarity(queryFeature, frameFeature);

                // 只保留高于阈值的结果
                if (similarity >= minSimilarity) {
                    results.push({
                        video: video,
                        frame: frame,
                        similarity: similarity
                    });
                }
            }
        }

        // 按相似度降序排序
        results.sort((a, b) => b.similarity - a.similarity);

        // 返回 Top K 结果
        return results.slice(0, topK);
    }

    /**
     * 批量匹配（使用 setTimeout 避免阻塞UI）
     * @param {HTMLImageElement} imageElement - 图片元素
     * @param {Object} videoIndex - 视频索引
     * @returns {Promise<Array>} - 匹配结果
     */
    async matchAsync(imageElement, videoIndex) {
        // 提取特征
        const feature = await this.extractFeature(imageElement);

        // 使用 setTimeout 让出主线程，避免UI卡顿
        return new Promise((resolve) => {
            setTimeout(() => {
                const results = this.match(feature, videoIndex);
                resolve(results);
            }, 50);
        });
    }
}

// 导出类
export { ImageMatcher };
