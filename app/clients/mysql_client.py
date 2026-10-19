from typing import Optional

from sqlalchemy import text
import asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession, async_sessionmaker

from app.conf.app_config import app_config,DBConfig

class MySQLClient:
    def __init__(self,config:DBConfig):
        self.db_config = config
        self.engine:Optional[AsyncEngine] = None
        self.session_factory= None

    def _get_url(self):
        return f"mysql+asyncmy://{self.db_config.user}:{self.db_config.password}@{self.db_config.host}:{self.db_config.port}/{self.db_config.database}?charset=utf8mb4"

    def init(self):
        self.engine = create_async_engine(self._get_url(),pool_size=10,pool_pre_ping=True)
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
            autoflush=True,
            autobegin=True,

        )

    async def close(self):
        await self.engine.dispose()

dw_mysql_client = MySQLClient(app_config.db_dw)
meta_mysql_client = MySQLClient(app_config.db_meta)

if __name__ == '__main__':
    dw_mysql_client.init()


    async def test():
        #autoflush自动刷新，autobegin自动开启事务，expire_on_commit为true时，查询与修改结果会自动缓存，下次查询会结果为最新
        async with dw_mysql_client.session_factory() as session:
            # 执行sql查询
            result = await session.execute(text("select * from fact_order limit 10"))
            # 提取查询结果rows对象结构如：[(),(),()]
            rows = result.fetchall()
            # 提取查询结果封装成字典结构如：[{},{},{}]
            rows = result.mappings().fetchall()
            # 输出返回结果类型
            print(type(rows[0]))
            # 输出首行数据
            print(rows[0])


    asyncio.run(test())
