"""
达梦数据库连接和查询模块
支持多种安全模式和灵活的访问控制

Copyright (c) 2025 qyue
Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""
import dmPython
from typing import List, Dict, Any, Optional, Set
import logging
from contextlib import contextmanager
from config import get_config_instance, SecurityMode

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SQLValidator:
    """SQL语句验证器"""
    
    # 只读操作
    READONLY_OPERATIONS = {
        'SELECT', 'WITH', 'SHOW', 'DESCRIBE', 'EXPLAIN', 'ANALYZE'
    }
    
    # 写入操作
    WRITE_OPERATIONS = {
        'INSERT', 'UPDATE'
    }
    
    # 危险操作
    DANGEROUS_OPERATIONS = {
        'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE', 'GRANT', 'REVOKE'
    }
    
    @classmethod
    def validate_sql(cls, sql: str, security_mode: SecurityMode) -> bool:
        """验证SQL语句是否符合当前安全模式"""
        sql_upper = sql.upper().strip()
        
        # 提取SQL的第一个关键字
        first_keyword = cls._extract_first_keyword(sql_upper)
        
        if security_mode == SecurityMode.READONLY:
            return cls._validate_readonly(first_keyword, sql_upper)
        elif security_mode == SecurityMode.LIMITED_WRITE:
            return cls._validate_limited_write(first_keyword, sql_upper)
        elif security_mode == SecurityMode.FULL_ACCESS:
            return True  # 完全访问模式允许所有操作
        
        return False
    
    @classmethod
    def _extract_first_keyword(cls, sql_upper: str) -> str:
        """提取SQL的第一个关键字"""
        words = sql_upper.split()
        return words[0] if words else ""
    
    @classmethod
    def _validate_readonly(cls, first_keyword: str, sql_upper: str) -> bool:
        """验证只读模式的SQL"""
        if first_keyword not in cls.READONLY_OPERATIONS:
            return False
        
        # 对于SELECT查询，进行更精确的检查
        if first_keyword == 'SELECT':
            # 检查是否包含危险的SQL子句（而不是简单的关键字匹配）
            dangerous_patterns = [
                r'\bDROP\s+TABLE\b',
                r'\bTRUNCATE\s+TABLE\b', 
                r'\bDELETE\s+FROM\b',
                r'\bINSERT\s+INTO\b',
                r'\bUPDATE\s+\w+\s+SET\b',
                r'\bCREATE\s+TABLE\b',
                r'\bALTER\s+TABLE\b'
            ]
            
            import re
            for pattern in dangerous_patterns:
                if re.search(pattern, sql_upper):
                    return False
        else:
            # 对于其他只读操作，检查是否包含写入操作的关键子句
            forbidden_in_readonly = cls.WRITE_OPERATIONS.union(cls.DANGEROUS_OPERATIONS)
            for forbidden in forbidden_in_readonly:
                if forbidden in sql_upper:
                    return False
        
        return True
    
    @classmethod
    def _validate_limited_write(cls, first_keyword: str, sql_upper: str) -> bool:
        """验证限制写入模式的SQL"""
        allowed_operations = cls.READONLY_OPERATIONS.union(cls.WRITE_OPERATIONS)
        
        if first_keyword not in allowed_operations:
            return False
        
        # 检查是否包含危险操作
        for dangerous in cls.DANGEROUS_OPERATIONS:
            if dangerous in sql_upper:
                return False
        
        return True
    
    @classmethod
    def get_error_message(cls, sql: str, security_mode: SecurityMode) -> str:
        """获取具体的错误信息"""
        sql_upper = sql.upper().strip()
        first_keyword = cls._extract_first_keyword(sql_upper)
        
        if security_mode == SecurityMode.READONLY:
            if first_keyword in cls.WRITE_OPERATIONS:
                return f"只读模式下禁止写入操作: {first_keyword}"
            elif first_keyword in cls.DANGEROUS_OPERATIONS:
                return f"只读模式下禁止危险操作: {first_keyword}"
            else:
                return f"只读模式下不支持的操作: {first_keyword}"
        
        elif security_mode == SecurityMode.LIMITED_WRITE:
            if first_keyword in cls.DANGEROUS_OPERATIONS:
                return f"限制写入模式下禁止危险操作: {first_keyword}"
            else:
                return f"限制写入模式下不支持的操作: {first_keyword}"
        
        return "操作被安全策略禁止"


class DamengDatabase:
    """达梦数据库操作类"""
    
    def __init__(self):
        self.config = get_config_instance()
        self.sql_validator = SQLValidator()
        logger.info(f"达梦数据库服务初始化完成，安全模式: {self.config.security_mode.value}")
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接上下文管理器"""
        conn = None
        try:
            conn = dmPython.connect(
                user=self.config.username,
                password=self.config.password,
                server=self.config.host,
                port=self.config.port,
                autoCommit=False
            )
            
            # 达梦数据库连接成功后记录配置的数据库实例信息
            if self.config.database:
                logger.info(f"连接配置的数据库实例: {self.config.database}")
            
            # 根据安全模式设置事务属性
            if self.config.is_readonly_mode():
                with conn.cursor() as cur:
                    # 达梦数据库设置只读模式
                    cur.execute("SET SESSION AUTOCOMMIT = 0")
                    logger.info("已设置达梦数据库连接为只读模式")
            
            conn.commit()
            logger.info(f"成功连接到达梦数据库（{self.config.security_mode.value}模式）")
            yield conn
            
        except dmPython.Error as e:
            logger.error(f"达梦数据库连接错误: {e}")
            raise
        finally:
            if conn:
                conn.close()
                logger.info("达梦数据库连接已关闭")
    
    def execute_query(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """执行查询语句"""
        # 安全检查：验证SQL是否符合当前安全模式
        if not self.sql_validator.validate_sql(sql, self.config.security_mode):
            error_msg = self.sql_validator.get_error_message(sql, self.config.security_mode)
            raise ValueError(f"SQL操作被安全策略禁止: {error_msg}")
        
        # 记录查询日志（如果启用）
        if self.config.enable_query_log:
            logger.info(f"执行SQL ({self.config.security_mode.value}): {sql[:200]}...")
        
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(sql, params)
                    
                    # 对于查询操作，获取结果
                    if sql.upper().strip().startswith(('SELECT', 'WITH', 'SHOW', 'DESCRIBE', 'EXPLAIN')):
                        results = cur.fetchall()
                        
                        # 获取列名
                        columns = [desc[0] for desc in cur.description] if cur.description else []
                        
                        # 将结果转换为字典列表
                        result_dicts = []
                        for row in results:
                            result_dicts.append(dict(zip(columns, row)))
                        
                        # 限制返回结果数量
                        if len(result_dicts) > self.config.max_result_rows:
                            logger.warning(f"查询结果超过限制({self.config.max_result_rows})，截断返回")
                            result_dicts = result_dicts[:self.config.max_result_rows]
                        
                        logger.info(f"查询执行成功，返回 {len(result_dicts)} 条记录")
                        return result_dicts
                    else:
                        # 对于非查询操作（INSERT、UPDATE等），提交事务并返回影响的行数
                        conn.commit()
                        affected_rows = cur.rowcount
                        logger.info(f"操作执行成功，影响 {affected_rows} 行")
                        return [{"affected_rows": affected_rows, "status": "success"}]
                        
                except dmPython.Error as e:
                    logger.error(f"SQL执行失败: {e}")
                    raise
    
    def execute_safe_query(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """执行安全查询（强制只读，用于系统查询）"""
        # 强制验证为只读操作
        if not self.sql_validator.validate_sql(sql, SecurityMode.READONLY):
            raise ValueError("系统查询必须是只读操作")
        
        return self.execute_query(sql, params)
    
    def get_all_tables(self, schema: str = 'SYSDBA') -> List[Dict[str, Any]]:
        """获取所有表信息（适配达梦数据库）"""
        # 验证模式是否在允许列表中
        if not self._is_schema_allowed(schema):
            allowed_schemas = self._get_allowed_schemas_display()
            raise ValueError(f"不允许访问模式: {schema}，允许的模式: {allowed_schemas}")
        
        # 达梦数据库查询表信息的SQL
        sql = """
        SELECT 
            OWNER AS schemaname,
            TABLE_NAME AS tablename,
            OWNER AS tableowner,
            'YES' AS hasindexes,
            'NO' AS hasrules,
            'NO' AS hastriggers,
            'NO' AS rowsecurity
        FROM ALL_TABLES 
        WHERE OWNER = ? 
        ORDER BY TABLE_NAME
        """
        return self.execute_safe_query(sql, (schema,))
    
    def _is_schema_allowed(self, schema: str) -> bool:
        """检查schema是否被允许访问"""
        # 如果配置为允许所有schema
        if self.config.is_all_schemas_allowed():
            return True
        
        # 如果配置为自动发现schema
        if self.config.is_auto_discover_schemas():
            # 尝试查询该schema是否存在且用户有权限访问
            try:
                test_sql = """
                SELECT USERNAME 
                FROM ALL_USERS 
                WHERE USERNAME = ?
                """
                result = self.execute_safe_query(test_sql, (schema,))
                return len(result) > 0
            except Exception:
                return False
        
        # 否则检查是否在明确允许的列表中
        return schema in self.config.allowed_schemas
    
    def _get_allowed_schemas_display(self) -> str:
        """获取允许的schema的显示字符串"""
        if self.config.is_all_schemas_allowed():
            return "所有模式(*)"
        elif self.config.is_auto_discover_schemas():
            return "自动发现(auto)"
        else:
            return str(self.config.allowed_schemas)
    
    def get_available_schemas(self) -> List[Dict[str, Any]]:
        """获取用户有权限访问的所有schema（适配达梦数据库）"""
        sql = """
        SELECT USERNAME as schemaname
        FROM ALL_USERS 
        WHERE USERNAME NOT IN ('SYS', 'SYSTEM', 'SYSAUDITOR', 'CTXSYS', 'SYSDBA')
        ORDER BY USERNAME
        """
        return self.execute_safe_query(sql)

    def get_table_structure(self, table_name: str, schema: str = 'SYSDBA') -> List[Dict[str, Any]]:
        """获取表结构信息（适配达梦数据库）"""
        # 验证模式是否在允许列表中
        if not self._is_schema_allowed(schema):
            allowed_schemas = self._get_allowed_schemas_display()
            raise ValueError(f"不允许访问模式: {schema}，允许的模式: {allowed_schemas}")
        
        # 达梦数据库查询表结构的SQL
        sql = """
        SELECT 
            c.COLUMN_NAME as column_name,
            c.DATA_TYPE as data_type,
            c.DATA_LENGTH as character_maximum_length,
            c.DATA_PRECISION as numeric_precision,
            c.DATA_SCALE as numeric_scale,
            CASE WHEN c.NULLABLE = 'Y' THEN 'YES' ELSE 'NO' END as is_nullable,
            c.DATA_DEFAULT as column_default,
            c.COLUMN_ID as ordinal_position,
            CASE 
                WHEN pk.COLUMN_NAME IS NOT NULL THEN 'YES'
                ELSE 'NO'
            END as is_primary_key,
            c.COMMENTS as column_comment
        FROM ALL_TAB_COLUMNS c
        LEFT JOIN (
            SELECT cc.COLUMN_NAME
            FROM ALL_CONSTRAINTS cons
            INNER JOIN ALL_CONS_COLUMNS cc ON cons.CONSTRAINT_NAME = cc.CONSTRAINT_NAME
            WHERE cons.CONSTRAINT_TYPE = 'P'
                AND cons.TABLE_NAME = ?
                AND cons.OWNER = ?
        ) pk ON c.COLUMN_NAME = pk.COLUMN_NAME
        WHERE c.TABLE_NAME = ?
            AND c.OWNER = ?
        ORDER BY c.COLUMN_ID
        """
        return self.execute_safe_query(sql, (table_name, schema, table_name, schema))
    
    def get_table_indexes(self, table_name: str, schema: str = 'SYSDBA') -> List[Dict[str, Any]]:
        """获取表索引信息（适配达梦数据库）"""
        if not self._is_schema_allowed(schema):
            allowed_schemas = self._get_allowed_schemas_display()
            raise ValueError(f"不允许访问模式: {schema}，允许的模式: {allowed_schemas}")
        
        try:
            sql = """
            SELECT 
                INDEX_NAME as indexname,
                'CREATE INDEX ' || INDEX_NAME || ' ON ' || TABLE_NAME as indexdef,
                CASE WHEN UNIQUENESS = 'UNIQUE' THEN 'YES' ELSE 'NO' END as is_unique
            FROM ALL_INDEXES 
            WHERE TABLE_NAME = ? 
                AND OWNER = ?
            ORDER BY INDEX_NAME
            """
            return self.execute_safe_query(sql, (table_name, schema))
        except Exception as e:
            logger.warning(f"获取索引信息失败: {e}")
            return []  # 返回空列表而不是抛出异常
    
    def get_table_constraints(self, table_name: str, schema: str = 'SYSDBA') -> List[Dict[str, Any]]:
        """获取表约束信息（适配达梦数据库）"""
        if not self._is_schema_allowed(schema):
            allowed_schemas = self._get_allowed_schemas_display()
            raise ValueError(f"不允许访问模式: {schema}，允许的模式: {allowed_schemas}")
        
        try:
            sql = """
            SELECT 
                cons.CONSTRAINT_NAME as constraint_name,
                cons.CONSTRAINT_TYPE as constraint_type,
                cc.COLUMN_NAME as column_name,
                CASE 
                    WHEN cons.CONSTRAINT_TYPE = 'R' THEN
                        ref_cons.OWNER||'.'||ref_cons.TABLE_NAME||'.'||ref_cc.COLUMN_NAME
                    ELSE NULL
                END as foreign_key_references
            FROM ALL_CONSTRAINTS cons
            LEFT JOIN ALL_CONS_COLUMNS cc ON cons.CONSTRAINT_NAME = cc.CONSTRAINT_NAME AND cons.OWNER = cc.OWNER
            LEFT JOIN ALL_CONSTRAINTS ref_cons ON cons.R_CONSTRAINT_NAME = ref_cons.CONSTRAINT_NAME
            LEFT JOIN ALL_CONS_COLUMNS ref_cc ON ref_cons.CONSTRAINT_NAME = ref_cc.CONSTRAINT_NAME AND ref_cons.OWNER = ref_cc.OWNER
            WHERE cons.TABLE_NAME = ?
                AND cons.OWNER = ?
            ORDER BY cons.CONSTRAINT_TYPE, cons.CONSTRAINT_NAME
            """
            return self.execute_safe_query(sql, (table_name, schema))
        except Exception as e:
            logger.warning(f"获取约束信息失败: {e}")
            return []  # 返回空列表而不是抛出异常
    
    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            result = self.execute_safe_query("SELECT 1 as test_connection FROM DUAL")
            return len(result) > 0 and result[0]['test_connection'] == 1
        except Exception as e:
            logger.error(f"连接测试失败: {e}")
            return False
    
    def get_security_info(self) -> Dict[str, Any]:
        """获取当前安全配置信息"""
        return {
            "security_mode": self.config.security_mode.value,
            "allowed_schemas": self.config.allowed_schemas,
            "readonly_mode": self.config.is_readonly_mode(),
            "write_allowed": self.config.is_write_allowed(),
            "dangerous_operations_allowed": self.config.is_dangerous_operation_allowed(),
            "max_result_rows": self.config.max_result_rows,
            "query_log_enabled": self.config.enable_query_log
        }


# 全局数据库实例 - 延迟初始化以避免配置未就绪问题
_db_instance = None

def get_db_instance() -> DamengDatabase:
    """获取全局数据库实例"""
    global _db_instance
    if _db_instance is None:
        _db_instance = DamengDatabase()
    return _db_instance


# 保持向后兼容性
db = None  # 将在首次使用时初始化 