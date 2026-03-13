#!/usr/bin/env python3
"""
CLIP 特征提取服务
独立的 Flask 服务，专门用于 CLIP 特征提取，避免与其他库冲突
"""

import io
import base64
from flask import Flask, request, jsonify
import torch
import clip
from PIL import Image
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 全局 CLIP 模型
model = None
preprocess = None
device = "cpu"


def load_model():
    """加载 CLIP 模型"""
    global model, preprocess
    if model is None:
        logger.info("加载 CLIP 模型...")
        model, preprocess = clip.load("ViT-B/32", device=device)
        logger.info("✓ CLIP 模型加载完成")
    return model is not None


@app.route('/extract', methods=['POST'])
def extract_feature():
    """提取图片特征"""
    try:
        # 确保模型已加载
        if not load_model():
            return jsonify({
                'success': False,
                'error': 'CLIP 模型加载失败'
            }), 500

        # 获取图片数据
        data = request.json
        image_data = data.get('image', '')

        if not image_data:
            return jsonify({
                'success': False,
                'error': '请提供图片数据'
            }), 400

        # 解码 Base64
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]

        image_bytes = base64.b64decode(image_data)

        # 加载图片
        image = Image.open(io.BytesIO(image_bytes))

        # 预处理
        image_input = preprocess(image).unsqueeze(0).to(device)

        # 提取特征
        with torch.no_grad():
            feature = model.encode_image(image_input)

        # 转换为 numpy 并展平
        feature_np = feature.cpu().numpy().flatten()

        logger.info(f"特征提取成功: {feature_np.shape}")

        return jsonify({
            'success': True,
            'feature': feature_np.tolist(),
            'shape': list(feature_np.shape),
            'dtype': str(feature_np.dtype)
        })

    except Exception as e:
        logger.error(f"特征提取失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'model_loaded': model is not None
    })


def main():
    print("=" * 60)
    print("CLIP 特征提取服务")
    print("=" * 60)
    print("启动服务在 http://localhost:9998")
    print("=" * 60)

    # 预加载模型
    load_model()

    app.run(host='127.0.0.1', port=9998, debug=False, threaded=False)


if __name__ == '__main__':
    main()
