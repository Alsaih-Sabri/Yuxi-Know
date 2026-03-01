class DisabledGraphService:
    """禁用态图谱服务，占位实现。"""

    feature_enabled = False

    def __init__(self, reason: str = "知识图谱功能已禁用"):
        self.reason = reason

    def start(self):
        return None

    def close(self):
        return None

    def is_running(self):
        return False

    def get_graph_info(self, graph_name="neo4j"):
        return None

    def query_node(self, keyword, threshold=0.9, kgdb_name="neo4j", hops=2, max_entities=8, return_format="graph", **kwargs):
        if return_format == "triples":
            return {"triples": [], "message": self.reason}
        return {"nodes": [], "edges": [], "message": self.reason}

    async def add_embedding_to_nodes(self, node_names=None, kgdb_name="neo4j", batch_size=None):
        raise RuntimeError(self.reason)

    async def jsonl_file_add_entity(self, file_path, kgdb_name="neo4j", embed_model_name=None, batch_size=None):
        raise RuntimeError(self.reason)
