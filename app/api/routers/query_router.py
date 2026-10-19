from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, APIRouter
from starlette.responses import StreamingResponse

from app.api.dependencies import get_query_service
from app.clients import embedding_client
from app.core.context import request_id_ctx_var
from app.services.query_servise import QueryServise


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
from app.api.schemas.query_schema import QuerySchema
from app.models.qdrant.metric_info_qdrant import MetricInfoQdrant
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository

query_router = APIRouter()
# 定义POST接口/api/query
@query_router.post("/api/query")
async def query(query: QuerySchema,query_service: QueryServise = Depends(get_query_service)):
    # 调用服务处理查询，返回SSE流式响应
    return StreamingResponse(query_service.query(query.query), media_type="text/event-stream")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # FastApi启动器执行的初始化逻辑
    # 初始化客户端对象
    embedding_client_manager.init()
    qdrant_client.init()
    es_client.init()
    meta_mysql_client.init()
    dw_mysql_client.init()
    yield
    # FastApi结束后执行的释放资源逻辑
    # 关闭客户端
    await qdrant_client.close()
    await es_client.close()
    await meta_mysql_client.close()
    await dw_mysql_client.close()


# 创建FastAPI应用实例，并注册生命周期组件
app = FastAPI(lifespan=lifespan)
app.include_router(query_router)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    # 调用路径函数之前进行业务处理
    request_id_ctx_var.set(uuid.uuid4())
    # 调用路径函数
    response = await call_next(request)
    # 调用路径函数之后进行业务处理
    return response



