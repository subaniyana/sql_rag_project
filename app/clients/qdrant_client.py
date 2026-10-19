from typing import Optional
import random
import asyncio

from qdrant_client import AsyncQdrantClient,models
from app.conf.app_config import QdrantConfig, app_config


class QdrantClient:
    def __init__(self,config:QdrantConfig):
        self.client:Optional[AsyncQdrantClient]=None
        self.config=config
    def _get_url(self):
        return f"http://{self.config.host}:{self.config.port}"
    def init(self):
        self.client=AsyncQdrantClient(url=self._get_url())
    async def close(self):
        await self.clent.close()

qdrant_client=QdrantClient(app_config.qdrant)

if __name__ == '__main__':
    # 初始化Qdrant异步客户端
    qdrant_client.init()


    async def test():
        """测试Qdrant异步客户端核心功能：创建集合、插入向量、相似度检索"""
        # 获取初始化后的Qdrant异步客户端实例
        client = qdrant_client.client
        # 1. 检查集合是否存在，不存在则创建
        if not await client.collection_exists("my_collection"):
            await client.create_collection(
                collection_name="my_collection",  # 集合名称（类似数据库表名）
                # 向量字段配置：10维向量，使用余弦相似度计算
                vectors_config=models.VectorParams(size=app_config.qdrant.embedding_size, distance=models.Distance.COSINE),
            )

        # 2. 批量插入100个10维随机向量到集合中
        await client.upsert(
            collection_name="my_collection",
            # 列表推导式生成100个PointStruct对象（包含ID和随机向量）
            points=[
                models.PointStruct(
                    id=i,  # 向量唯一标识ID
                    vector=[random.random() for _ in range(10)]  # 生成10维随机向量
                )
                for i in range(100)
            ],
        )

        # 3. 向量相似度检索：查找最相似的10个向量
        res = await client.query_points(
            collection_name="my_collection",  # 检索的集合名称
            query=[random.random() for _ in range(10)],  # 10维随机查询向量（type: ignore忽略类型提示）
            limit=10,  # 返回最相似的前10个向量
            score_threshold=0.5  # 相似度得分阈值：只返回得分≥0.5的结果
        )
        # 打印检索结果中的向量点信息（包含ID、向量、得分等）
        print(res.points)


    # 运行异步测试函数（asyncio.run是执行异步函数的标准方式）
    asyncio.run(test())