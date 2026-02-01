import hashlib
import os
import time
import traceback
from pathlib import Path

import aiofiles
from langchain_text_splitters import MarkdownTextSplitter

from src import config
from src.config.static.models import EmbedModelInfo
from src.utils import hashstr, logger
from src.utils.datetime_utils import utc_isoformat


def validate_file_path(file_path: str, db_id: str = None) -> str:
    """
    Validate file path security to prevent path traversal attacks - supports local files and MinIO URLs

    Args:
        file_path: File path or MinIO URL to validate
        db_id: Database ID for getting knowledge base specific upload directory

    Returns:
        str: Normalized safe path

    Raises:
        ValueError: If path is unsafe
    """
    try:
        # Detect if it's a MinIO URL, if so return directly (skip path traversal check)
        if is_minio_url(file_path):
            logger.debug(f"MinIO URL detected, skipping path validation: {file_path}")
            return file_path

        # Normalize path (only for local files)
        normalized_path = os.path.abspath(os.path.realpath(file_path))

        # Get allowed root directories
        from src.knowledge import knowledge_base

        allowed_dirs = [
            os.path.abspath(os.path.realpath(config.save_dir)),
        ]

        # If db_id is specified, add knowledge base specific upload directory
        if db_id:
            try:
                allowed_dirs.append(os.path.abspath(os.path.realpath(knowledge_base.get_db_upload_path(db_id))))
            except Exception:
                # If unable to get db path, use general upload directory
                allowed_dirs.append(
                    os.path.abspath(os.path.realpath(os.path.join(config.save_dir, "database", "uploads")))
                )

        # Check if path is within allowed directories
        is_safe = False
        for allowed_dir in allowed_dirs:
            try:
                if normalized_path.startswith(allowed_dir):
                    is_safe = True
                    break
            except Exception:
                continue

        if not is_safe:
            logger.warning(f"Path traversal attempt detected: {file_path} (normalized: {normalized_path})")
            raise ValueError(f"Access denied: Invalid file path: {file_path}")

        return normalized_path

    except Exception as e:
        logger.error(f"Path validation failed for {file_path}: {e}")
        raise ValueError(f"Invalid file path: {file_path}")


def _unescape_separator(separator: str | None) -> str | None:
    """Convert literal escape characters from frontend to actual characters

    Example: "\\n\\n\\n" -> "\n\n\n"
    """
    if not separator:
        return None

    # Handle common escape sequences
    separator = separator.replace("\\n", "\n")
    separator = separator.replace("\\r", "\r")
    separator = separator.replace("\\t", "\t")
    separator = separator.replace("\\\\", "\\")

    return separator


def split_text_into_chunks(text: str, file_id: str, filename: str, params: dict = {}) -> list[dict]:
    """
    Split text into chunks using LangChain's MarkdownTextSplitter for intelligent splitting
    """
    chunks = []
    chunk_size = params.get("chunk_size", 1000)
    chunk_overlap = params.get("chunk_overlap", 200)

    # Get separator and convert to actual characters
    separator = params.get("qa_separator")
    separator = _unescape_separator(separator)

    # Backward compatibility: if old config set use_qa_split=True but no separator specified, use default separator
    use_qa_split = params.get("use_qa_split", False)
    if use_qa_split and not separator:
        separator = "\n\n\n"
        logger.debug("Enabled backward compatibility mode: use_qa_split=True, using default separator \\n\\n\\n")

    # Use MarkdownTextSplitter for intelligent splitting
    # MarkdownTextSplitter attempts to split along Markdown format headers
    text_splitter = MarkdownTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    # If separator is set, pre-split then process with current splitting logic
    if separator:
        # Convert separator to visual format (newlines displayed as \n)
        separator_display = separator.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
        logger.debug(f"Enabled pre-split mode, using separator: '{separator_display}'")
        pre_chunks = text.split(separator)
        text_chunks = []
        for pre_chunk in pre_chunks:
            if pre_chunk.strip():
                text_chunks.extend(text_splitter.split_text(pre_chunk))
    else:
        text_chunks = text_splitter.split_text(text)

    # Convert to standard format
    for chunk_index, chunk_content in enumerate(text_chunks):
        if chunk_content.strip():  # Skip empty chunks
            chunks.append(
                {
                    "id": f"{file_id}_chunk_{chunk_index}",
                    "content": chunk_content,  # .strip(),
                    "file_id": file_id,
                    "filename": filename,
                    "chunk_index": chunk_index,
                    "source": filename,
                    "chunk_id": f"{file_id}_chunk_{chunk_index}",
                }
            )

    logger.debug(f"Successfully split text into {len(chunks)} chunks using MarkdownTextSplitter")
    return chunks


async def calculate_content_hash(data: bytes | bytearray | str | os.PathLike[str] | Path) -> str:
    """
    Calculate SHA-256 hash of file content.

    Args:
        data: Binary data of file content or file path

    Returns:
        str: Hexadecimal hash value
    """
    sha256 = hashlib.sha256()

    if isinstance(data, (bytes, bytearray)):
        sha256.update(data)
        return sha256.hexdigest()

    if isinstance(data, (str, os.PathLike, Path)):
        path = Path(data)
        async with aiofiles.open(path, "rb") as file_handle:
            chunk = await file_handle.read(8192)
            while chunk:
                sha256.update(chunk)
                chunk = await file_handle.read(8192)

        return sha256.hexdigest()

    # Theoretically won't reach here, but kept as defensive programming
    raise TypeError(f"Unsupported data type for hashing: {type(data)!r}")  # type: ignore[unreachable]


async def prepare_item_metadata(item: str, content_type: str, db_id: str, params: dict | None = None) -> dict:
    """
    Prepare metadata for file or URL - supports local files and MinIO files

    Args:
        item: File path or MinIO URL
        content_type: Content type ("file" or "url")
        db_id: Database ID
        params: Processing parameters, optional
    """
    if content_type == "file":
        # Detect if it's a MinIO URL or local file path
        if is_minio_url(item):
            # MinIO file processing
            logger.debug(f"Processing MinIO file: {item}")
            # Extract filename from MinIO URL
            if "?" in item:
                # URL may contain query parameters, remove them
                item_clean = item.split("?")[0]
            else:
                item_clean = item

            # Get filename (from last part of path)
            filename = item_clean.split("/")[-1]

            # If filename contains timestamp, extract original filename
            import re

            timestamp_pattern = r"^(.+)_(\d{13})(\.[^.]+)$"
            match = re.match(timestamp_pattern, filename)
            if match:
                original_filename = match.group(1) + match.group(3)
                # Store original filename for display
                filename_display = original_filename
            else:
                filename_display = filename

            file_type = filename.split(".")[-1].lower() if "." in filename else ""
            item_path = item  # Keep MinIO URL as path

            # Get content_hash from content_hashes mapping
            content_hash = None
            if params and "content_hashes" in params and isinstance(params["content_hashes"], dict):
                content_hash = params["content_hashes"].get(item)

            if not content_hash:
                raise ValueError(f"Missing content_hash for file: {item}")

        else:
            # Local file processing
            file_path = Path(item)
            file_type = file_path.suffix.lower().replace(".", "")
            filename = file_path.name
            filename_display = filename
            item_path = os.path.relpath(file_path, Path.cwd())
            content_hash = None
            try:
                if file_path.exists():
                    content_hash = await calculate_content_hash(file_path)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Failed to calculate content hash for {file_path}: {exc}")

        # Generate file ID
        file_id = f"file_{hashstr(str(item_path) + str(time.time()), 6)}"

    else:
        raise ValueError("URL metadata generation is disabled")

    metadata = {
        "database_id": db_id,
        "filename": filename_display,  # Use display filename
        "path": item_path,
        "file_type": file_type,
        "status": "processing",
        "created_at": utc_isoformat(),
        "file_id": file_id,
        "content_hash": content_hash,
        "parent_id": params.get("parent_id") if params else None,
    }

    # Save processing parameters to metadata
    if params:
        metadata["processing_params"] = params.copy()

    return metadata


def merge_processing_params(metadata_params: dict | None, request_params: dict | None) -> dict:
    """
    Merge processing parameters: prioritize request parameters, use metadata parameters when missing

    Args:
        metadata_params: Parameters saved in metadata
        request_params: Parameters provided in request

    Returns:
        dict: Merged parameters
    """
    merged_params = {}

    # First use parameters from metadata as default values
    if metadata_params:
        merged_params.update(metadata_params)

    # Then override with request parameters (if provided)
    if request_params:
        merged_params.update(request_params)

    logger.debug(f"Merged processing params: {metadata_params=}, {request_params=}, {merged_params=}")
    return merged_params


def get_embedding_config(embed_info: dict) -> dict:
    """
    Get embedding model configuration

    Args:
        embed_info: Embedding information dictionary

    Returns:
        dict: Standardized embedding configuration
    """
    try:
        # Use latest configuration
        assert isinstance(embed_info, dict), f"embed_info must be a dict, got {type(embed_info)}"
        assert "model_id" in embed_info, f"embed_info must contain 'model_id', got {embed_info}"
        logger.warning(f"Using model_id: {embed_info['model_id']}")
        config_dict = config.embed_model_names[embed_info["model_id"]].model_dump()
        config_dict["api_key"] = os.getenv(config_dict["api_key"]) or config_dict["api_key"]
        return config_dict

    except AssertionError as e:
        logger.error(f"AssertionError in get_embedding_config: {e}, embed_info={embed_info}")

    # Compatibility check: legacy configuration fields
    try:
        # 1. Check if embed_info is valid
        if not embed_info or ("model" not in embed_info and "name" not in embed_info):
            logger.error(f"Invalid embed_info: {embed_info}, using default embedding model config")
            raise ValueError("Invalid embed_info: must be a non-empty dictionary")

        # 2. Check if it's an EmbedModelInfo object (may be passed directly in some cases)
        if hasattr(embed_info, "name") and isinstance(embed_info, EmbedModelInfo):
            logger.debug(f"Using EmbedModelInfo object: {embed_info.name}, {traceback.format_exc()}")
            config_dict = embed_info.model_dump()
            config_dict["api_key"] = os.getenv(config_dict["api_key"]) or config_dict["api_key"]
            return config_dict

        raise ValueError(f"Unsupported embed_info format: {embed_info}")

    except Exception as e:
        logger.error(f"Error in get_embedding_config: {e}, embed_info={embed_info}")
        # Return default configuration as fallback
        logger.warning("Falling back to default embedding model config")
        try:
            config_dict = config.embed_model_names[config.embed_model].model_dump()
            config_dict["api_key"] = os.getenv(config_dict["api_key"]) or config_dict["api_key"]
            return config_dict
        except Exception as fallback_error:
            logger.error(f"Failed to get default embedding config: {fallback_error}")
            raise ValueError(f"Failed to get embedding config and fallback failed: {e}")


def is_minio_url(file_path: str) -> bool:
    """
    Detect if it's a MinIO URL

    Args:
        file_path: File path or URL

    Returns:
        bool: Whether it's a MinIO URL
    """
    return file_path.startswith(("http://", "https://", "s3://")) or "minio" in file_path.lower()


def parse_minio_url(file_path: str) -> tuple[str, str]:
    """
    Parse MinIO URL to extract bucket name and object name

    Supports standard HTTP/HTTPS URL format:
    - http(s)://host/bucket-name/path/to/object

    Args:
        file_path: MinIO file URL (http:// or https://)

    Returns:
        tuple[str, str]: (bucket_name, object_name)

    Raises:
        ValueError: If URL cannot be parsed
    """
    try:
        from urllib.parse import urlparse

        # Parse URL
        parsed_url = urlparse(file_path)

        # For minio:// protocol, bucket name is in netloc
        if parsed_url.scheme == "minio":
            bucket_name = parsed_url.netloc
            object_name = parsed_url.path.lstrip("/")
        else:
            # For http/https protocol, bucket name is in first part of path
            object_name = parsed_url.path.lstrip("/")
            path_parts = object_name.split("/", 1)
            if len(path_parts) > 1:
                bucket_name = path_parts[0]
                object_name = path_parts[1]
            else:
                raise ValueError(f"Cannot parse bucket name from MinIO URL: {file_path}")

        logger.debug(f"Parsed MinIO URL: bucket_name={bucket_name}, object_name={object_name}")
        return bucket_name, object_name

    except Exception as e:
        logger.error(f"Failed to parse MinIO URL {file_path}: {e}")
        raise ValueError(f"Cannot parse MinIO URL: {file_path}")
