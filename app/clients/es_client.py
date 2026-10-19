from typing import Optional

from elasticsearch import AsyncElasticsearch

from app.conf.app_config import ESConfig, app_config


class ElasticClient:
    def __init__(self,config:ESConfig):
        self.config = config
        self.client:Optional[AsyncElasticsearch]=None

    def _get_url(self):
        return f"http://{self.config.host}:{self.config.port}"
    def init(self):
        self.client = AsyncElasticsearch(hosts=[self._get_url()])
    async def close(self):
        await self.client.close()

es_client = ElasticClient(app_config.es)

if __name__ == '__main__':
    es_client.init()
    client = es_client.client
