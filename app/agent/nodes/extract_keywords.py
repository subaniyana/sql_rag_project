from langgraph.runtime import Runtime
import jieba

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger


async def extract_keywords(state:DataAgentState,runtime:Runtime[DataAgentContext]):
    """
    关键字提取，根据用户问题使用jieba提取关键字，供后续节点使用
    :param state:
    :param runtime:
    :return:
    """
    try:
        writer=runtime.stream_writer
        writer({"state":"提取关键字"})
        query=state["query"]
        # 定义返回指定词性的元组
        allow_pos = (
            "n",  # 名词: 数据、服务器、表格
            "nr",  # 人名: 张三、李四
            "ns",  # 地名: 北京、上海
            "nt",  # 机构团体名: 政府、学校、某公司
            "nz",  # 其他专有名词: Unicode、哈希算法、诺贝尔奖
            "v",  # 动词: 运行、开发
            "vn",  # 名动词: 工作、研究
            "a",  # 形容词: 美丽、快速
            "an",  # 名形词: 难度、合法性、复杂度
            "eng",  # 英文
            "i",  # 成语
            "l",  # 常用固定短语
        )
        # 使用jieba从用户的查询信息中提取关键，基于TF-IDF算法实现
        keywords: list[str] = jieba.analyse.extract_tags(query, allowPOS=allow_pos)
        # 为了防止分词后缺乏语义理解，将原问题加入到关键字中
        keywords=list(set(keywords+[query]))
        logger.info(f"关键字:{keywords}")
        return {"keywords":keywords}
    except Exception as e:
        logger.error(f"节点extract_keywords错误关键字抽取失败{e}")
        raise

