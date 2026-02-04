from typing import Annotated, Any

from langchain.tools import tool
from pydantic import BaseModel, Field

from src.utils import logger

from .connection import (
    MySQLConnectionManager,
    QueryTimeoutError,
    execute_query_with_timeout,
    limit_result_size,
)
from .exceptions import MySQLConnectionError
from .security import MySQLSecurityChecker

# 全局连接管理器实例
_connection_manager: MySQLConnectionManager | None = None


def get_connection_manager() -> MySQLConnectionManager:
    """获取全局连接管理器"""
    global _connection_manager
    if _connection_manager is None:
        import os

        # 从环境变量中读取 MySQL 配置
        mysql_config = {
            "host": os.getenv("MYSQL_HOST"),
            "user": os.getenv("MYSQL_USER"),
            "password": os.getenv("MYSQL_PASSWORD"),
            "database": os.getenv("MYSQL_DATABASE"),
            "port": int(os.getenv("MYSQL_PORT") or "3306"),
            "charset": "utf8mb4",
            "description": os.getenv("MYSQL_DATABASE_DESCRIPTION") or "默认 MySQL 数据库",
        }
        # 验证配置完整性
        required_keys = ["host", "user", "password", "database"]
        for key in required_keys:
            if not mysql_config[key]:
                raise MySQLConnectionError(
                    f"MySQL configuration missing required key: {key}, please check your environment variables."
                )

        _connection_manager = MySQLConnectionManager(mysql_config)
    return _connection_manager


class TableListModel(BaseModel):
    """获取表名列表的参数模型"""

    pass


@tool(name_or_callable="List Tables", args_schema=TableListModel)
def mysql_list_tables() -> str:
    """Get all table names in the database.

    This tool lists all table names in the current database to help you understand the database structure.
    """
    try:
        conn_manager = get_connection_manager()

        with conn_manager.get_cursor() as cursor:
            # 获取表名
            cursor.execute("SHOW TABLES")
            logger.debug("Executed `SHOW TABLES` query")
            tables = cursor.fetchall()

            if not tables:
                return "No tables found in the database"

            # 提取表名
            table_names = []
            for table in tables:
                table_name = list(table.values())[0]
                table_names.append(table_name)

            # 获取每个表的行数信息
            # table_info = []
            # for table_name in table_names:
            #     try:
            #         cursor.execute(f"SELECT COUNT(*) as count FROM `{table_name}`")
            #         logger.debug(f"Executed `SELECT COUNT(*) FROM {table_name}` query")
            #         count_result = cursor.fetchone()
            #         row_count = count_result["count"]
            #         table_info.append(f"- {table_name} (约 {row_count} 行)")
            #     except Exception:
            #         table_info.append(f"- {table_name} (无法获取行数)")

            all_table_names = "\n".join(table_names)
            result = f"Tables in database:\n{all_table_names}"
            if db_note := conn_manager.config.get("description"):
                result = f"Database description: {db_note}\n\n" + result
            logger.info(f"Retrieved {len(table_names)} tables from database")
            return result

    except Exception as e:
        error_msg = f"Failed to get table names: {str(e)}"
        logger.error(error_msg)
        return error_msg


class TableDescribeModel(BaseModel):
    """Parameter model for getting table structure"""

    table_name: str = Field(description="Table name to query", example="users")


@tool(name_or_callable="Describe Table", args_schema=TableDescribeModel)
def mysql_describe_table(table_name: Annotated[str, "Table name to query structure"]) -> str:
    """Get detailed structure information of a specified table.

    This tool shows field information, data types, NULL constraints, default values, key types, etc.
    Helps you understand the table structure to write correct SQL queries.
    """
    try:
        # 验证表名安全性
        if not MySQLSecurityChecker.validate_table_name(table_name):
            return "Table name contains illegal characters, please check the table name"

        conn_manager = get_connection_manager()

        with conn_manager.get_cursor() as cursor:
            # 获取表结构
            cursor.execute(f"DESCRIBE `{table_name}`")
            columns = cursor.fetchall()

            if not columns:
                return f"Table {table_name} does not exist or has no fields"

            # 获取字段备注信息
            column_comments: dict[str, str] = {}
            try:
                cursor.execute(
                    """
                    SELECT COLUMN_NAME, COLUMN_COMMENT
                    FROM information_schema.COLUMNS
                    WHERE TABLE_NAME = %s AND TABLE_SCHEMA = %s
                    """,
                    (table_name, conn_manager.database_name),
                )
                comment_rows = cursor.fetchall()
                for row in comment_rows:
                    column_name = row.get("COLUMN_NAME")
                    if column_name:
                        column_comments[column_name] = row.get("COLUMN_COMMENT") or ""
            except Exception as e:
                logger.warning(f"Failed to fetch column comments for table {table_name}: {e}")

            # 格式化输出
            result = f"Structure of table `{table_name}`:\n\n"
            result += "Field\t\tType\t\tNULL\tKey\tDefault\t\tExtra\tComment\n"
            result += "-" * 80 + "\n"

            for col in columns:
                field = col["Field"] or ""
                type_str = col["Type"] or ""
                null_str = col["Null"] or ""
                key_str = col["Key"] or ""
                default_str = col.get("Default") or ""
                extra_str = col.get("Extra") or ""
                comment_str = column_comments.get(field, "")

                # 格式化输出
                result += (
                    f"{field:<16}\t{type_str:<16}\t{null_str:<8}\t{key_str:<4}\t"
                    f"{default_str:<16}\t{extra_str:<16}\t{comment_str}\n"
                )

            # 获取索引信息
            try:
                cursor.execute(f"SHOW INDEX FROM `{table_name}`")
                indexes = cursor.fetchall()

                if indexes:
                    result += "\nIndex information:\n"
                    index_dict = {}
                    for idx in indexes:
                        key_name = idx["Key_name"]
                        if key_name not in index_dict:
                            index_dict[key_name] = []
                        index_dict[key_name].append(idx["Column_name"])

                    for key_name, columns in index_dict.items():
                        result += f"- {key_name}: {', '.join(columns)}\n"
            except Exception as e:
                logger.warning(f"Failed to get index info for table {table_name}: {e}")

            logger.info(f"Retrieved structure for table {table_name}")
            return result

    except Exception as e:
        error_msg = f"Failed to get structure of table {table_name}: {str(e)}"
        logger.error(error_msg)
        return error_msg


class QueryModel(BaseModel):
    """Parameter model for executing SQL queries"""

    sql: str = Field(description="SQL query statement to execute (SELECT only)", example="SELECT * FROM users WHERE id = 1")
    timeout: int | None = Field(default=60, description="Query timeout in seconds, default 60s, max 600s", ge=1, le=600)


@tool(name_or_callable="Execute SQL Query", args_schema=QueryModel)
def mysql_query(
    sql: Annotated[str, "SQL query statement to execute (SELECT only)"],
    timeout: Annotated[int | None, "Query timeout in seconds, default 60s, max 600s"] = 60,
) -> str:
    """Execute read-only SQL query statements.

    This tool executes SQL queries and returns results. Supports complex SELECT queries including JOIN, GROUP BY, etc.
    Note: Only query operations are allowed, data modification is not permitted.

    Args:
        sql: SQL query statement
        timeout: Query timeout (prevents long-running queries)
    """
    try:
        # 验证SQL安全性
        if not MySQLSecurityChecker.validate_sql(sql):
            return "SQL statement contains unsafe operations or potential injection attacks, please check the SQL statement"

        if not MySQLSecurityChecker.validate_timeout(timeout):
            return "timeout parameter must be between 1-600"

        conn_manager = get_connection_manager()
        connection = conn_manager.get_connection()

        effective_timeout = timeout or 60
        try:
            result = execute_query_with_timeout(connection, sql, timeout=effective_timeout)
        except QueryTimeoutError as timeout_error:
            logger.error(f"MySQL query timed out after {effective_timeout} seconds: {timeout_error}")
            raise
        except Exception:
            conn_manager.invalidate_connection()
            raise

        if not result:
            return "Query executed successfully, but no results returned"

        # 限制结果大小
        limited_result = limit_result_size(result, max_chars=10000)

        # 检查结果是否被截断
        if len(limited_result) < len(result):
            warning = f"\n\n⚠️ Warning: Query result too large, only showing first {len(limited_result)} rows (total {len(result)} rows).\n"
            warning += "Consider using more precise query conditions or LIMIT clause to reduce returned data."
        else:
            warning = ""

        # 格式化输出
        if limited_result:
            # 获取列名
            columns = list(limited_result[0].keys())

            # 计算每列的最大宽度
            col_widths = {}
            for col in columns:
                col_widths[col] = max(len(str(col)), max(len(str(row.get(col, ""))) for row in limited_result))
                col_widths[col] = min(col_widths[col], 50)  # 限制最大宽度

            # 构建表头
            header = "| " + " | ".join(f"{col:<{col_widths[col]}}" for col in columns) + " |"
            separator = "|" + "|".join("-" * (col_widths[col] + 2) for col in columns) + "|"

            # 构建数据行
            rows = []
            for row in limited_result:
                row_str = "| " + " | ".join(f"{str(row.get(col, '')):<{col_widths[col]}}" for col in columns) + " |"
                rows.append(row_str)

            result_str = f"Query results ({len(limited_result)} rows):\n\n"
            result_str += header + "\n" + separator + "\n"
            result_str += "\n".join(rows[:50])  # 最多显示50行

            if len(rows) > 50:
                result_str += f"\n\n... {len(rows) - 50} more rows not shown ..."

            result_str += warning

            logger.info(f"Query executed successfully, returned {len(limited_result)} rows")
            return result_str

        return "Query executed successfully, but returned data is empty"

    except Exception as e:
        error_msg = f"SQL query execution failed: {str(e)}\n\n{sql}"

        # Provide more useful error information
        if "timeout" in str(e).lower():
            error_msg += "\n\n💡 Suggestion: Query timed out, try the following:\n"
            error_msg += "1. Reduce query data volume (use WHERE conditions to filter)\n"
            error_msg += "2. Use LIMIT clause to limit returned rows\n"
            error_msg += "3. Increase timeout parameter value (max 600 seconds)"
        elif "table" in str(e).lower() and "doesn't exist" in str(e).lower():
            error_msg += "\n\n💡 Suggestion: Table doesn't exist, use mysql_list_tables to view available table names"
        elif "column" in str(e).lower() and "doesn't exist" in str(e).lower():
            error_msg += "\n\n💡 Suggestion: Column doesn't exist, use mysql_describe_table to view table structure"
        elif "not enough arguments for format string" in str(e).lower():
            error_msg += (
                "\n\n💡 Suggestion: The percent sign (%) in SQL is being used as a parameter placeholder."
                " To match text containing percent signs, use double percent signs (%%) or parameterized queries."
            )

        logger.error(error_msg)
        return error_msg


def get_mysql_tools() -> list[Any]:
    """获取MySQL工具列表"""
    return [mysql_list_tables, mysql_describe_table, mysql_query]
