from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.models.es.value_info_es import ValueInfoEs
from app.prompt.prompt_loader import load_prompt


async def recall_value(state:DataAgentState,runtime:Runtime[DataAgentContext]):
    """
    召回值
    :param state:
    :param runtime:
    :return:
    """
    writer = runtime.stream_writer
    writer({"state": "召回字段取值"})


    embedding_client = runtime.context["embedding_client"]
    value_es_repository= runtime.context["value_es_repository"]
    keywords = state["keywords"]
    query = state["query"]
    try:
        # 扩展关键字
        # 构建提示词
        prompt = PromptTemplate(template=load_prompt("extend_keywords_for_value_recall"), input_variables=["query"])
        # 构建结构转换器
        output_parser = JsonOutputParser()
        # 构建执行链
        chain = prompt | llm | output_parser
        # 执行链
        result = await chain.ainvoke({"query": query})
        # 合并关键字列表
        keywords = set(keywords + result)
        logger.info(f"扩展后的关键词列表：{keywords}")

        # 去重
        retrieved_value_map: dict[str, ValueInfoEs] = {}
        # 2.召回字段
        # 遍历列表召回
        for keyword in keywords:

            # 查询es
            es_values = await value_es_repository.search(keyword)

            for es_value in es_values:
                value_id = es_value["id"]
                if not value_id in retrieved_value_map:
                    retrieved_value_map[value_id] = es_value

        retrieved_values = list(retrieved_value_map.values())
        logger.info(f"召回字段取值成功：{[retrieved_value_map.keys()]}")
        return {"retrieved_values": retrieved_values}
    except Exception as e:
        logger.error(f"召回字段取值错误{e}")
        raise
