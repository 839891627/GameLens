#!/usr/bin/env python3
"""测试 Flask 环境中的 CLIP 加载"""

import sys
import logging
from flask import Flask, request, jsonify

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 全局变量
clip_model = None
clip_preprocess = None
clip_loaded = False


@app.route('/test/load', methods=['POST'])
def test_load():
    """测试 CLIP 加载"""
    global clip_model, clip_preprocess, clip_loaded

    if clip_loaded:
        return jsonify({
            'success': True,
            'message': 'CLIP already loaded'
        })

    logger.info("开始加载 CLIP 模型...")
    try:
        import clip
        import torch

        device = "cpu"
        logger.info("调用 clip.load()...")
        clip_model, clip_preprocess = clip.load("ViT-B/32", device=device)
        clip_loaded = True

        logger.info("✓ CLIP 模型加载完成")

        return jsonify({
            'success': True,
            'message': 'CLIP loaded successfully',
            'model_type': str(type(clip_model)),
            'output_dim': clip_model.visual.output_dim
        })
    except Exception as e:
        logger.error(f"CLIP 加载失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/test/inference', methods=['POST'])
def test_inference():
    """测试 CLIP 推理"""
    if not clip_loaded:
        return jsonify({
            'success': False,
            'error': 'CLIP not loaded'
        }), 400

    try:
        import torch
        import numpy as np
        from PIL import Image

        # 创建测试图片
        test_image = Image.new('RGB', (224, 224), color='blue')

        # 预处理
        image_input = clip_preprocess(test_image).unsqueeze(0).to("cpu")

        # 提取特征
        with torch.no_grad():
            feature = clip_model.encode_image(image_input)

        feature_np = feature.cpu().numpy().flatten()

        return jsonify({
            'success': True,
            'feature_shape': list(feature_np.shape),
            'feature_dtype': str(feature_np.dtype)
        })
    except Exception as e:
        logger.error(f"推理失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/test/status', methods=['GET'])
def test_status():
    """检查状态"""
    return jsonify({
        'loaded': clip_loaded
    })


def main():
    print("=" * 60)
    print("Flask CLIP 测试服务器")
    print("=" * 60)
    print("启动服务器在 http://localhost:9999")
    print("测试命令:")
    print("  curl -X POST http://localhost:9999/test/load")
    print("  curl -X POST http://localhost:9999/test/inference")
    print("  curl http://localhost:9999/test/status")
    print("=" * 60)

    app.run(host='127.0.0.1', port=9999, debug=False, threaded=True)


if __name__ == '__main__':
    main()
