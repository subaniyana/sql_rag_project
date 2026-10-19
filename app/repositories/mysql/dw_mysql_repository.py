from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

class DwMySQLRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_columns_types(self, table_name:str):
        """
        根据表查询表中所有字段类型
        :param name:
        :return:
        """
        # 查询语句
        sql=f"show columns from {table_name}"
        result=await self.session.execute(text(sql))
        # 查询结果[row(Field=order_id,Type=v)]
        return {row.Field: row.Type for row in result.fetchall()}

    async def get_column_values(self, table_name:str, column_name:str,limit:int=10)->list[str]:
        """
        查询字段值
        :param table_name:
        :param column_name:
        :param limit:
        :return:
        """
        sql=f"select distinct {column_name} from {table_name} limit :limit"
        result=await self.session.execute(text(sql), {"limit": limit})
        return [row[0] for row in result.fetchall()]

    async def get_db_info(self):
        """
        查询数据库环境信息，版本、方言
        :return:
        """
        # 查询数据版本
        result = await self.session.execute(text("select version()"))
        # 解析结果
        version = result.scalar()

        # 查询数据方言
        dialect = self.session.get_bind().dialect.name
        return {"version": version, "dialect": dialect}

    async def validate_sql(self, sql:str):
        """
        使用explain进行校验
        :param sql:
        :return:
        """

        await self.session.execute(text("explain " + sql))

    async def execute_sql(self, sql)->list[dict]:
        """
        执行sql
        :param sql:
        :return:
        """
        result = await self.session.execute(text(sql))
        return [dict(row) for row in result.mappings().fetchall()]




