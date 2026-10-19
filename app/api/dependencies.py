import uuid
from dataclasses import asdict
from pathlib import Path

from fastapi import Depends
from omegaconf import OmegaConf
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.embedding_client import embedding_client_manager
from app.clients.es_client import es_client
from app.clients.mysql_client import dw_mysql_client, meta_mysql_client
from app.clients.qdrant_client import qdrant_client
from app.conf.meta_config import MetaConfig
from app.core.log import logger
from app.models.es.value_info_es import ValueInfoEs
from app.models.mysql.column_info_mysql import ColumnInfoMySQL
from app.models.mysql.column_metric_mysql import ColumnMetricMySQL
from app.models.mysql.metric_info_mysql import MetricInfoMySQL
from app.models.mysql.table_info_mysql import TableInfoMySQL
from app.models.qdrant.column_info_qdrant import ColumnInfoQdrant
from app.repositories.es.value_es_repository import ValueEsRepository
from app.repositories.mysql.dw_mysql_repository import DwMySQLRepository
from app.repositories.mysql.meta_mysql_repository import MetaMysqlRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from app.services.query_servise import QueryServise
from app.models.qdrant.metric_info_qdrant import MetricInfoQdrant
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository





async def get_meta_session():
    # https://fastapi.org.cn/tutorial/dependencies/dependencies-with-yield/
    async with meta_mysql_client.session_factory() as session:
        yield session


async def get_dw_session():
    async with dw_mysql_client.session_factory() as session:
        yield session


async def get_embedding_client():
    return embedding_client_manager.client


async def get_column_qdrant_repository():
    return ColumnQdrantRepository(qdrant_client.client)


async def get_value_es_repository():
    return ValueEsRepository(es_client.client)


async def get_metric_qdrant_repository():
    return MetricQdrantRepository(qdrant_client.client)


async def get_meta_mysql_repository(session: AsyncSession = Depends(get_meta_session)):
    return MetaMysqlRepository(session)


async def get_dw_mysql_repository(session: AsyncSession = Depends(get_dw_session)):
    return DwMySQLRepository(session)

# 构建QueryService依赖项
async def get_query_service(
        embedding_client: HuggingFaceEndpointEmbeddings = Depends(get_embedding_client),
        column_qdrant_repository: ColumnQdrantRepository = Depends(get_column_qdrant_repository),
        value_es_repository: ValueEsRepository = Depends(get_value_es_repository),
        metric_qdrant_repository: MetricQdrantRepository = Depends(get_metric_qdrant_repository),
        meta_mysql_repository: MetaMysqlRepository = Depends(get_meta_mysql_repository),
        dw_mysql_repository: DwMySQLRepository = Depends(get_dw_mysql_repository),
) -> QueryServise:
    return QueryServise(
        embedding_client=embedding_client,
        column_qdrant_repository=column_qdrant_repository,
        value_es_repository=value_es_repository,
        metric_qdrant_repository=metric_qdrant_repository,
        meta_mysql_repository=meta_mysql_repository,
        dw_mysql_repository=dw_mysql_repository
    )