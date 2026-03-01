import os

from ..config import config
from .factory import KnowledgeBaseFactory
from .implementations.dify import DifyKB
from .implementations.milvus import MilvusKB
from .manager import KnowledgeBaseManager
from .services.disabled_graph_service import DisabledGraphService
from .services.upload_graph_service import UploadGraphService
from src.utils import logger


def _env_enabled(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


LIGHTRAG_ENABLED = _env_enabled("YUXI_ENABLE_LIGHTRAG", default=True)
KNOWLEDGE_GRAPH_ENABLED = _env_enabled("YUXI_ENABLE_KNOWLEDGE_GRAPH", default=True)

# 注册知识库类型
KnowledgeBaseFactory.register("milvus", MilvusKB, {"description": "基于 Milvus 的生产级向量知识库，适合高性能部署"})
KnowledgeBaseFactory.register("dify", DifyKB, {"description": "连接 Dify Dataset 的只读检索知识库"})

if LIGHTRAG_ENABLED:
    from .implementations.lightrag import LightRagKB

    KnowledgeBaseFactory.register("lightrag", LightRagKB, {"description": "基于图检索的知识库，支持实体关系构建和复杂查询"})
else:
    logger.info("LightRAG feature disabled by YUXI_ENABLE_LIGHTRAG=false")

# 创建知识库管理器
work_dir = os.path.join(config.save_dir, "knowledge_base_data")
knowledge_base = KnowledgeBaseManager(work_dir)

# 创建图数据库实例
if KNOWLEDGE_GRAPH_ENABLED:
    try:
        graph_base = UploadGraphService()
    except Exception as e:
        logger.warning(f"Knowledge graph init failed, fallback to disabled mode: {e}")
        graph_base = DisabledGraphService(reason=f"知识图谱服务不可用: {e}")
else:
    graph_base = DisabledGraphService(reason="知识图谱功能已禁用（YUXI_ENABLE_KNOWLEDGE_GRAPH=false）")

# 向后兼容：让 GraphDatabase 指向 UploadGraphService
GraphDatabase = UploadGraphService if KNOWLEDGE_GRAPH_ENABLED else DisabledGraphService

__all__ = ["GraphDatabase", "UploadGraphService", "knowledge_base", "graph_base"]
