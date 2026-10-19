import uuid
from dataclasses import asdict
from pathlib import Path

from omegaconf import OmegaConf

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

from app.models.qdrant.metric_info_qdrant import MetricInfoQdrant
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository


class MetaKnowledgeService:
    def __init__(self,
                 meta_mysql_repository:MetaMysqlRepository,
                 dw_mysql_repository:DwMySQLRepository,
                 column_qdrant_repository:ColumnQdrantRepository,
                 embedding_client:HuggingFaceEndpointEmbeddings,
                 value_es_repository:ValueEsRepository,
                 metric_qdrant_repository:MetricQdrantRepository,
                 ):
        self.meta_mysql_repository=meta_mysql_repository
        self.dw_mysql_repository=dw_mysql_repository
        self.column_qdrant_repository=column_qdrant_repository
        self.metric_qdrant_repository=metric_qdrant_repository
        self.embedding_client=embedding_client
        self.value_es_repository=value_es_repository

    async def build_meta(self, file_path:Path):

        #加载配置文件读取数据
        context=OmegaConf.load(file_path)
        schema=OmegaConf.structured(MetaConfig)
        meta_config:MetaConfig=OmegaConf.to_object(OmegaConf.merge(schema,context))
        logger.info("加载元数据完成")

        #保存表信息到meta数据库
        if meta_config.tables:

            #保存表信息
            column_infos:list[ColumnInfoMySQL]=await self._save_table_info_to_meta_db(meta_config)
            logger.info("保存表和字段信息到meta数据库完成")
            #为字段信息构建向量索引
            await self._save_column_info_to_dqrant(column_infos)
            logger.info("为字段信息构建向量索引完成")

            await self._save_value_info_to_es(column_infos,meta_config)
            logger.info("为字段值构建全文索引完成")

        #保存指标信息到metas数据库
        if meta_config.metrics:
            metric_infos:list[MetricInfoMySQL]=await self._save_metric_info_to_meta_db(meta_config)
            logger.info("保存指标信息到meta数据库")

            await self._save_metric_info_to_qdrant(metric_infos)
            logger.info("为指标信息创建向量索引完成")






            #为指标信息创建向量索引

    async def _save_table_info_to_meta_db(self, meta_config):
        all_column_infos: list[ColumnInfoMySQL] = []
        for table in meta_config.tables:
            logger.info(f"保存表{table.name}信息")
            table_infos: list[TableInfoMySQL] = []
            column_infos: list[ColumnInfoMySQL] = []
            table_infos.append(TableInfoMySQL(
                id=table.name,
                name=table.name,
                role=table.role,
                description=table.description
            ))
            column_types: dict[str, str] = await self.dw_mysql_repository.get_columns_types(table.name)
            for column in table.columns:
                column_info = ColumnInfoMySQL(
                    id=f"{table.name}.{column.name}",
                    name=column.name,
                    type=column_types.get(column.name),
                    role=column.role,
                    examples=[],
                    description=column.description,
                    alias=column.alias,
                    table_id=table.name
                )
                column_infos.append(column_info)

            # 保存到meta数据库

            async with self.meta_mysql_repository.session.begin():
                await self.meta_mysql_repository.save_table_infos(table_infos)
                await self.meta_mysql_repository.save_column_infos(column_infos)

            # 累积所有表的字段信息
            all_column_infos.extend(column_infos)
        return all_column_infos

    def _convert_column_info_to_payload(self, column_info:ColumnInfoMySQL):
        # ColumnInfoMySQL是SQLAlchemy模型而非dataclass，不能使用asdict()，手动按字段构建dict
        return ColumnInfoQdrant(
            **{key: getattr(column_info, key) for key in ColumnInfoQdrant.__annotations__}
        )

    async def _save_column_info_to_dqrant(self, column_infos):
        # 1.确保存储字段数据的向量存在
        await self.column_qdrant_repository.ensure_collection()

        points: list[dict] = []
        for column_info in column_infos:
            points.append({
                "id": uuid.uuid4(),
                "embedding_text": column_info.name,
                "payload": self._convert_column_info_to_payload(column_info)
            })
            points.append({
                "id": uuid.uuid4(),
                "embedding_text": column_info.description,
                "payload": self._convert_column_info_to_payload(column_info)
            })

            for alia in column_info.alias:
                points.append({
                    "id": uuid.uuid4(),
                    "embedding_text": alia,
                    "payload": self._convert_column_info_to_payload(column_info)
                })
        # 获得所有向量文本
        embedding_texts: list[str] = [point["embedding_text"] for point in points]

        # 批量转换向量并插入
        batch_size = 10
        embeddings: list[list[float]] = []
        for i in range(0, len(points), batch_size):
            # 获得批次向量文本
            batch_embedding_texts = embedding_texts[i:i + batch_size]
            # 转换向量
            batch_embeddings = await self.embedding_client.aembed_documents(batch_embedding_texts)
            # 收集批次向量
            embeddings.extend(batch_embeddings)

        # 保存向量数据到qdrant
        ids = [point["id"] for point in points]
        payloads = [point["payload"] for point in points]
        await self.column_qdrant_repository.upsert_embedding(ids=ids, embeddings=embeddings, payloads=payloads)

    async def _save_value_info_to_es(self, column_infos,meta_config):
        # 确保存储字段值存在
        await self.value_es_repository.insure_index()

        colunm2sync: dict[str, bool] = {}
        for table in meta_config.tables:
            for column in table.columns:
                colunm2sync[column.name] = column.sync
        for column_info in column_infos:
            sync = colunm2sync.get(column_info.name, True)
            if sync:
                column_values: list[str] = await self.dw_mysql_repository.get_column_values(
                    column_info.table_name, column_info.name, limit=1000
                )

                # 搜集所有字段值数据
                value_infos: list[ValueInfoEs] = []

                for column_value in column_values:
                    value_info_es = ValueInfoEs(
                        id=f"{column_info.id}.{column_value}",
                        value=column_value,
                        type=column_info.type,
                        column_id=column_info.id,
                        column_name=column_info.name,
                        table_id=column_info.table_id,
                        table_name=column_info.table_name
                    )
                    value_infos.append(value_info_es)
                # 保存到es
                await self.value_es_repository.insert_embedding(value_infos)

        pass

    async def _save_metric_info_to_meta_db(self, meta_config):
        metric_infos: list[MetricInfoMySQL] = []
        for metric in meta_config.metrics:
            metric_info_mysql = MetricInfoMySQL(
                id=metric.name,
                name=metric.name,
                description=metric.description,
                relevant_columns=metric.relevant_columns,
                alias=metric.alias,
            )
            metric_infos.append(metric_info_mysql)

            # 构建指标字段关联对象
            column_metrics: list[ColumnMetricMySQL] = []
            for relevant_column in metric.relevant_columns:
                column_metirc_mysql = ColumnMetricMySQL(
                    column_id=relevant_column,
                    metric_id=metric.name
                )
                column_metrics.append(column_metirc_mysql)

        # 保存指标信息
        async with self.meta_mysql_repository.session.begin():
            await self.meta_mysql_repository.save_metric_infos(metric_infos)
            await self.meta_mysql_repository.save_column_metrics(column_metrics)
        return metric_infos

    def _convert_metric_mysql_to_payload(self, metric_info:MetricInfoMySQL):
        return MetricInfoQdrant(
            id=metric_info.id,
            name=metric_info.name,
            description=metric_info.description,
            relevant_columns=metric_info.relevant_columns,
            alias=metric_info.alias,
        )

    async def _save_metric_info_to_qdrant(self, metric_infos):
        # 保存指标信息存在
        await self.metric_qdrant_repository.ensure_collection()

        # 定义列表收集向量保存对象
        points: list[dict] = []
        # 创建向量索引
        for metric_info in metric_infos:
            points.append(
                {
                    "id": uuid.uuid4(),
                    "embedding_text": metric_info.name,
                    "payload": self._convert_metric_mysql_to_payload(metric_info),
                }
            )
            points.append({
                "id": uuid.uuid4(),
                "embedding_text": metric_info.description,
                "payload": self._convert_metric_mysql_to_payload(metric_info),
            })
            for alia in metric_info.alias:
                points.append({
                    "id": uuid.uuid4(),
                    "embedding_text": alia,
                    "payload": self._convert_metric_mysql_to_payload(metric_info),
                })
        # 获得所有向量文本
        embedding_texts = [point["embedding_text"] for point in points]
        # 转换数据
        batch_size = 20
        embeddings: list[list[float]] = []
        for i in range(0, len(embedding_texts), batch_size):
            batch_embeddings_texts = embedding_texts[i:i + batch_size]
            batch_embeddings = await self.embedding_client.aembed_documents(batch_embeddings_texts)
            embeddings.extend(batch_embeddings)

        # 获得id
        ids = [point["id"] for point in points]
        # 获得负载
        payloads = [point["payload"] for point in points]
        # 保存向量索引到qdrant数据库
        await self.metric_qdrant_repository.upsert_embedding(ids, embeddings, payloads, batch_size)
        logger.info("保存指标构建向量索引")








