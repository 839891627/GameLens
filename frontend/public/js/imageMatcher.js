/**
 * 帧探·GameLens - 图像匹配模块（已弃用）
 *
 * 注意：此模块已弃用
 * 图像匹配功能已迁移到服务端，以提供更好的性能和更快的页面加载速度
 *
 * 如果您需要使用前端匹配功能（离线场景），请恢复旧版本的实现
 */

// 保留类定义以避免代码错误
class ImageMatcher {
    constructor() {
        console.warn('[ImageMatcher] 此模块已弃用，请使用服务端匹配 API');
    }

    async init() {
        console.warn('[ImageMatcher] 此模块已弃用，请使用服务端匹配 API');
    }

    async extractFeature() {
        console.warn('[ImageMatcher] 此模块已弃用，请使用服务端匹配 API');
        return new Float32Array(1280);
    }

    async matchAsync() {
        console.warn('[ImageMatcher] 此模块已弃用，请使用服务端匹配 API');
        return [];
    }
}

// 导出（如果需要）
export { ImageMatcher };
