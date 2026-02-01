import asyncio
import os
import traceback
import uuid
from typing import Annotated, Any

import requests
from langchain.tools import tool
from langchain_core.tools import StructuredTool
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from src import config, graph_base, knowledge_base
from src.services.mcp_service import get_enabled_mcp_tools
from src.storage.minio import aupload_file_to_minio
from src.utils import logger

# Lazy initialization for TavilySearch (only when TAVILY_API_KEY is available)
_tavily_search_instance = None


def get_tavily_search():
    """Get TavilySearch instance lazily, only when API key is available."""
    global _tavily_search_instance
    if _tavily_search_instance is None and config.enable_web_search:
        from langchain_tavily import TavilySearch

        _tavily_search_instance = TavilySearch()
        _tavily_search_instance.metadata = {"name": "Tavily 网页搜索"}
    return _tavily_search_instance


@tool(name_or_callable="Calculator", description="Perform add, subtract, multiply, divide operations on two given numbers")
def calculator(a: float, b: float, operation: str) -> float:
    try:
        if operation == "add":
            return a + b
        elif operation == "subtract":
            return a - b
        elif operation == "multiply":
            return a * b
        elif operation == "divide":
            if b == 0:
                raise ZeroDivisionError("Divisor cannot be zero")
            return a / b
        else:
            raise ValueError(f"Unsupported operation: {operation}, only supports add, subtract, multiply, divide")
    except Exception as e:
        logger.error(f"Calculator error: {e}")
        raise


@tool
async def text_to_img_demo(text: str) -> str:
    """【测试用】使用模型生成图片， 会返回图片的URL"""

    url = "https://api.siliconflow.cn/v1/images/generations"

    payload = {
        "model": "Qwen/Qwen-Image",
        "prompt": text,
    }
    headers = {"Authorization": f"Bearer {os.getenv('SILICONFLOW_API_KEY')}", "Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response_json = response.json()
    except Exception as e:
        logger.error(f"Failed to generate image with: {e}")
        raise ValueError(f"Image generation failed: {e}")

    try:
        image_url = response_json["images"][0]["url"]
    except (KeyError, IndexError, TypeError) as e:
        logger.error(f"Failed to parse image URL from response: {e}, {response_json=}")
        raise ValueError(f"Image URL extraction failed: {e}")

    # 2. Upload to MinIO (Simplified)
    response = requests.get(image_url)
    file_data = response.content

    file_name = f"{uuid.uuid4()}.jpg"
    image_url = await aupload_file_to_minio(
        bucket_name="generated-images", file_name=file_name, data=file_data, file_extension="jpg"
    )
    logger.info(f"Image uploaded. URL: {image_url}")
    return image_url


@tool(name_or_callable="Human Approval Tool (Debug)", description="Request human approval tool for obtaining human confirmation before executing important operations.")
def get_approved_user_goal(
    operation_description: str,
) -> dict:
    """
    Request human approval before executing important operations.

    Args:
        operation_description: Description of the operation requiring approval, e.g., "Call knowledge base tool"
    Returns:
        dict: Dictionary containing approval result, format: {"approved": bool, "message": str}
    """
    # Build detailed interrupt info
    interrupt_info = {
        "question": "Approve the following operation?",
        "operation": operation_description,
    }

    # Trigger human approval
    is_approved = interrupt(interrupt_info)

    # Return approval result
    if is_approved:
        result = {
            "approved": True,
            "message": f"✅ Operation approved: {operation_description}",
        }
        print(f"✅ Human approval granted: {operation_description}")
    else:
        result = {
            "approved": False,
            "message": f"❌ Operation rejected: {operation_description}",
        }
        print(f"❌ Human approval rejected: {operation_description}")

    return result


KG_QUERY_DESCRIPTION = """
Use this tool to query triple information contained in the knowledge graph.
Keyword (query): Use keywords that may help answer the question for querying, do not directly use the user's raw input for querying.
"""


@tool(name_or_callable="Query Knowledge Graph", description=KG_QUERY_DESCRIPTION)
def query_knowledge_graph(query: Annotated[str, "The keyword to query knowledge graph."]) -> Any:
    """Use this tool to query triple information contained in the knowledge graph. Keyword (query): Use keywords that may help answer the question for querying, do not directly use the user's raw input for querying."""
    try:
        logger.debug(f"Querying knowledge graph with: {query}")
        result = graph_base.query_node(query, hops=2, return_format="triples")
        logger.debug(
            f"Knowledge graph query returned "
            f"{len(result.get('triples', [])) if isinstance(result, dict) else 'N/A'} triples"
        )
        return result
    except Exception as e:
        logger.error(f"Knowledge graph query error: {e}, {traceback.format_exc()}")
        return f"Knowledge graph query failed: {str(e)}"


class KnowledgeRetrieverModel(BaseModel):
    query_text: str = Field(
        description=(
            "Query keywords. When querying, use keywords that may help answer the question, do not directly use the user's raw input for querying."
        )
    )
    operation: str = Field(
        default="search",
        description=(
            "Operation type: 'search' means retrieve knowledge base content, 'get_mindmap' means get the knowledge base's mindmap structure. "
            "Use 'get_mindmap' when the user asks about the overall structure, file classification, or knowledge architecture of the knowledge base. "
            "Use 'search' when the user needs to query specific content."
        ),
    )


class CommonKnowledgeRetriever(KnowledgeRetrieverModel):
    """Common knowledge retriever model."""

    file_name: str = Field(description="Restrict to specific filename. When operation type is 'search', you can specify a filename, supports fuzzy matching")


def get_kb_based_tools(db_names: list[str] | None = None) -> list:
    """获取所有知识库基于的工具"""
    # 获取所有知识库
    kb_tools = []
    retrievers = knowledge_base.get_retrievers()
    if db_names is None:
        db_ids = None
    else:
        db_ids = [kb_id for kb_id, kb in retrievers.items() if kb["name"] in db_names]

    def _create_retriever_wrapper(db_id: str, retriever_info: dict[str, Any]):
        """创建检索器包装函数的工厂函数，避免闭包变量捕获问题"""

        async def async_retriever_wrapper(
            query_text: str, operation: str = "search", file_name: str | None = None
        ) -> Any:
            """异步检索器包装函数，支持检索和获取思维导图"""

            # Get mindmap
            if operation == "get_mindmap":
                try:
                    logger.debug(f"Getting mindmap for database {db_id}")

                    # Get mindmap from knowledge base metadata
                    if db_id not in knowledge_base.global_databases_meta:
                        return f"Knowledge base {retriever_info['name']} does not exist"

                    db_meta = knowledge_base.global_databases_meta[db_id]
                    mindmap_data = db_meta.get("mindmap")

                    if not mindmap_data:
                        return f"Knowledge base {retriever_info['name']} has not generated a mindmap yet."

                    # Convert mindmap data to text format for AI understanding
                    def mindmap_to_text(node, level=0):
                        """Recursively convert mindmap JSON to hierarchical text"""
                        indent = "  " * level
                        text = f"{indent}- {node.get('content', '')}\n"
                        for child in node.get("children", []):
                            text += mindmap_to_text(child, level + 1)
                        return text

                    mindmap_text = f"Mindmap structure of knowledge base {retriever_info['name']}:\n\n"
                    mindmap_text += mindmap_to_text(mindmap_data)

                    logger.debug(f"Successfully retrieved mindmap for {db_id}")
                    return mindmap_text

                except Exception as e:
                    logger.error(f"Error getting mindmap for {db_id}: {e}")
                    return f"Failed to get mindmap: {str(e)}"

            # Default: retrieve from knowledge base
            retriever = retriever_info["retriever"]
            try:
                logger.debug(f"Retrieving from database {db_id} with query: {query_text}")
                kwargs = {}
                if file_name:
                    kwargs["file_name"] = file_name

                if asyncio.iscoroutinefunction(retriever):
                    result = await retriever(query_text, **kwargs)
                else:
                    result = retriever(query_text, **kwargs)
                logger.debug(f"Retrieved {len(result) if isinstance(result, list) else 'N/A'} results from {db_id}")
                return result
            except Exception as e:
                logger.error(f"Error in retriever {db_id}: {e}")
                return f"Retrieval failed: {str(e)}"

        return async_retriever_wrapper

    for db_id, retrieve_info in retrievers.items():
        if db_ids is not None and db_id not in db_ids:
            continue

        try:
            # Build tool description
            description = (
                f"Multi-functional tool for {retrieve_info['name']} knowledge base.\n"
                f"Knowledge base description: {retrieve_info['description'] or 'No description.'}\n\n"
                f"Supported operations:\n"
                f"1. 'search' - Retrieve knowledge base content: Query relevant document fragments based on keywords\n"
                f"2. 'get_mindmap' - Get mindmap: View the overall structure and file classification of the knowledge base\n\n"
                f"Usage suggestions:\n"
                f"- When you need to query specific content, use operation='search'\n"
                f"- When you want to understand the knowledge base structure or file classification, use operation='get_mindmap'"
            )

            # 使用工厂函数创建检索器包装函数，避免闭包问题
            retriever_wrapper = _create_retriever_wrapper(db_id, retrieve_info)

            safename = retrieve_info["name"].replace(" ", "_")[:20]

            args_schema = KnowledgeRetrieverModel
            if retrieve_info["metadata"]["kb_type"] in ["milvus"]:
                args_schema = CommonKnowledgeRetriever

            # 使用 StructuredTool.from_function 创建异步工具
            tool = StructuredTool.from_function(
                coroutine=retriever_wrapper,
                name=safename,
                description=description,
                args_schema=args_schema,
                metadata=retrieve_info["metadata"] | {"tag": ["knowledgebase"]},
            )

            kb_tools.append(tool)
            # logger.debug(f"Successfully created tool {tool_id} for database {db_id}")

        except Exception as e:
            logger.error(f"Failed to create tool for database {db_id}: {e}, \n{traceback.format_exc()}")
            continue

    return kb_tools


def gen_tool_info(tools) -> list[dict[str, Any]]:
    """获取所有工具的信息（用于前端展示）"""
    tools_info = []

    try:
        # 获取注册的工具信息
        for tool_obj in tools:
            try:
                metadata = getattr(tool_obj, "metadata", {}) or {}
                info = {
                    "id": tool_obj.name,
                    "name": metadata.get("name", tool_obj.name),
                    "description": tool_obj.description,
                    "metadata": metadata,
                    "args": [],
                    # "is_async": is_async  # Include async information
                }

                if hasattr(tool_obj, "args_schema") and tool_obj.args_schema:
                    if isinstance(tool_obj.args_schema, dict):
                        schema = tool_obj.args_schema
                    else:
                        schema = tool_obj.args_schema.schema()

                    for arg_name, arg_info in schema.get("properties", {}).items():
                        info["args"].append(
                            {
                                "name": arg_name,
                                "type": arg_info.get("type", ""),
                                "description": arg_info.get("description", ""),
                            }
                        )

                tools_info.append(info)
                # logger.debug(f"Successfully processed tool info for {tool_obj.name}")

            except Exception as e:
                logger.error(
                    f"Failed to process tool {getattr(tool_obj, 'name', 'unknown')}: {e}\n{traceback.format_exc()}. "
                    f"Details: {dict(tool_obj.__dict__)}"
                )
                continue

    except Exception as e:
        logger.error(f"Failed to get tools info: {e}\n{traceback.format_exc()}")
        return []

    logger.info(f"Successfully extracted info for {len(tools_info)} tools")
    return tools_info


def get_buildin_tools() -> list:
    """注册静态工具"""
    static_tools = [
        query_knowledge_graph,
        get_approved_user_goal,
        calculator,
        text_to_img_demo,
    ]

    # subagents 工具
    from .subagents import calc_agent_tool

    static_tools.append(calc_agent_tool)

    # 检查是否启用网页搜索（即是否配置了 API_KEY）
    if config.enable_web_search:
        tavily_search = get_tavily_search()
        if tavily_search:
            static_tools.append(tavily_search)

    return static_tools


async def get_tools_from_context(context, extra_tools=None) -> list:
    """从上下文配置中获取工具列表"""
    # 1. 基础工具 (从 context.tools 中筛选)
    all_basic_tools = get_buildin_tools() + (extra_tools or [])
    selected_tools = []

    if context.tools:
        # 创建工具映射表
        tools_map = {t.name: t for t in all_basic_tools}
        for tool_name in context.tools:
            if tool_name in tools_map:
                selected_tools.append(tools_map[tool_name])

    # 2. 知识库工具
    if context.knowledges:
        kb_tools = get_kb_based_tools(db_names=context.knowledges)
        selected_tools.extend(kb_tools)

    # 3. MCP 工具（使用统一入口，自动过滤 disabled_tools）
    if context.mcps:
        for server_name in context.mcps:
            mcp_tools = await get_enabled_mcp_tools(server_name)
            selected_tools.extend(mcp_tools)

    return selected_tools
