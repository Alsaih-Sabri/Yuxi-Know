import asyncio
import os
import textwrap
import traceback
from urllib.parse import quote, unquote

import aiofiles
from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from starlette.responses import StreamingResponse

from server.services.tasker import TaskContext, tasker
from server.utils.auth_middleware import get_admin_user
from src import config, knowledge_base
from src.knowledge.indexing import SUPPORTED_FILE_EXTENSIONS, is_supported_file_extension, process_file_to_markdown
from src.knowledge.utils import calculate_content_hash
from src.models.embed import test_all_embedding_models_status, test_embedding_model_status
from src.models import select_model
from src.storage.db.models import User
from src.storage.minio.client import StorageError, aupload_file_to_minio, get_minio_client
from src.utils import logger

knowledge = APIRouter(prefix="/knowledge", tags=["knowledge"])


# =============================================================================
# === Helper Functions ===
# =============================================================================

async def _auto_generate_mindmap(db_id: str):
    """
    Auto-generate mindmap for a knowledge base in the background
    
    Args:
        db_id: Database ID
    """
    try:
        import json
        
        # Get database info
        db_info = knowledge_base.get_database_info(db_id)
        if not db_info:
            logger.warning(f"Database {db_id} not found for mindmap generation")
            return
        
        db_name = db_info.get("name", "Knowledge Base")
        all_files = db_info.get("files", {})
        
        # Get file list (limit to 20 files)
        file_ids = list(all_files.keys())[:20]
        if not file_ids:
            logger.info(f"No files to generate mindmap for database {db_id}")
            return
        
        # Collect file info
        files_info = []
        for file_id in file_ids:
            if file_id in all_files:
                file_info = all_files[file_id]
                files_info.append({
                    "filename": file_info.get("filename", ""),
                    "type": file_info.get("type", ""),
                })
        
        if not files_info:
            return
        
        # Build AI prompt
        system_prompt = """You are a professional knowledge organization assistant.

Your task is to analyze the provided file list and generate a clear hierarchical mindmap structure.

**IMPORTANT: Generate all category names in ENGLISH. Only keep original filenames as they are.**

**Core rule: Each filename can only appear once! No duplicates allowed!**

Requirements:
1. Clear hierarchical structure (2-4 levels)
2. Root node is the knowledge base name (translate to English if needed)
3. First level is main categories in ENGLISH (e.g., Technical Docs, Regulations, Data Resources)
4. Second level is subcategories in ENGLISH
5. **Leaf nodes must be specific filenames (keep original names)**
6. **Each filename can only appear once in the entire mindmap!**
7. If a file could belong to multiple categories, choose only the most appropriate one
8. Use appropriate emoji icons for better readability
9. Return JSON format following this structure:

```json
{
  "content": "Knowledge Base Name",
  "children": [
    {
      "content": "🎯 Main Category 1",
      "children": [
        {
          "content": "Subcategory 1.1",
          "children": [
            {"content": "file1.txt", "children": []},
            {"content": "file2.pdf", "children": []}
          ]
        }
      ]
    }
  ]
}
```

**Important constraints:**
- Each filename can only appear once in the entire JSON
- Don't classify by multiple dimensions causing file duplication
- Choose the most appropriate classification dimension
- Each leaf node's children must be an empty array []
- Category names should be concise and clear
- Use emojis to enhance visual effect"""
        
        files_text = "\n".join([f"- {f['filename']} ({f['type']})" for f in files_info])
        user_message = f"""Please generate a mindmap structure for knowledge base "{db_name}".

File list ({len(files_info)} files):
{files_text}

**Important reminder:**
1. This knowledge base has {len(files_info)} files
2. Each filename can only appear once in the mindmap
3. Don't let the same file appear in multiple categories
4. Choose the most appropriate unique category for each file
5. **Generate ALL category names in ENGLISH** (only keep original filenames unchanged)

Please generate a reasonable mindmap structure with English category names."""
        
        # Call AI to generate
        logger.info(f"Generating mindmap for {db_name} with {len(files_info)} files")
        
        model = select_model()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        response = await asyncio.to_thread(model.call, messages, stream=False)
        
        # Parse AI response
        content = response.content if hasattr(response, "content") else str(response)
        
        # Extract JSON from markdown code block
        if "```json" in content:
            json_start = content.find("```json") + 7
            json_end = content.find("```", json_start)
            content = content[json_start:json_end].strip()
        elif "```" in content:
            json_start = content.find("```") + 3
            json_end = content.find("```", json_start)
            content = content[json_start:json_end].strip()
        
        mindmap_data = json.loads(content)
        
        # Validate structure
        if not isinstance(mindmap_data, dict) or "content" not in mindmap_data:
            logger.error("Invalid mindmap structure generated")
            return
        
        # Save mindmap to knowledge base metadata
        async with knowledge_base._metadata_lock:
            if db_id in knowledge_base.global_databases_meta:
                knowledge_base.global_databases_meta[db_id]["mindmap"] = mindmap_data
                knowledge_base._save_global_metadata()
                logger.info(f"Auto-generated mindmap saved for database {db_id}")
        
    except Exception as e:
        logger.error(f"Failed to auto-generate mindmap for {db_id}: {e}")


# =============================================================================
# === API Endpoints ===
# =============================================================================

media_types = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".json": "application/json",
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".ppt": "application/vnd.ms-powerpoint",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".svg": "image/svg+xml",
    ".zip": "application/zip",
    ".rar": "application/x-rar-compressed",
    ".7z": "application/x-7z-compressed",
    ".tar": "application/x-tar",
    ".gz": "application/gzip",
    ".html": "text/html",
    ".htm": "text/html",
    ".xml": "text/xml",
    ".css": "text/css",
    ".js": "application/javascript",
    ".py": "text/x-python",
    ".java": "text/x-java-source",
    ".cpp": "text/x-c++src",
    ".c": "text/x-csrc",
    ".h": "text/x-chdr",
    ".hpp": "text/x-c++hdr",
}

# =============================================================================
# === 知识库管理分组 ===
# =============================================================================


@knowledge.get("/databases")
async def get_databases(current_user: User = Depends(get_admin_user)):
    """获取所有知识库"""
    try:
        database = knowledge_base.get_databases()
        return database
    except Exception as e:
        logger.error(f"获取数据库列表失败 {e}, {traceback.format_exc()}")
        return {"message": f"获取数据库列表失败 {e}", "databases": []}


@knowledge.post("/databases")
async def create_database(
    database_name: str = Body(...),
    description: str = Body(...),
    embed_model_name: str = Body(...),
    kb_type: str = Body("lightrag"),
    additional_params: dict = Body({}),
    llm_info: dict = Body(None),
    current_user: User = Depends(get_admin_user),
):
    """创建知识库"""
    logger.debug(
        f"Create database {database_name} with kb_type {kb_type}, "
        f"additional_params {additional_params}, llm_info {llm_info}, "
        f"embed_model_name {embed_model_name}"
    )
    try:
        # 先检查名称是否已存在
        if knowledge_base.database_name_exists(database_name):
            raise HTTPException(
                status_code=409,
                detail=f"知识库名称 '{database_name}' 已存在，请使用其他名称",
            )

        additional_params = {**(additional_params or {})}
        additional_params["auto_generate_questions"] = False  # 默认不生成问题

        def remove_reranker_config(kb: str, params: dict) -> None:
            """
            移除 reranker_config（已废弃）
            所有 reranker 参数现在通过 query_params.options 配置
            """
            reranker_cfg = params.get("reranker_config")
            if reranker_cfg:
                if kb == "milvus":
                    logger.info("reranker_config is deprecated, please use query_params.options instead")
                else:
                    logger.warning(f"{kb} does not support reranker, ignoring reranker_config")
                # 移除 reranker_config，不再保存
                params.pop("reranker_config", None)

        remove_reranker_config(kb_type, additional_params)

        embed_info = config.embed_model_names[embed_model_name]
        database_info = await knowledge_base.create_database(
            database_name, description, kb_type=kb_type, embed_info=embed_info, llm_info=llm_info, **additional_params
        )

        # 需要重新加载所有智能体，因为工具刷新了
        from src.agents import agent_manager

        await agent_manager.reload_all()

        return database_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建数据库失败 {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"创建数据库失败: {e}")


@knowledge.get("/databases/{db_id}")
async def get_database_info(db_id: str, current_user: User = Depends(get_admin_user)):
    """获取知识库详细信息"""
    database = knowledge_base.get_database_info(db_id)
    if database is None:
        raise HTTPException(status_code=404, detail="Database not found")
    return database


@knowledge.put("/databases/{db_id}")
async def update_database_info(
    db_id: str,
    name: str = Body(...),
    description: str = Body(...),
    llm_info: dict = Body(None),
    additional_params: dict = Body({}),  # Now accepts a dict
    current_user: User = Depends(get_admin_user),
):
    """更新知识库信息"""
    logger.debug(
        f"Update database {db_id} info: {name}, {description}, llm_info: {llm_info}, "
        f"additional_params: {additional_params}"
    )
    try:
        database = await knowledge_base.update_database(
            db_id,
            name,
            description,
            llm_info,
            additional_params=additional_params,  # Pass the dict to the manager
        )
        return {"message": "更新成功", "database": database}
    except Exception as e:
        logger.error(f"更新数据库失败 {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"更新数据库失败: {e}")


@knowledge.delete("/databases/{db_id}")
async def delete_database(db_id: str, current_user: User = Depends(get_admin_user)):
    """删除知识库"""
    logger.debug(f"Delete database {db_id}")
    try:
        await knowledge_base.delete_database(db_id)

        # 需要重新加载所有智能体，因为工具刷新了
        from src.agents import agent_manager

        await agent_manager.reload_all()

        return {"message": "删除成功"}
    except Exception as e:
        logger.error(f"删除数据库失败 {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"删除数据库失败: {e}")


@knowledge.get("/databases/{db_id}/export")
async def export_database(
    db_id: str,
    format: str = Query("csv", enum=["csv", "xlsx", "md", "txt"]),
    include_vectors: bool = Query(False, description="是否在导出中包含向量数据"),
    current_user: User = Depends(get_admin_user),
):
    """导出知识库数据"""
    logger.debug(f"Exporting database {db_id} with format {format}")
    try:
        file_path = await knowledge_base.export_data(db_id, format=format, include_vectors=include_vectors)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Exported file not found.")

        media_type = media_types.get(format, "application/octet-stream")

        return FileResponse(path=file_path, filename=os.path.basename(file_path), media_type=media_type)
    except NotImplementedError as e:
        logger.warning(f"A disabled feature was accessed: {e}")
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        logger.error(f"导出数据库失败 {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"导出数据库失败: {e}")


# =============================================================================
# === 知识库文档管理分组 ===
# =============================================================================


@knowledge.post("/databases/{db_id}/documents")
async def add_documents(
    db_id: str, items: list[str] = Body(...), params: dict = Body(...), current_user: User = Depends(get_admin_user)
):
    """添加文档到知识库（上传 -> 解析 -> 可选入库）"""
    logger.debug(f"Add documents for db_id {db_id}: {items} {params=}")

    content_type = params.get("content_type", "file")
    # 自动入库参数
    auto_index = params.get("auto_index", False)
    indexing_params = {
        "chunk_size": params.get("chunk_size", 1000),
        "chunk_overlap": params.get("chunk_overlap", 200),
        "qa_separator": params.get("qa_separator", ""),
    }

    # 禁止 URL 解析与入库
    if content_type == "url":
        raise HTTPException(status_code=400, detail="URL 文档上传与解析已禁用")

    # 安全检查：验证文件路径
    if content_type == "file":
        from src.knowledge.utils.kb_utils import validate_file_path

        for item in items:
            try:
                validate_file_path(item, db_id)
            except ValueError as e:
                raise HTTPException(status_code=403, detail=str(e))

    async def run_ingest(context: TaskContext):
        await context.set_message("任务初始化")
        await context.set_progress(5.0, "准备处理文档")

        total = len(items)
        processed_items = []

        # 存储第一阶段成功添加的文件记录 {item: (file_id, file_meta)}
        added_files = {}

        try:
            # ========== 第一阶段：批量添加文件记录 ==========
            await context.set_message("第一阶段：添加文件记录")
            for idx, item in enumerate(items, 1):
                await context.raise_if_cancelled()

                # 第一阶段进度：5% ~ 30%
                progress = 5.0 + (idx / total) * 25.0
                await context.set_progress(progress, f"[1/2] 添加记录 {idx}/{total}")

                try:
                    # 1. Add file record (UPLOADED)
                    file_meta = await knowledge_base.add_file_record(
                        db_id, item, params=params, operator_id=current_user.id
                    )
                    file_id = file_meta["file_id"]
                    added_files[item] = (file_id, file_meta)
                except Exception as add_error:
                    logger.error(f"添加文件记录失败 {item}: {add_error}")
                    error_type = "timeout" if isinstance(add_error, TimeoutError) else "add_failed"
                    error_msg = "添加超时" if isinstance(add_error, TimeoutError) else "添加记录失败"
                    processed_items.append(
                        {
                            "item": item,
                            "status": "failed",
                            "error": f"{error_msg}: {str(add_error)}",
                            "error_type": error_type,
                        }
                    )

            # ========== 第二阶段：批量解析文件 ==========
            await context.set_message("第二阶段：解析文件")
            parse_success_count = 0
            # 计算解析阶段的进度范围
            parse_progress_range = 30.0 if not auto_index else 25.0

            for idx, (item, (file_id, add_file_meta)) in enumerate(added_files.items(), 1):
                await context.raise_if_cancelled()

                # 第二阶段进度：25%~55% 或 30%~60%
                progress = parse_progress_range + (idx / len(added_files)) * 30.0
                await context.set_progress(progress, f"[2/2] 解析文件 {idx}/{len(added_files)}")

                try:
                    # 2. Parse file (PARSING -> PARSED)
                    file_meta = await knowledge_base.parse_file(db_id, file_id, operator_id=current_user.id)
                    processed_items.append(file_meta)
                    parse_success_count += 1
                except Exception as parse_error:
                    logger.error(f"解析文件失败 {item} (file_id={file_id}): {parse_error}")
                    error_type = "timeout" if isinstance(parse_error, TimeoutError) else "parse_failed"
                    error_msg = "解析超时" if isinstance(parse_error, TimeoutError) else "解析失败"
                    processed_items.append(
                        {
                            "item": item,
                            "status": "failed",
                            "error": f"{error_msg}: {str(parse_error)}",
                            "error_type": error_type,
                        }
                    )

            # ========== 第三阶段：自动入库 ==========
            if auto_index:
                await context.set_message("第三阶段：自动入库")
                parsed_files = [(item, data) for item, data in added_files.items() if data[1].get("status") == "parsed"]
                total_parsed = len(parsed_files)

                for idx, (item, (file_id, file_meta)) in enumerate(parsed_files, 1):
                    await context.raise_if_cancelled()

                    # 第三阶段进度：55%~95% 或 60%~95%
                    progress = 55.0 + (idx / total_parsed) * 40.0
                    await context.set_progress(progress, f"[3/3] 入库文件 {idx}/{total_parsed}")

                    try:
                        # 1. 更新入库参数
                        await knowledge_base.update_file_params(
                            db_id, file_id, indexing_params, operator_id=current_user.id
                        )
                        # 2. 执行入库
                        result = await knowledge_base.index_file(db_id, file_id, operator_id=current_user.id)
                        processed_items.append(result)
                    except Exception as index_error:
                        logger.error(f"自动入库失败 {item} (file_id={file_id}): {index_error}")
                        processed_items.append(
                            {
                                "item": item,
                                "status": "failed",
                                "error": f"入库失败: {str(index_error)}",
                                "error_type": "index_failed",
                            }
                        )

        except asyncio.CancelledError:
            await context.set_progress(100.0, "任务已取消")
            raise
        except Exception as task_error:
            # 处理整体任务的其他异常（如内存不足、网络错误等）
            logger.exception(f"Task processing failed: {task_error}")
            await context.set_progress(100.0, f"任务处理失败: {str(task_error)}")
            # 注意：不需要手动标记未处理的文件为失败，因为：
            # 1. 内层异常处理已记录所有处理过的文件（成功/失败）
            # 2. 未处理的文件没有进入 processed_items，前端会正确显示
            # 3. 用户可以重新提交未处理的文件
            raise

        item_type = "URL" if content_type == "url" else "文件"
        # Check for failed status (including ERROR_PARSING)
        failed_count = len([_p for _p in processed_items if "error" in _p or _p.get("status") == "failed"])

        summary = {
            "db_id": db_id,
            "item_type": item_type,
            "submitted": len(processed_items),
            "failed": failed_count,
        }
        message = f"{item_type}处理完成，失败 {failed_count} 个" if failed_count else f"{item_type}处理完成"
        await context.set_result(summary | {"items": processed_items})
        await context.set_progress(100.0, message)
        
        # Auto-generate mindmap if files were successfully processed
        success_count = len(processed_items) - failed_count
        if success_count > 0:
            try:
                logger.info(f"Auto-generating mindmap for database {db_id} after processing {success_count} files")
                asyncio.create_task(_auto_generate_mindmap(db_id))
            except Exception as mindmap_error:
                logger.warning(f"Failed to trigger auto mindmap generation: {mindmap_error}")
                # Don't fail the main task if mindmap generation fails
        
        return summary | {"items": processed_items}

    try:
        database = knowledge_base.get_database_info(db_id)
        task = await tasker.enqueue(
            name=f"知识库文档处理 ({database['name']})",
            task_type="knowledge_ingest",
            payload={
                "db_id": db_id,
                "items": items,
                "params": params,
                "content_type": content_type,
            },
            coroutine=run_ingest,
        )
        return {
            "message": "任务已提交，请在任务中心查看进度",
            "status": "queued",
            "task_id": task.id,
        }
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to enqueue {content_type}s: {e}, {traceback.format_exc()}")
        return {"message": f"Failed to enqueue task: {e}", "status": "failed"}


@knowledge.post("/databases/{db_id}/documents/parse")
async def parse_documents(db_id: str, file_ids: list[str] = Body(...), current_user: User = Depends(get_admin_user)):
    """手动触发文档解析"""
    logger.debug(f"Parse documents for db_id {db_id}: {file_ids}")

    async def run_parse(context: TaskContext):
        await context.set_message("任务初始化")
        await context.set_progress(5.0, "准备解析文档")

        total = len(file_ids)
        processed_items = []

        try:
            for idx, file_id in enumerate(file_ids, 1):
                await context.raise_if_cancelled()
                progress = 5.0 + (idx / total) * 90.0
                await context.set_progress(progress, f"正在解析第 {idx}/{total} 个文档")

                try:
                    result = await knowledge_base.parse_file(db_id, file_id, operator_id=current_user.id)
                    processed_items.append(result)
                except Exception as e:
                    logger.error(f"Parse failed for {file_id}: {e}")
                    processed_items.append({"file_id": file_id, "status": "failed", "error": str(e)})

        except Exception as e:
            logger.exception(f"Parse task failed: {e}")
            raise

        failed_count = len([p for p in processed_items if "error" in p])
        message = f"解析完成，失败 {failed_count} 个"
        await context.set_result({"items": processed_items})
        await context.set_progress(100.0, message)
        return {"items": processed_items}

    try:
        database = knowledge_base.get_database_info(db_id)
        task = await tasker.enqueue(
            name=f"文档解析 ({database['name']})",
            task_type="knowledge_parse",
            payload={"db_id": db_id, "file_ids": file_ids},
            coroutine=run_parse,
        )
        return {"message": "解析任务已提交", "status": "queued", "task_id": task.id}
    except Exception as e:
        return {"message": f"提交失败: {e}", "status": "failed"}


@knowledge.post("/databases/{db_id}/documents/index")
async def index_documents(
    db_id: str,
    file_ids: list[str] = Body(...),
    params: dict = Body({}),
    current_user: User = Depends(get_admin_user),
):
    """手动触发文档入库（Indexing），支持更新参数"""
    logger.debug(f"Index documents for db_id {db_id}: {file_ids} {params=}")

    # extract operator_id safely before background task
    operator_id = current_user.id

    async def run_index(context: TaskContext):
        await context.set_message("任务初始化")
        await context.set_progress(5.0, "准备入库文档")

        total = len(file_ids)
        processed_items = []

        # Track files that failed param update
        param_update_failed = set()

        try:
            # Update params if provided
            if params:
                for file_id in file_ids:
                    try:
                        await knowledge_base.update_file_params(db_id, file_id, params, operator_id=operator_id)
                    except Exception as e:
                        logger.error(f"Failed to update params for {file_id}: {e}")
                        param_update_failed.add(file_id)
                        processed_items.append(
                            {"file_id": file_id, "status": "failed", "error": f"参数更新失败: {str(e)}"}
                        )

            for idx, file_id in enumerate(file_ids, 1):
                await context.raise_if_cancelled()

                # Skip files that failed param update
                if file_id in param_update_failed:
                    logger.debug(f"Skipping {file_id} due to param update failure")
                    continue

                progress = 5.0 + (idx / total) * 90.0
                await context.set_progress(progress, f"正在入库第 {idx}/{total} 个文档")

                try:
                    result = await knowledge_base.index_file(db_id, file_id, operator_id=operator_id)
                    processed_items.append(result)
                except Exception as e:
                    logger.error(f"Index failed for {file_id}: {e}")
                    processed_items.append({"file_id": file_id, "status": "failed", "error": str(e)})

        except Exception as e:
            logger.exception(f"Index task failed: {e}")
            raise

        failed_count = len([p for p in processed_items if "error" in p])
        message = f"入库完成，失败 {failed_count} 个"
        await context.set_result({"items": processed_items})
        await context.set_progress(100.0, message)
        return {"items": processed_items}

    try:
        database = knowledge_base.get_database_info(db_id)
        task = await tasker.enqueue(
            name=f"文档入库 ({database['name']})",
            task_type="knowledge_index",
            payload={"db_id": db_id, "file_ids": file_ids, "params": params},
            coroutine=run_index,
        )
        return {"message": "入库任务已提交", "status": "queued", "task_id": task.id}
    except Exception as e:
        return {"message": f"提交失败: {e}", "status": "failed"}


@knowledge.get("/databases/{db_id}/documents/{doc_id}")
async def get_document_info(db_id: str, doc_id: str, current_user: User = Depends(get_admin_user)):
    """获取文档详细信息（包含基本信息和内容信息）"""
    logger.debug(f"GET document {doc_id} info in {db_id}")

    try:
        info = await knowledge_base.get_file_info(db_id, doc_id)
        return info
    except Exception as e:
        logger.error(f"Failed to get file info, {e}, {db_id=}, {doc_id=}, {traceback.format_exc()}")
        return {"message": "Failed to get file info", "status": "failed"}


@knowledge.get("/databases/{db_id}/documents/{doc_id}/basic")
async def get_document_basic_info(db_id: str, doc_id: str, current_user: User = Depends(get_admin_user)):
    """获取文档基本信息（仅元数据）"""
    logger.debug(f"GET document {doc_id} basic info in {db_id}")

    try:
        info = await knowledge_base.get_file_basic_info(db_id, doc_id)
        return info
    except Exception as e:
        logger.error(f"Failed to get file basic info, {e}, {db_id=}, {doc_id=}, {traceback.format_exc()}")
        return {"message": "Failed to get file basic info", "status": "failed"}


@knowledge.get("/databases/{db_id}/documents/{doc_id}/content")
async def get_document_content(db_id: str, doc_id: str, current_user: User = Depends(get_admin_user)):
    """获取文档内容信息（chunks和lines）"""
    logger.debug(f"GET document {doc_id} content in {db_id}")

    try:
        info = await knowledge_base.get_file_content(db_id, doc_id)
        return info
    except Exception as e:
        logger.error(f"Failed to get file content, {e}, {db_id=}, {doc_id=}, {traceback.format_exc()}")
        return {"message": "Failed to get file content", "status": "failed"}


@knowledge.delete("/databases/{db_id}/documents/{doc_id}")
async def delete_document(db_id: str, doc_id: str, current_user: User = Depends(get_admin_user)):
    """删除文档或文件夹"""
    logger.debug(f"DELETE document {doc_id} info in {db_id}")
    try:
        file_meta_info = await knowledge_base.get_file_basic_info(db_id, doc_id)

        # Check if it is a folder
        is_folder = file_meta_info.get("meta", {}).get("is_folder", False)
        if is_folder:
            await knowledge_base.delete_folder(db_id, doc_id)
            return {"message": "文件夹删除成功"}

        file_name = file_meta_info.get("meta", {}).get("filename")

        # 尝试从MinIO删除文件，如果失败（例如旧知识库没有MinIO实例），则忽略
        try:
            minio_client = get_minio_client()
            await minio_client.adelete_file("ref-" + db_id.replace("_", "-"), file_name)
            logger.debug(f"成功从MinIO删除文件: {file_name}")
        except Exception as minio_error:
            logger.warning(f"从MinIO删除文件失败（可能是旧知识库）: {minio_error}")

        # 无论MinIO删除是否成功，都继续从知识库删除
        await knowledge_base.delete_file(db_id, doc_id)
        return {"message": "删除成功"}
    except Exception as e:
        logger.error(f"删除文档失败 {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"删除文档失败: {e}")


@knowledge.get("/databases/{db_id}/documents/{doc_id}/download")
async def download_document(db_id: str, doc_id: str, request: Request, current_user: User = Depends(get_admin_user)):
    """下载原始文件 - 根据path类型选择本地或MinIO下载"""
    logger.debug(f"Download document {doc_id} from {db_id}")
    try:
        file_info = await knowledge_base.get_file_basic_info(db_id, doc_id)
        file_meta = file_info.get("meta", {})

        # 获取文件路径和文件名
        file_path = file_meta.get("path", "")
        filename = file_meta.get("filename", "file")
        logger.debug(f"File path from database: {file_path}")
        logger.debug(f"Original filename from database: {filename}")

        # 解码URL编码的文件名（如果有的话）
        try:
            decoded_filename = unquote(filename, encoding="utf-8")
            logger.debug(f"Decoded filename: {decoded_filename}")
        except Exception as e:
            logger.debug(f"Failed to decode filename {filename}: {e}")
            decoded_filename = filename  # 如果解码失败，使用原文件名

        _, ext = os.path.splitext(decoded_filename)
        media_type = media_types.get(ext.lower(), "application/octet-stream")

        # 根据path类型选择下载方式
        from src.knowledge.utils.kb_utils import is_minio_url

        if is_minio_url(file_path):
            # MinIO下载
            logger.debug(f"Downloading from MinIO: {file_path}")

            try:
                # 使用通用函数解析MinIO URL
                from src.knowledge.utils.kb_utils import parse_minio_url

                bucket_name, object_name = parse_minio_url(file_path)

                logger.debug(f"Parsed bucket_name: {bucket_name}, object_name: {object_name}")

                minio_client = get_minio_client()

                # 直接使用解析出的完整对象名称下载
                minio_response = await minio_client.adownload_response(
                    bucket_name=bucket_name,
                    object_name=object_name,
                )
                logger.debug(f"Successfully downloaded object: {object_name}")

            except Exception as e:
                logger.error(f"Failed to download MinIO file: {e}")
                raise StorageError(f"下载文件失败: {e}")

            # 创建流式生成器
            async def minio_stream():
                try:
                    while True:
                        chunk = await asyncio.to_thread(minio_response.read, 8192)
                        if not chunk:
                            break
                        yield chunk
                finally:
                    minio_response.close()
                    minio_response.release_conn()

            # 创建StreamingResponse
            response = StreamingResponse(
                minio_stream(),
                media_type=media_type,
            )
            # 正确处理中文文件名的HTTP头部设置
            try:
                # 尝试使用ASCII编码（适用于英文文件名）
                decoded_filename.encode("ascii")
                # 如果成功，直接使用简单格式
                response.headers["Content-Disposition"] = f'attachment; filename="{decoded_filename}"'
            except UnicodeEncodeError:
                # 如果包含非ASCII字符（如中文），使用RFC 2231格式
                encoded_filename = quote(decoded_filename.encode("utf-8"))
                response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{encoded_filename}"

            return response

        else:
            # 本地文件下载
            logger.debug(f"Downloading from local filesystem: {file_path}")

            if not os.path.exists(file_path):
                raise StorageError(f"文件不存在: {file_path}")

            # 获取文件大小
            file_size = os.path.getsize(file_path)

            # 创建文件流式生成器
            async def file_stream():
                async with aiofiles.open(file_path, "rb") as f:
                    while True:
                        chunk = await f.read(8192)
                        if not chunk:
                            break
                        yield chunk

            # 创建StreamingResponse
            response = StreamingResponse(
                file_stream(),
                media_type=media_type,
            )
            # 正确处理中文文件名的HTTP头部设置
            try:
                # 尝试使用ASCII编码（适用于英文文件名）
                decoded_filename.encode("ascii")
                # 如果成功，直接使用简单格式
                response.headers["Content-Disposition"] = f'attachment; filename="{decoded_filename}"'
                response.headers["Content-Length"] = str(file_size)
            except UnicodeEncodeError:
                # 如果包含非ASCII字符（如中文），使用RFC 2231格式
                encoded_filename = quote(decoded_filename.encode("utf-8"))
                response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{encoded_filename}"
                response.headers["Content-Length"] = str(file_size)

            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载文件失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"下载失败: {e}")


# =============================================================================
# === 知识库查询分组 ===
# =============================================================================


@knowledge.post("/databases/{db_id}/query")
async def query_knowledge_base(
    db_id: str, query: str = Body(...), meta: dict = Body(...), current_user: User = Depends(get_admin_user)
):
    """查询知识库"""
    logger.debug(f"Query knowledge base {db_id}: {query}")
    try:
        result = await knowledge_base.aquery(query, db_id=db_id, **meta)
        return {"result": result, "status": "success"}
    except Exception as e:
        logger.error(f"知识库查询失败 {e}, {traceback.format_exc()}")
        return {"message": f"知识库查询失败: {e}", "status": "failed"}


@knowledge.post("/databases/{db_id}/query-test")
async def query_test(
    db_id: str, query: str = Body(...), meta: dict = Body(...), current_user: User = Depends(get_admin_user)
):
    """测试查询知识库"""
    logger.debug(f"Query test in {db_id}: {query}")
    try:
        result = await knowledge_base.aquery(query, db_id=db_id, **meta)
        return result
    except Exception as e:
        logger.error(f"测试查询失败 {e}, {traceback.format_exc()}")
        return {"message": f"测试查询失败: {e}", "status": "failed"}


@knowledge.put("/databases/{db_id}/query-params")
async def update_knowledge_base_query_params(
    db_id: str, params: dict = Body(...), current_user: User = Depends(get_admin_user)
):
    """更新知识库查询参数配置"""
    try:
        # 获取知识库实例
        kb_instance = knowledge_base.get_kb(db_id)
        if not kb_instance:
            raise HTTPException(status_code=404, detail="Knowledge base not found")

        # 更新实例元数据中的查询参数
        async with knowledge_base._metadata_lock:
            # 确保 db_id 在实例的 databases_meta 中
            if db_id not in kb_instance.databases_meta:
                raise HTTPException(status_code=404, detail="Database not found in instance metadata")

            # 使用 setdefault 简化嵌套字典的初始化
            options = kb_instance.databases_meta[db_id].setdefault("query_params", {}).setdefault("options", {})
            options.update(params)
            kb_instance._save_metadata()

            logger.info(f"更新知识库 {db_id} 查询参数: {params}")

        return {"message": "success", "data": params}

    except Exception as e:
        logger.error(f"更新知识库查询参数失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新查询参数失败: {str(e)}")


@knowledge.get("/databases/{db_id}/query-params")
async def get_knowledge_base_query_params(db_id: str, current_user: User = Depends(get_admin_user)):
    """获取知识库类型特定的查询参数"""
    try:
        # 获取知识库实例
        kb_instance = knowledge_base._get_kb_for_database(db_id)

        # 调用知识库实例的方法获取配置
        params = kb_instance.get_query_params_config(
            db_id=db_id,
            reranker_names=config.reranker_names,  # 传递动态配置
        )

        # 获取用户保存的配置并合并（从实例 metadata 读取）
        saved_options = kb_instance._get_query_params(db_id)
        if saved_options:
            params = _merge_saved_options(params, saved_options)

        return {"params": params, "message": "success"}

    except Exception as e:
        logger.error(f"获取知识库查询参数失败 {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


def _merge_saved_options(params: dict, saved_options: dict) -> dict:
    """将用户保存的配置合并到默认配置中"""
    for option in params.get("options", []):
        key = option.get("key")
        if key in saved_options:
            option["default"] = saved_options[key]
    return params


# =============================================================================
# === AI生成示例问题 ===
# =============================================================================


SAMPLE_QUESTIONS_SYSTEM_PROMPT = """你是一个专业的知识库问答测试专家。

你的任务是根据知识库中的文件列表，生成有价值的测试问题。

要求：
1. 问题要具体、有针对性，基于文件名称和类型推测可能的内容
2. 问题要涵盖不同方面和难度
3. 问题要简洁明了，适合用于检索测试
4. 问题要多样化，包括事实查询、概念解释、操作指导等
5. 问题长度控制在10-30字之间
6. 直接返回JSON数组格式，不要其他说明

返回格式：
```json
{
  "questions": [
    "问题1？",
    "问题2？",
    "问题3？"
  ]
}
```
"""


@knowledge.post("/databases/{db_id}/sample-questions")
async def generate_sample_questions(
    db_id: str,
    request_body: dict = Body(...),
    current_user: User = Depends(get_admin_user),
):
    """
    AI生成针对知识库的测试问题

    Args:
        db_id: 知识库ID
        request_body: 请求体，包含 count 字段

    Returns:
        生成的问题列表
    """
    try:
        import json

        from src.models import select_model

        # 从请求体中提取参数
        count = request_body.get("count", 10)

        # 获取知识库信息
        db_info = knowledge_base.get_database_info(db_id)
        if not db_info:
            raise HTTPException(status_code=404, detail=f"知识库 {db_id} 不存在")

        db_name = db_info.get("name", "")
        all_files = db_info.get("files", {})

        if not all_files:
            raise HTTPException(status_code=400, detail="知识库中没有文件")

        # 收集文件信息
        files_info = []
        for file_id, file_info in all_files.items():
            files_info.append(
                {
                    "filename": file_info.get("filename", ""),
                    "type": file_info.get("type", ""),
                }
            )

        # 构建AI提示词
        system_prompt = SAMPLE_QUESTIONS_SYSTEM_PROMPT

        # 构建用户消息
        files_text = "\n".join(
            [
                f"- {f['filename']} ({f['type']})"
                for f in files_info[:20]  # 最多列举20个文件
            ]
        )

        file_count_text = f"（共{len(files_info)}个文件）" if len(files_info) > 20 else ""

        user_message = textwrap.dedent(f"""请为知识库"{db_name}"生成{count}个测试问题。

            知识库文件列表{file_count_text}：
            {files_text}

            请根据这些文件的名称和类型，生成{count}个有价值的测试问题。""")

        # 调用AI生成
        logger.info(f"开始生成知识库问题，知识库: {db_name}, 文件数量: {len(files_info)}, 问题数量: {count}")

        # 选择模型并调用
        model = select_model()
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]
        response = model.call(messages, stream=False)

        # 解析AI返回的JSON
        try:
            # 提取JSON内容
            content = response.content if hasattr(response, "content") else str(response)

            # 尝试从markdown代码块中提取JSON
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()

            questions_data = json.loads(content)
            questions = questions_data.get("questions", [])

            if not questions or not isinstance(questions, list):
                raise ValueError("AI返回的问题格式不正确")

            logger.info(f"成功生成{len(questions)}个问题")

            # 保存问题到知识库元数据
            try:
                async with knowledge_base._metadata_lock:
                    # 确保知识库元数据存在
                    if db_id not in knowledge_base.global_databases_meta:
                        knowledge_base.global_databases_meta[db_id] = {}
                    # 保存问题到对应知识库
                    knowledge_base.global_databases_meta[db_id]["sample_questions"] = questions
                    knowledge_base._save_global_metadata()
                    logger.info(f"成功保存 {len(questions)} 个问题到知识库 {db_id}")
            except Exception as save_error:
                logger.error(f"保存问题失败: {save_error}")

            return {
                "message": "success",
                "questions": questions,
                "count": len(questions),
                "db_id": db_id,
                "db_name": db_name,
            }

        except json.JSONDecodeError as e:
            logger.error(f"AI返回的JSON解析失败: {e}, 原始内容: {content}")
            raise HTTPException(status_code=500, detail=f"AI返回格式错误: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成知识库问题失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"生成问题失败: {str(e)}")


@knowledge.get("/databases/{db_id}/sample-questions")
async def get_sample_questions(db_id: str, current_user: User = Depends(get_admin_user)):
    """
    获取知识库的测试问题

    Args:
        db_id: 知识库ID

    Returns:
        问题列表
    """
    try:
        # 直接从全局元数据中读取
        if db_id not in knowledge_base.global_databases_meta:
            raise HTTPException(status_code=404, detail=f"知识库 {db_id} 不存在")

        db_meta = knowledge_base.global_databases_meta[db_id]
        questions = db_meta.get("sample_questions", [])

        return {
            "message": "success",
            "questions": questions,
            "count": len(questions),
            "db_id": db_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取知识库问题失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取问题失败: {str(e)}")


# =============================================================================
# === 文件管理分组 ===
# =============================================================================


@knowledge.post("/databases/{db_id}/folders")
async def create_folder(
    db_id: str,
    folder_name: str = Body(..., embed=True),
    parent_id: str | None = Body(None, embed=True),
    current_user: User = Depends(get_admin_user),
):
    """创建文件夹"""
    try:
        return await knowledge_base.create_folder(db_id, folder_name, parent_id)
    except Exception as e:
        logger.error(f"创建文件夹失败 {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@knowledge.put("/databases/{db_id}/documents/{doc_id}/move")
async def move_document(
    db_id: str,
    doc_id: str,
    new_parent_id: str | None = Body(..., embed=True),
    current_user: User = Depends(get_admin_user),
):
    """移动文件或文件夹"""
    logger.debug(f"Move document {doc_id} to {new_parent_id} in {db_id}")
    try:
        return await knowledge_base.move_file(db_id, doc_id, new_parent_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"移动文件失败 {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@knowledge.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    db_id: str | None = Query(None),
    allow_jsonl: bool = Query(False),
    current_user: User = Depends(get_admin_user),
):
    """上传文件"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No selected file")

    logger.debug(f"Received upload file with filename: {file.filename}")

    ext = os.path.splitext(file.filename)[1].lower()

    if ext == ".jsonl":
        if allow_jsonl is not True or db_id is not None:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
    elif not (is_supported_file_extension(file.filename) or ext == ".zip"):
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    basename, ext = os.path.splitext(file.filename)
    # 直接使用原始文件名（小写）
    filename = f"{basename}{ext}".lower()

    file_bytes = await file.read()

    content_hash = await calculate_content_hash(file_bytes)

    file_exists = await knowledge_base.file_existed_in_db(db_id, content_hash)
    if file_exists:
        raise HTTPException(
            status_code=409,
            detail="数据库中已经存在了相同内容文件，File with the same content already exists in this database",
        )

    # 直接上传到MinIO，添加时间戳区分版本
    import time

    timestamp = int(time.time() * 1000)
    minio_filename = f"{basename}_{timestamp}{ext}"

    # 生成符合MinIO规范的存储桶名称（将下划线替换为连字符）
    if db_id:
        bucket_name = f"ref-{db_id.replace('_', '-')}"
    else:
        bucket_name = "default-uploads"

    # 上传到MinIO
    minio_url = await aupload_file_to_minio(bucket_name, minio_filename, file_bytes, ext.lstrip("."))

    # 检测同名文件（基于原始文件名）
    same_name_files = await knowledge_base.get_same_name_files(db_id, filename)
    has_same_name = len(same_name_files) > 0

    return {
        "message": "File successfully uploaded",
        "file_path": minio_url,  # MinIO路径作为主要路径
        "minio_path": minio_url,  # MinIO路径
        "db_id": db_id,
        "content_hash": content_hash,
        "filename": filename,  # 原始文件名（小写）
        "original_filename": basename,  # 原始文件名（去掉后缀）
        "minio_filename": minio_filename,  # MinIO中的文件名（带时间戳）
        "bucket_name": bucket_name,  # MinIO存储桶名称
        "same_name_files": same_name_files,  # 同名文件列表
        "has_same_name": has_same_name,  # 是否包含同名文件标志
    }


@knowledge.get("/files/supported-types")
async def get_supported_file_types(current_user: User = Depends(get_admin_user)):
    """获取当前支持的文件类型"""
    return {"message": "success", "file_types": sorted(SUPPORTED_FILE_EXTENSIONS)}


@knowledge.post("/files/markdown")
async def mark_it_down(file: UploadFile = File(...), current_user: User = Depends(get_admin_user)):
    """调用 src.knowledge.indexing 下面的 process_file_to_markdown 解析为 markdown，参数是文件，需要管理员权限"""
    try:
        content = await file.read()
        markdown_content = await process_file_to_markdown(content)
        return {"markdown_content": markdown_content, "message": "success"}
    except Exception as e:
        logger.error(f"文件解析失败 {e}, {traceback.format_exc()}")
        return {"message": f"文件解析失败 {e}", "markdown_content": ""}


# =============================================================================
# === 知识库类型分组 ===
# =============================================================================


@knowledge.get("/types")
async def get_knowledge_base_types(current_user: User = Depends(get_admin_user)):
    """获取支持的知识库类型"""
    try:
        kb_types = knowledge_base.get_supported_kb_types()
        return {"kb_types": kb_types, "message": "success"}
    except Exception as e:
        logger.error(f"获取知识库类型失败 {e}, {traceback.format_exc()}")
        return {"message": f"获取知识库类型失败 {e}", "kb_types": {}}


@knowledge.get("/stats")
async def get_knowledge_base_statistics(current_user: User = Depends(get_admin_user)):
    """获取知识库统计信息"""
    try:
        stats = knowledge_base.get_statistics()
        return {"stats": stats, "message": "success"}
    except Exception as e:
        logger.error(f"获取知识库统计失败 {e}, {traceback.format_exc()}")
        return {"message": f"获取知识库统计失败 {e}", "stats": {}}


# =============================================================================
# === Embedding模型状态检查分组 ===
# =============================================================================


@knowledge.get("/embedding-models/{model_id}/status")
async def get_embedding_model_status(model_id: str, current_user: User = Depends(get_admin_user)):
    """获取指定embedding模型的状态"""
    logger.debug(f"Checking embedding model status: {model_id}")
    try:
        status = await test_embedding_model_status(model_id)
        return {"status": status, "message": "success"}
    except Exception as e:
        logger.error(f"获取embedding模型状态失败 {model_id}: {e}, {traceback.format_exc()}")
        return {
            "message": f"获取embedding模型状态失败: {e}",
            "status": {"model_id": model_id, "status": "error", "message": str(e)},
        }


@knowledge.get("/embedding-models/status")
async def get_all_embedding_models_status(current_user: User = Depends(get_admin_user)):
    """获取所有embedding模型的状态"""
    logger.debug("Checking all embedding models status")
    try:
        status = await test_all_embedding_models_status()
        return {"status": status, "message": "success"}
    except Exception as e:
        logger.error(f"获取所有embedding模型状态失败: {e}, {traceback.format_exc()}")
        return {"message": f"获取所有embedding模型状态失败: {e}", "status": {"models": {}, "total": 0, "available": 0}}


# =============================================================================
# === 知识库 AI 辅助功能分组 ===
# =============================================================================


@knowledge.post("/generate-description")
async def generate_description(
    name: str = Body(..., description="知识库名称"),
    current_description: str = Body("", description="当前描述（可选，用于优化）"),
    file_list: list[str] = Body([], description="文件列表"),
    current_user: User = Depends(get_admin_user),
):
    """使用 LLM 生成或优化知识库描述

    根据知识库名称和现有描述，使用 LLM 生成适合作为智能体工具描述的内容。
    """
    from src.models import select_model

    logger.debug(f"Generating description for knowledge base: {name}, files: {len(file_list)}")

    # 构建文件列表文本
    if file_list:
        # 限制文件数量，避免 prompt 过长
        display_files = file_list[:50]
        files_str = "\n".join([f"- {f}" for f in display_files])
        more_text = f"\n... (还有 {len(file_list) - 50} 个文件)" if len(file_list) > 50 else ""
        current_description += f"\n\n知识库包含的文件:\n{files_str}{more_text}"

    current_description = current_description or "暂无描述"

    # 构建提示词
    prompt = textwrap.dedent(f"""
        请帮我优化以下知识库的描述。

        知识库名称: {name}
        当前描述: {current_description}

        要求:
        1. 这个描述将作为智能体工具的描述使用
        2. 智能体会根据知识库的标题和描述来选择合适的工具
        3. 所以描述需要清晰、具体，说明该知识库包含什么内容、适合解答什么类型的问题
        4. 描述应该简洁有力，通常 2-4 句话即可
        5. 不要使用 Markdown 格式
        {"6. 请参考提供的文件列表来准确概括知识库内容" if file_list else ""}

        请直接输出优化后的描述，不要有任何前缀说明。
    """).strip()

    try:
        model = select_model()
        response = await asyncio.to_thread(model.call, prompt)
        description = response.content.strip()
        logger.debug(f"Generated description: {description}")
        return {"description": description, "status": "success"}
    except Exception as e:
        logger.error(f"生成描述失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"生成描述失败: {e}")
