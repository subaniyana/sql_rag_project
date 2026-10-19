from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.models.mysql.column_info_mysql import ColumnInfoMySQL
from app.models.mysql.column_metric_mysql import ColumnMetricMySQL
from app.models.mysql.metric_info_mysql import MetricInfoMySQL
from app.models.mysql.table_info_mysql import TableInfoMySQL


class MetaMysqlRepository:
    def __init__(self, session:AsyncSession):
        self.session = session

    async def save_table_infos(self, table_infos):
        """
        保存表信息到数据库
        :param table_infos:
        :return:
        """
        self.session.add_all(table_infos)

    async def save_column_infos(self, column_infos):
        """
        保存字段信息到数据库
        :param column_infos:
        :return:
        """
        self.session.add_all(column_infos)

    async def save_metric_infos(self, metric_infos:list[MetricInfoMySQL]):
        """
        保存指标列表
        :param metric_infos:
        :return:
        """
        self.session.add_all(metric_infos)



    async def save_column_metrics(self, column_metrics:list[ColumnMetricMySQL]):
        """
        保存字段指标信息
        :param column_metrics:
        :return:
        """
        self.session.add_all(column_metrics)

    async def get_column_by_id(self, column_id):
        """
        根据id获取字段信息
        :param relevant_column:
        :return:
        """
        return await self.session.get(ColumnInfoMySQL, column_id)

    async def get_key_columns_by_table_id(self, table_id)->list[ColumnInfoMySQL]:
        sql="""
            select * from column_info where table_id = :table_id and role in ('primary_key','foreign_key')
        """

        result= await self.session.execute(select(ColumnInfoMySQL).from_statement(text(sql)),{'table_id':table_id})
        return result.scalars().fetchall()

    async def get_table_info_by_id(self, table_id):
        """
        根据id获取表信息
        :param table_id:
        :return:
        """
        return await self.session.get(TableInfoMySQL, table_id)






