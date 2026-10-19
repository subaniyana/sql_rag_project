import asyncio
from pathlib import Path

from app.clients.embedding_client import embedding_client_manager
from app.clients.es_client import es_client
from app.clients.mysql_client import meta_mysql_client, dw_mysql_client
from app.clients.qdrant_client import qdrant_client
from app.repositories.es.value_es_repository import ValueEsRepository
from app.repositories.mysql.dw_mysql_repository import DwMySQLRepository
from app.repositories.mysql.meta_mysql_repository import MetaKnowledgeRepositories
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
from app.services.meta_knowledge_service import MetaKnowledgeService


async def build_meta(file_path:Path):

        # 创建meta数据库连接
        dw_mysql_client.init()
        meta_mysql_client.init()
        qdrant_client.init()
        embedding_client_manager.init()
        es_client.init()
        async with meta_mysql_client.session_factory() as meta_session,dw_mysql_client.session_factory() as dw_session:
            # 创建数据库对象
            meta_mysql_repository = MetaKnowledgeRepositories(meta_session)
            dw_mysql_repository = DwMySQLRepository(dw_session)
            column_qdrant_repository = ColumnQdrantRepository(qdrant_client.client)
            value_es_repository = ValueEsRepository(es_client.client)
            metric_qdrant_repository = MetricQdrantRepository(qdrant_client.client)
            # 创建servise对象
            meta_mysql_service = MetaKnowledgeService(meta_mysql_repository=meta_mysql_repository,
                                                    dw_mysql_repository=dw_mysql_repository,
                                                    column_qdrant_repository=column_qdrant_repository,
                                                    embedding_client=embedding_client_manager.client,
                                                    value_es_repository=value_es_repository,
                                                    metric_qdrant_repository=metric_qdrant_repository)
            dw_mysql_service = DwMySQLRepository(dw_session)
            #调用servise函数
            await meta_mysql_service.build_meta(file_path)

        await  meta_mysql_client.close()
        await dw_mysql_client.close()




if __name__ == '__main__':
    from argparse import ArgumentParser
    # 创建一个命令行参数解析器对象
    parser = ArgumentParser(
        prog='data_agent',  # 程序名称，在帮助信息中显示
        description='用于自然语言统计处理sql数据库',  # 程序的简短描述
        epilog='请使用前阅读使用说明'  # 帮助信息底部的附加文本
    )

    # 添加一个可选参数，支持短选项 -c 和长选项 --count
    parser.add_argument('-c', '--config')

    # 解析命令行传入的所有参数，并将结果存入 args 对象
    args = parser.parse_args()
    file_path = Path(args.config)
    # 打印解析后的所有参数，用于调试或确认
    print(args)
    asyncio.run(build_meta(file_path))