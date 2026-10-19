from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import  PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.models.qdrant.metric_info_qdrant import MetricInfoQdrant
from app.prompt.prompt_loader import load_prompt
from app.core.log import logger


async def recall_metrics(state:DataAgentState,runtime:Runtime[DataAgentContext]):
    """
    召回指标
    :param state:
    :param runtime:
    :return:
    """
    writer = runtime.stream_writer
    writer({"state": "召回指标"})

    embedding_client = runtime.context["embedding_client"]
    metric_qdrant_repository = runtime.context["metric_qdrant_repository"]
    keywords = state["keywords"]
    query = state["query"]
    try:
        #扩展关键字
        #构建提示词
        prompt = PromptTemplate(template=load_prompt("extend_keywords_for_metric_recall"),input_variables=["query"])
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
        retrievd_metric_map: dict[str, MetricInfoQdrant] = {}
        # 2.召回字段
        # 遍历列表召回
        for keyword in keywords:
            # 转换向量
            embedding = await embedding_client.aembed_documents(keyword)
            # 查询qdrant
            payloads = await metric_qdrant_repository.search(embedding)

            for payload in payloads:
                metric_id = payload["id"]
                if not metric_id in retrievd_metric_map:
                    retrievd_metric_map[metric_id] = payload

        retrieved_metrics = list(retrievd_metric_map.values())
        logger.info(f"召回指标字段列表成功：{[retrievd_metric_map.keys()]}")
        return {"retrieved_metrics": retrieved_metrics}
    except Exception as e:
        logger.error(f"召回指标字段错误{e}")
