from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.agent.llm import llm
from app.prompt.prompt_loader import load_prompt
from app.core.log import logger
from app.models.qdrant.column_info_qdrant import ColumnInfoQdrant


async def recall_column(state:DataAgentState,runtime:Runtime[DataAgentContext]):
    """
    召回字段
    :param state:
    :param runtime:
    :return:
    """
    writer = runtime.stream_writer
    writer({"state": "召回字段"})

    embedding_client=runtime.context["embedding_client"]
    column_qdrant_repository=runtime.context["column_qdrant_repository"]
    keywords=state["keywords"]
    query=state["query"]
    try:
        #1.扩展关键词
        #构建提示词
        prompt=PromptTemplate(template=load_prompt("extend_keywords_for_column_recall.prompt"),validate_template=["query"])
        #构建结构转换器
        output_parser=JsonOutputParser()
        #构建执行链
        chain =prompt |llm | output_parser
        #执行链
        result=await chain.ainvoke({"query":query})
        #合并关键字列表
        keywords=set(keywords+result)
        logger.info(f"扩展后的关键词列表：{keywords}")

        #去重
        retrievd_column_map:dict[str,ColumnInfoQdrant]={}
        #2.召回字段
        #遍历列表召回
        for keyword in keywords:
            #转换向量
            embedding=await embedding_client.aembed_documents(keyword)
            #查询qdrant
            payloads=await column_qdrant_repository.search(embedding)

            for payload in payloads:
                column_id=payload["id"]
                if not column_id in retrievd_column_map:
                    retrievd_column_map[column_id]=payload

        retrieved_columns=list(retrievd_column_map.values())
        logger.info(f"召回的字段列表成功：{[retrievd_column_map.keys()]}")
        return {"retrieved_columns":retrieved_columns}
    except Exception as e:
        logger.error(f"召回字段错误{e}")

