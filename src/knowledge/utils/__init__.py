"""Knowledge base utility module

Contains knowledge base related utility functions:
- kb_utils: General knowledge base utility functions
- indexing: File processing and indexing related functions
"""

from .kb_utils import (
    calculate_content_hash,
    get_embedding_config,
    merge_processing_params,
    prepare_item_metadata,
    split_text_into_chunks,
    validate_file_path,
)

__all__ = [
    "calculate_content_hash",
    "get_embedding_config",
    "prepare_item_metadata",
    "split_text_into_chunks",
    "merge_processing_params",
    "validate_file_path",
]
