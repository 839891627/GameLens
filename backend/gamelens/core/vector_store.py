#!/usr/bin/env python3.12
"""
帧探·GameLens - FAISS 向量索引管理模块

提供 FAISS 向量索引的创建、加载、保存和搜索功能:
- IndexFlatL2: 精确搜索，适合 < 10万帧
- IndexIVFFlat: 近似搜索，适合 10万-100万帧
- IndexIVFPQ: 压缩存储，适合 > 100万帧
"""

import faiss
import numpy as np
import logging
from pathlib import Path
from typing import Tuple, List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# ==================== 配置 ====================
# 从 core/ 目录向上三级到 backend 目录
INDEX_DIR = Path(__file__).parent.parent.parent / "data"
INDEX_FILE = INDEX_DIR / "faiss_index.index"
ID_FILE = INDEX_DIR / "frame_ids.npy"  # 存储 frame_id 映射
DIMENSION = 1280  # MobileNetV2 特征维度
USE_COSINE_SIMILARITY = True  # 使用余弦相似度


# ==================== 异常类 ====================
class VectorStoreError(Exception):
    """向量存储异常"""
    pass


class IndexNotInitialized(VectorStoreError):
    """索引未初始化"""
    pass


class IndexNotFoundError(VectorStoreError):
    """索引文件不存在"""
    pass


# ==================== 向量存储类 ====================
class VectorStore:
    """FAISS 向量索引管理器

    支持多种索引类型:
    - IndexFlatL2: 精确 L2 距离搜索
    - IndexFlatIP: 精确内积搜索（余弦相似度，特征需归一化）
    - IndexIDMapIP: 带显式 ID 映射的内积索引（修复 ID 映射脆弱性）
    - IndexIVFFlat: 倒排索引，适合大规模数据
    - IndexIVFPQ: 乘积量化压缩
    """

    def __init__(
        self,
        dimension: int = DIMENSION,
        index_path: Optional[Path] = None,
        index_type: str = "IndexIDMapIP",
        use_cosine: bool = USE_COSINE_SIMILARITY
    ):
        """初始化向量存储

        Args:
            dimension: 向量维度
            index_path: 索引文件路径
            index_type: 索引类型 (IndexFlatL2, IndexFlatIP, IndexIDMapIP, IndexIVFFlat, IndexIVFPQ)
            use_cosine: 是否使用余弦相似度（自动归一化特征）
        """
        self.dimension = dimension
        self.index_path = index_path or INDEX_FILE
        self.id_path = ID_FILE  # frame_id 映射文件
        self.index_type = index_type
        self.use_cosine = use_cosine
        self.index: Optional[faiss.Index] = None
        self.frame_ids: List[int] = []  # 存储 frame_id 列表
        self.is_trained = False

    def create_index(self, index_type: Optional[str] = None) -> faiss.Index:
        """创建 FAISS 索引

        Args:
            index_type: 索引类型，如果为 None 则使用初始化时的类型

        Returns:
            创建的 FAISS 索引对象
        """
        index_type = index_type or self.index_type

        if index_type == "IndexFlatL2":
            # 精确搜索，L2 距离（兼容旧索引）
            self.index = faiss.IndexFlatL2(self.dimension)
            self.is_trained = True
            logger.info(f"创建 IndexFlatL2 索引，维度: {self.dimension}")

        elif index_type == "IndexFlatIP":
            # 精确搜索，内积（余弦相似度，特征需归一化）
            self.index = faiss.IndexFlatIP(self.dimension)
            self.is_trained = True
            logger.info(f"创建 IndexFlatIP 索引（余弦相似度），维度: {self.dimension}")

        elif index_type == "IndexIDMapIP":
            # 使用 IDMap 的内积索引（修复 ID 映射脆弱性）
            quantizer = faiss.IndexFlatIP(self.dimension)
            self.index = faiss.IndexIDMap(quantizer)
            self.is_trained = True
            logger.info(f"创建 IndexIDMapIP 索引（余弦相似度 + ID映射），维度: {self.dimension}")

        elif index_type == "IndexIVFFlat":
            # 倒排索引，需要训练
            nlist = 100  # 聚类中心数
            quantizer = faiss.IndexFlatL2(self.dimension)
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
            self.is_trained = False
            logger.info(f"创建 IndexIVFFlat 索引，聚类中心数: {nlist}")

        elif index_type == "IndexIVFPQ":
            # 乘积量化压缩
            nlist = 100
            m = 64  # 压缩维度（必须是维度的约数）
            quantizer = faiss.IndexFlatL2(self.dimension)
            self.index = faiss.IndexIVFPQ(quantizer, self.dimension, nlist, m, 8)
            self.is_trained = False
            logger.info(f"创建 IndexIVFPQ 索引，聚类中心数: {nlist}, 压缩维度: {m}")

        else:
            raise ValueError(f"不支持的索引类型: {index_type}")

        return self.index

    def load_index(self) -> bool:
        """从文件加载索引

        Returns:
            是否成功加载
        """
        if not self.index_path.exists():
            logger.warning(f"索引文件不存在: {self.index_path}")
            return False

        try:
            self.index = faiss.read_index(str(self.index_path))
            self.is_trained = True

            # 加载 frame_id 映射
            if self.id_path.exists():
                self.frame_ids = np.load(self.id_path).tolist()
                logger.info(f"加载 FAISS 索引: {self.index.ntotal} 个向量, {len(self.frame_ids)} 个 frame_id")
            else:
                logger.warning(f"frame_id 映射文件不存在: {self.id_path}，将使用索引位置映射")
                self.frame_ids = []

            return True

        except Exception as e:
            logger.error(f"加载索引失败: {e}")
            return False

    def save_index(self):
        """保存索引到文件"""
        if self.index is None:
            raise IndexNotInitialized("索引未初始化，无法保存")

        try:
            # 确保目录存在
            self.index_path.parent.mkdir(parents=True, exist_ok=True)

            # 保存索引
            faiss.write_index(self.index, str(self.index_path))

            # 保存 frame_id 映射
            if self.frame_ids:
                np.save(self.id_path, np.array(self.frame_ids))
                logger.info(f"保存 frame_id 映射: {len(self.frame_ids)} 个")

            file_size_mb = self.index_path.stat().st_size / (1024 * 1024)
            logger.info(f"保存 FAISS 索引: {self.index.ntotal} 个向量，文件大小: {file_size_mb:.2f} MB")

        except Exception as e:
            logger.error(f"保存索引失败: {e}")
            raise

    def add_vectors(self, vectors: np.ndarray, frame_ids: Optional[List[int]] = None) -> int:
        """添加向量到索引

        Args:
            vectors: 向量数组，形状 (n, dimension)
            frame_ids: 对应的 frame_id 列表，与 vectors 一一对应

        Returns:
            添加的向量数量
        """
        if self.index is None:
            self.create_index()

        # 验证输入
        if vectors.ndim != 2:
            raise ValueError(f"向量必须是 2D 数组，当前维度: {vectors.ndim}")

        if vectors.shape[1] != self.dimension:
            raise ValueError(
                f"向量维度不匹配，期望: {self.dimension}，实际: {vectors.shape[1]}"
            )

        # 归一化特征（余弦相似度）
        if self.use_cosine:
            # L2 归一化
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            norms[norms == 0] = 1  # 避免除零
            vectors = vectors / norms
            logger.debug(f"特征已归一化用于余弦相似度")

        # 检查是否需要训练（针对 IndexIVF）
        if isinstance(self.index, (faiss.IndexIVF, faiss.IndexIVFPQ)) and not self.is_trained:
            if vectors.shape[0] < 100:
                logger.warning("训练数据太少 (< 100)，建议使用 IndexFlatIP")
            logger.info(f"训练索引，使用 {vectors.shape[0]} 个向量")
            self.index.train(vectors.astype('float32'))
            self.is_trained = True

        # 添加向量
        if vectors.shape[0] == 0:
            logger.warning("尝试添加空向量数组，跳过")
            return 0

        # 使用 IDMap 添加向量（带显式 ID 映射）
        if isinstance(self.index, faiss.IndexIDMap):
            if frame_ids is None:
                raise ValueError("IndexIDMap 需要提供 frame_ids 参数")

            frame_ids_array = np.array(frame_ids, dtype=np.int64)
            n_added = self.index.add_with_ids(vectors.astype('float32'), frame_ids_array)
            self.frame_ids.extend(frame_ids)
        else:
            # 普通索引，只添加向量
            n_added = self.index.add(vectors.astype('float32'))
            # 如果提供了 frame_ids，记录下来（用于兼容）
            if frame_ids is not None:
                self.frame_ids.extend(frame_ids)

        logger.info(f"添加 {n_added} 个向量到索引，总数: {self.index.ntotal}")

        return n_added

    def search(
        self,
        query_vector: np.ndarray,
        k: int = 5,
        min_similarity: float = 0.0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """搜索最相似的 k 个向量

        Args:
            query_vector: 查询向量，形状 (dimension,) 或 (n, dimension)
            k: 返回结果数量
            min_similarity: 最低相似度阈值（余弦相似度），低于此值的结果会被过滤

        Returns:
            (distances, indices): 距离数组和索引数组
                - 如果使用余弦相似度：distances 为余弦相似度（越大越相似，范围 -1 到 1）
                - 如果使用 L2 距离：distances 为 L2 距离（越小越相似）
                - indices: 如果使用 IndexIDMap，返回实际的 frame_id；否则返回向量在索引中的位置

        Raises:
            IndexNotInitialized: 索引未初始化
        """
        if self.index is None:
            raise IndexNotInitialized("索引未初始化，请先调用 load_index() 或 create_index()")

        if self.index.ntotal == 0:
            raise IndexNotInitialized("索引为空，无法搜索")

        # 确保是 2D 数组
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)

        # 验证维度
        if query_vector.shape[1] != self.dimension:
            raise ValueError(
                f"查询向量维度不匹配，期望: {self.dimension}，实际: {query_vector.shape[1]}"
            )

        # 归一化查询向量（余弦相似度）
        if self.use_cosine:
            norm = np.linalg.norm(query_vector)
            if norm > 0:
                query_vector = query_vector / norm

        # 调整 k 值（不超过索引总数）
        k = min(k, self.index.ntotal)

        # 搜索
        distances, indices = self.index.search(query_vector.astype('float32'), k)

        # 过滤低于阈值的结果
        if min_similarity > 0:
            if self.use_cosine:
                # 余弦相似度：保留 > min_similarity 的结果
                mask = distances[0] >= min_similarity
            else:
                # L2 距离：需要转换为相似度
                similarities = self.distances_to_similarities(distances[0])
                mask = similarities >= min_similarity

            distances = distances[0][mask].reshape(1, -1)
            indices = indices[0][mask].reshape(1, -1)

        return distances[0], indices[0]

    def get_vector_count(self) -> int:
        """获取索引中的向量数量"""
        if self.index is None:
            return 0
        return self.index.ntotal

    def is_empty(self) -> bool:
        """检查索引是否为空"""
        return self.get_vector_count() == 0

    def clear_index(self):
        """清空索引"""
        if self.index is not None:
            self.index.reset()
            logger.info("索引已清空")

    def delete_index_file(self):
        """删除索引文件"""
        if self.index_path.exists():
            self.index_path.unlink()
            logger.info(f"索引文件已删除: {self.index_path}")
        if self.id_path.exists():
            self.id_path.unlink()
            logger.info(f"ID 映射文件已删除: {self.id_path}")

    def get_index_info(self) -> Dict[str, Any]:
        """获取索引信息"""
        return {
            'type': type(self.index).__name__ if self.index else None,
            'dimension': self.dimension,
            'total_vectors': self.get_vector_count(),
            'is_trained': self.is_trained,
            'index_path': str(self.index_path),
            'file_exists': self.index_path.exists(),
            'file_size_mb': self.index_path.stat().st_size / (1024 * 1024) if self.index_path.exists() else 0
        }

    def distance_to_similarity(self, distance: float) -> float:
        """将距离/内积转换为相似度分数

        对于使用余弦相似度的索引（IndexFlatIP, IndexIDMapIP）：
        - 内积值即为余弦相似度，范围 -1 到 1
        - 返回归一化后的 0-1 分数

        对于使用 L2 距离的索引（IndexFlatL2）：
        - L2 距离越小越相似
        - 使用归一化方法将距离转换为 0-1 的相似度分数

        Args:
            distance: FAISS 搜索返回的距离/内积值

        Returns:
            相似度分数 (0-1)，1 为完全相同
        """
        if self.use_cosine:
            # 余弦相似度：-1 到 1，映射到 0-1
            # 余弦相似度 1 = 完全相同，0 = 正交，-1 = 完全相反
            similarity = (distance + 1) / 2
            return float(max(0.0, min(1.0, similarity)))
        else:
            # L2 距离：越小越相似，映射到 0-1
            min_distance = 0    # 完全相同
            max_distance = 100  # 最大距离阈值（CLIP特征更紧凑）

            # 确保在合理范围内
            distance_clamped = max(min_distance, min(distance, max_distance))

            # 线性归一化：距离越小，相似度越高
            similarity = 1 - (distance_clamped - min_distance) / (max_distance - min_distance)

            return float(similarity)

    def distances_to_similarities(self, distances: np.ndarray) -> np.ndarray:
        """批量转换距离为相似度"""
        if self.use_cosine:
            # 余弦相似度：-1 到 1，映射到 0-1
            return (distances + 1) / 2
        else:
            # L2 距离映射
            min_distance = 0
            max_distance = 100

            distances_clamped = np.clip(distances, min_distance, max_distance)
            similarities = 1 - (distances_clamped - min_distance) / (max_distance - min_distance)

            return similarities


# ==================== 便捷函数 ====================
def create_default_store() -> VectorStore:
    """创建默认配置的向量存储"""
    return VectorStore()


def load_or_create_store() -> VectorStore:
    """加载或创建向量存储

    如果索引文件存在则加载，否则创建新的。
    同时校验索引与数据库的一致性。
    """
    from gamelens.core.database import db_exists, get_total_frames_count

    store = VectorStore()

    if store.index_path.exists():
        if store.load_index():
            logger.info("加载已有索引")

            # 校验索引与数据库的一致性
            if db_exists():
                db_frame_count = get_total_frames_count()
                faiss_vector_count = store.get_vector_count()

                if db_frame_count != faiss_vector_count:
                    logger.error(f"数据不一致警告:")
                    logger.error(f"  - 数据库帧数: {db_frame_count}")
                    logger.error(f"  - FAISS向量数: {faiss_vector_count}")
                    logger.error(f"  - 差异: {abs(db_frame_count - faiss_vector_count)}")
                    logger.error(f"⚠️ 这会导致匹配结果错误！请删除以下文件并重新构建索引:")
                    logger.error(f"  - {store.index_path}")
                    logger.error(f"  - {store.index_path.parent / 'video_frames.db'}")
                    raise IndexNotInitialized(
                        f"索引与数据库不一致！数据库帧数({db_frame_count}) != FAISS向量数({faiss_vector_count})。"
                        "请删除不一致的文件后重新运行索引构建。"
                    )
                else:
                    logger.info(f"✓ 数据一致性校验通过: {faiss_vector_count} 个帧/向量")
        else:
            logger.warning("加载索引失败，创建新索引")
            store.create_index()
    else:
        logger.info("索引文件不存在，创建新索引")
        store.create_index()

    return store


def index_exists() -> bool:
    """检查索引文件是否存在"""
    return INDEX_FILE.exists()


def get_index_size() -> int:
    """获取索引文件大小（字节）"""
    if index_exists():
        return INDEX_FILE.stat().st_size
    return 0


# ==================== 主函数 ====================
def main():
    """测试向量存储功能"""
    print("=" * 60)
    print("向量存储模块测试")
    print("=" * 60)
    print()

    # 创建向量存储
    print("1. 创建向量存储...")
    store = VectorStore(dimension=128)
    store.create_index("IndexFlatL2")

    # 生成测试向量
    print("\n2. 生成测试向量...")
    np.random.seed(42)
    test_vectors = np.random.random((100, 128)).astype('float32')
    print(f"   生成 {len(test_vectors)} 个测试向量")

    # 添加向量
    print("\n3. 添加向量到索引...")
    store.add_vectors(test_vectors)

    # 保存索引
    print("\n4. 保存索引...")
    store.save_index()

    # 搜索测试
    print("\n5. 测试搜索...")
    query = test_vectors[0]  # 使用第一个向量作为查询
    distances, indices = store.search(query, k=5)
    print(f"   查询结果:")
    for i, (dist, idx) in enumerate(zip(distances, indices)):
        similarity = store.distance_to_similarity(dist)
        print(f"   #{i+1}: 索引={idx}, 距离={dist:.4f}, 相似度={similarity:.4f}")

    # 索引信息
    print("\n6. 索引信息:")
    info = store.get_index_info()
    for key, value in info.items():
        print(f"   {key}: {value}")

    # 测试加载
    print("\n7. 测试重新加载...")
    new_store = VectorStore(dimension=128)
    if new_store.load_index():
        print(f"   ✓ 成功加载索引: {new_store.get_vector_count()} 个向量")

    print("\n✓ 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
