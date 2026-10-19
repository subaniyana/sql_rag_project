from qdrant_client import  AsyncQdrantClient
from qdrant_client.http.models import VectorParams, Distance, PointStruct

from app.conf.app_config import app_config


class MetricQdrantRepository:
    def __init__(self, qdrant_client: AsyncQdrantClient):
        self.collection_name = "metric_info"
        self.qdrant_client = qdrant_client

    async def ensure_collection(self):
        """
        确保存储字段向量的集合存在
        :param param:
        :return:
        """
        if not await self.qdrant_client.collection_exists(collection_name=self.collection_name):
            await self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=app_config.qdrant.embedding_size,
                                            distance=Distance.COSINE
                                            )
            )

    async def upsert_embedding(self, ids,embeddings, payloads,batch_size=10):
        """
        存储qd向量到数据库
        :param ids:
        :param points:
        :param payloads:
        :return:
        """
        # 合并[(id,embedding,payload),(id,embedding,payload),(id,embedding,payload)]
        zipped = list(zip(ids, embeddings, payloads))
        for i in range(0,len(zipped),batch_size):
            zipped_batch = zipped[i:i+batch_size]
            #遍历批次处理
            points = [PointStruct(
                id=id,
                vector=embeddings,
                payload=payload
            ) for id, embeddings, payload in zipped_batch]

            # 保存向量数据到qdrant
            await self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )

    async def search(self, embedding):
        """
        检索向量
        :param embedding:
        :return:
        """
        search_result = await self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=embedding,
            score_threshold=0.6,
        )
        return [point.payload for point in search_result.points]
