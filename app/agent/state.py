from typing import TypedDict

from app.models.es.value_info_es import ValueInfoEs
from app.models.qdrant.column_info_qdrant import ColumnInfoQdrant
from app.models.qdrant.metric_info_qdrant import MetricInfoQdrant

# 日期信息封装实体
class DateInfoState(TypedDict):
    date: str
    weekday: str
    quarter: str


class DBInfoState(TypedDict):
    version: str
    dialect: str


class DataAgentState(TypedDict):
    """
     图的状态定义
     存储的数据：graph运行需要依赖和处理的数据
    """
    date_info: DateInfoState
    db_info: DBInfoState


# 列信息封装实体
class ColumnInfoState(TypedDict):
    name: str
    type: str
    role: str
    examples: list
    description: str
    alias: list[str]

# 表信息封装实体
class TableInfoState(TypedDict):
    name: str
    role: str
    description: str
    columns: list[ColumnInfoState]

# 指标信息封装实体
class MetricInfoState(TypedDict):
    name: str
    description: str
    relevant_columns: list[str]
    alias: list[str]


class DataAgentState(TypedDict):
    query: str #用户查询信息
    error: str #state是否出现错误
    sql: str
    keywords: list[str]
    metric_infos:list[MetricInfoState]
    table_infos: list[TableInfoState]
    date_info:DateInfoState
    db_info:DBInfoState
    retrieved_columns: list[ColumnInfoQdrant]
    retrieved_metrics: list[MetricInfoQdrant]
    retrieved_values: list[ValueInfoEs]
    table_infos: list[TableInfoState]