import os

from ..config import config
from .factory import KnowledgeBaseFactory
from .implementations.lightrag import LightRagKB
from .implementations.milvus import MilvusKB
from .manager import KnowledgeBaseManager
from .services.upload_graph_service import UploadGraphService

# Register knowledge base types
KnowledgeBaseFactory.register("milvus", MilvusKB, {"description": "Production-grade vector knowledge base based on Milvus, suitable for high-performance deployment"})
KnowledgeBaseFactory.register("lightrag", LightRagKB, {"description": "Graph-based knowledge base supporting entity relationship construction and complex queries"})

# Create knowledge base manager
work_dir = os.path.join(config.save_dir, "knowledge_base_data")
knowledge_base = KnowledgeBaseManager(work_dir)

# Create graph database instance
graph_base = UploadGraphService()

# Backward compatibility: point GraphDatabase to UploadGraphService
GraphDatabase = UploadGraphService

__all__ = ["GraphDatabase", "UploadGraphService", "knowledge_base", "graph_base"]
