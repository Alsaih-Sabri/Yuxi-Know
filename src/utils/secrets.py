"""Secure secrets management for production deployment"""
import os
from pathlib import Path
from typing import Optional

from src.utils.logging_config import logger


def read_secret(secret_name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Read secret from file or environment variable.
    
    Priority:
    1. Docker secret file (e.g., /run/secrets/secret_name)
    2. Custom secret file path from env var (e.g., SECRET_NAME_FILE)
    3. Environment variable (e.g., SECRET_NAME)
    4. Default value
    
    Args:
        secret_name: Name of the secret (e.g., "NEO4J_PASSWORD")
        default: Default value if secret not found
        
    Returns:
        Secret value or default
        
    Example:
        >>> password = read_secret("NEO4J_PASSWORD", "default_password")
        >>> api_key = read_secret("OPENAI_API_KEY")
    """
    # Try Docker secrets first (/run/secrets/secret_name)
    docker_secret_path = Path(f"/run/secrets/{secret_name.lower()}")
    if docker_secret_path.exists():
        try:
            secret_value = docker_secret_path.read_text().strip()
            if secret_value:
                logger.debug(f"Loaded secret '{secret_name}' from Docker secrets")
                return secret_value
        except Exception as e:
            logger.warning(f"Failed to read Docker secret '{secret_name}': {e}")
    
    # Try custom file path from environment variable
    secret_file_env = f"{secret_name}_FILE"
    secret_file_path = os.getenv(secret_file_env)
    if secret_file_path:
        secret_path = Path(secret_file_path)
        if secret_path.exists():
            try:
                secret_value = secret_path.read_text().strip()
                if secret_value:
                    logger.debug(f"Loaded secret '{secret_name}' from file: {secret_file_path}")
                    return secret_value
            except Exception as e:
                logger.warning(f"Failed to read secret file '{secret_file_path}': {e}")
        else:
            logger.warning(f"Secret file not found: {secret_file_path}")
    
    # Fallback to environment variable
    env_value = os.getenv(secret_name)
    if env_value:
        logger.debug(f"Loaded secret '{secret_name}' from environment variable")
        return env_value
    
    # Return default
    if default is not None:
        logger.debug(f"Using default value for secret '{secret_name}'")
        return default
    
    logger.warning(f"Secret '{secret_name}' not found in any source")
    return None


def get_database_credentials() -> dict:
    """Get database credentials from secrets"""
    return {
        "neo4j": {
            "uri": os.getenv("NEO4J_URI", "bolt://graph:7687"),
            "username": read_secret("NEO4J_USERNAME", "neo4j"),
            "password": read_secret("NEO4J_PASSWORD", "password"),
        },
        "milvus": {
            "uri": os.getenv("MILVUS_URI", "http://milvus:19530"),
            "token": read_secret("MILVUS_TOKEN", ""),
            "db_name": os.getenv("MILVUS_DB_NAME", "default"),
        },
        "minio": {
            "uri": os.getenv("MINIO_URI", "http://milvus-minio:9000"),
            "access_key": read_secret("MINIO_ACCESS_KEY", "minioadmin"),
            "secret_key": read_secret("MINIO_SECRET_KEY", "minioadmin"),
        },
    }


def get_api_keys() -> dict:
    """Get API keys from secrets"""
    return {
        "openai": read_secret("OPENAI_API_KEY"),
        "siliconflow": read_secret("SILICONFLOW_API_KEY"),
        "tavily": read_secret("TAVILY_API_KEY"),
        "deepseek": read_secret("DEEPSEEK_API_KEY"),
        "gemini": read_secret("GEMINI_API_KEY"),
        "zhipuai": read_secret("ZHIPUAI_API_KEY"),
        "dashscope": read_secret("DASHSCOPE_API_KEY"),
        "voyage": read_secret("VOYAGE_API_KEY"),
    }


def get_admin_credentials() -> dict:
    """Get admin credentials from secrets"""
    return {
        "username": read_secret("YUXI_SUPER_ADMIN_NAME", "admin"),
        "password": read_secret("YUXI_SUPER_ADMIN_PASSWORD"),
    }


def get_jwt_secret() -> str:
    """Get JWT secret for token signing"""
    secret = read_secret("JWT_SECRET")
    if not secret:
        logger.warning("JWT_SECRET not set! Using insecure default. Set JWT_SECRET in production!")
        secret = "insecure-default-secret-change-me"
    return secret
