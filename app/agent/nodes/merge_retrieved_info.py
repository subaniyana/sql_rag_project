from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState, TableInfoState, ColumnInfoState, MetricInfoState
from app.core.log import logger
from app.models.es.value_info_es import ValueInfoEs
from app.models.mysql.column_info_mysql import ColumnInfoMySQL
from app.models.mysql.table_info_mysql import TableInfoMySQL
from app.models.qdrant.column_info_qdrant import ColumnInfoQdrant
from app.models.qdrant.metric_info_qdrant import MetricInfoQdrant


def _convert_column_info_from_mysql_to_qdrant(column_info:ColumnInfoMySQL):
    return ColumnInfoQdrant(
        id=column_info.id,
        name=column_info.name,
        type=column_info.type,
        table_id=column_info.table_id,
        description=column_info.description,
        alias=column_info.alias,
        role=column_info.role,
        examples=column_info.example,
    )


def _convert_column_info_from_qdrant_to_state(column:ColumnInfoQdrant)->ColumnInfoState:
    return ColumnInfoState(
        name=column["name"],
        type=column["type"],
        role=column["role"],
        examples=column["examples"],
        description=column["description"],
        alias=column["alias"],
    )


def _convert_metric_info_from_qdrant_to_state(retrieved_metric:MetricInfoQdrant)->MetricInfoState:
    return MetricInfoState(
        name=retrieved_metric["name"],
        description=retrieved_metric["description"],
        relevant_columns=retrieved_metric["relevant_columns"],
        alias=retrieved_metric["alias"],
    )



async def merge_retrieved_info(state:DataAgentState,runtime:Runtime[DataAgentContext]):
    """
    三路合并
    :param state:
    :param runtime:
    :return:
    """
    writer = runtime.stream_writer
    writer({"state": "召回字段"})

    try:
        embedding_client=runtime.context["embedding_client"]
        meta_mysql_repository=runtime.context["meta_mysql_repository"]
        keywords=state["keywords"]
        query=state["query"]
        table_infos:list[TableInfoState]=[]

        #1.对信息进行查漏补缺

        # 获得召回信息
        retrieved_columns: list[ColumnInfoQdrant]=state["retrieved_columns"]
        retrieved_metrics: list[MetricInfoQdrant]=state["retrieved_metrics"]
        retrieved_values: list[ValueInfoEs]=state["retrieved_values"]

        #转化字段信息类型去重{id:column}
        retrieved_columns_map={column["id"] : column for column in retrieved_columns}

        #补充指标中关联字段信息
        for metric in retrieved_metrics:
            relevant_columns_id:list[str]=metric["relevant_columns"]
            for relevant_column_id in relevant_columns_id:
                #判断字段是否已召回
                if relevant_column_id not in retrieved_columns:
                    #根据字段id获得字段信息
                    column_info:ColumnInfoMySQL=await meta_mysql_repository.get_column_by_id(relevant_column_id)
                    #转换类型
                    column_info_qdrant=_convert_column_info_from_mysql_to_qdrant(column_info)
                    #存储
                    retrieved_columns_map[relevant_column_id]=column_info_qdrant

        #字段取值处理
        for column_value in retrieved_values:
            column_id=column_value["column_id"]
            if column_id not in retrieved_columns_map:
                column_info:ColumnInfoMySQL=await meta_mysql_repository.get_column_by_id(column_id)
                column_info_qdrant=_convert_column_info_from_mysql_to_qdrant(column_info)
                retrieved_columns_map[column_id]=column_info_qdrant

            #处理值信息
            if column_value not in retrieved_columns_map[column_id]["examples"]:
                #存储值到相关列表
                retrieved_columns_map[column_id]["examples"].append(column_value)

            #定义表封装结构
            table_to_column_map:dict[str,list[ColumnInfoQdrant]]={}
            #遍历封装字段
            for column in retrieved_columns_map.values():
                table_id=column["table_id"]
                if table_id not in table_to_column_map:
                    table_to_column_map[table_id]=[]
                table_to_column_map[table_id].append(column)

            #添加当前相关表的主外键
            for table_id in table_to_column_map.keys():
                #根据id查询表的主外键
                key_columns:list[ColumnInfoQdrant]=await meta_mysql_repository.get_key_columns_by_table_id(table_id)
                #获得已有字段的id
                ids=[column["id"] for column in table_to_column_map[table_id]]
                #遍历存储主外键
                for key_column in key_columns:
                    column_id=key_column.id
                    if column_id not in ids:
                        table_to_column_map[table_id].append(_convert_column_info_from_mysql_to_qdrant(key_column))

            #转换表封装
            # 遍历字段分组容器
            for table_id, columns in table_to_column_map.items():
                # 根据表id查询表信息TableInfoMysql
                table: TableInfoMySQL = await meta_mysql_repository.get_table_info_by_id(table_id)
                # 转换字段数据 ColumnInfoQdrant-ColumnInfoStata
                columns = [_convert_column_info_from_qdrant_to_state(column) for column in columns]
                # 构建tableInfoStata
                table_info = TableInfoState(
                    name=table.name,
                    role=table.role,
                    description=table.description,
                    columns=columns
                )
                # 收集组装的表数据
                table_infos.append(table_info)

            # 处理指标信息
            metric_infos = [_convert_metric_info_from_qdrant_to_state(retrieved_metric) for retrieved_metric in
                            retrieved_metrics]
            # 返回封装数据到后面节点
            logger.info("合并召回信息完成")
            return {"table_infos": table_infos, "metric_infos": metric_infos}
    except Exception as e:
        logger.info("合并召回信息异常")
        raise

