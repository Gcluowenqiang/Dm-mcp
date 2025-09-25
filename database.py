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
from decimal import Decimal
import time
import hashlib
from config import get_config_instance, SecurityMode

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QueryCache:
    """查询缓存管理器"""
    
    def __init__(self, max_size: int = 100, ttl: int = 300):
        """
        初始化查询缓存
        
        Args:
            max_size: 最大缓存条目数
            ttl: 缓存生存时间（秒）
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.ttl = ttl
        self.access_times: Dict[str, float] = {}
    
    def _generate_key(self, sql: str, schema: str = None) -> str:
        """生成缓存键"""
        key_data = f"{sql}_{schema or ''}"
        return hashlib.md5(key_data.encode('utf-8')).hexdigest()
    
    def get(self, sql: str, schema: str = None) -> Optional[List[Dict[str, Any]]]:
        """获取缓存结果"""
        key = self._generate_key(sql, schema)
        
        if key not in self.cache:
            return None
        
        # 检查是否过期
        if time.time() - self.cache[key]['timestamp'] > self.ttl:
            self._remove(key)
            return None
        
        # 更新访问时间
        self.access_times[key] = time.time()
        logger.debug(f"缓存命中: {sql[:50]}...")
        return self.cache[key]['data']
    
    def set(self, sql: str, data: List[Dict[str, Any]], schema: str = None):
        """设置缓存结果"""
        key = self._generate_key(sql, schema)
        
        # 如果缓存已满，删除最旧的条目
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        self.cache[key] = {
            'data': data,
            'timestamp': time.time(),
            'sql': sql,
            'schema': schema
        }
        self.access_times[key] = time.time()
        logger.debug(f"缓存设置: {sql[:50]}...")
    
    def _remove(self, key: str):
        """删除缓存条目"""
        if key in self.cache:
            del self.cache[key]
        if key in self.access_times:
            del self.access_times[key]
    
    def _evict_oldest(self):
        """删除最旧的缓存条目"""
        if not self.access_times:
            return
        
        oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        self._remove(oldest_key)
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.access_times.clear()
        logger.info("查询缓存已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            'cache_size': len(self.cache),
            'max_size': self.max_size,
            'ttl': self.ttl,
            'entries': list(self.cache.keys())
        }


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
    
    # 常量定义
    SYSTEM_USERS = ('SYS', 'SYSTEM', 'SYSAUDITOR', 'CTXSYS')
    DEFAULT_AUTO_COMMIT = True
    DEFAULT_SCHEMA = 'SYSDBA'
    
    def __init__(self):
        self.config = get_config_instance()
        self.sql_validator = SQLValidator()
        # 初始化查询缓存
        self.query_cache = QueryCache(
            max_size=getattr(self.config, 'cache_max_size', 100),
            ttl=getattr(self.config, 'cache_ttl', 300)
        )
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
                autoCommit=self.DEFAULT_AUTO_COMMIT  # 达梦数据库使用自动提交模式避免语法问题
            )
            
            # 达梦数据库连接成功后记录配置的数据库实例信息
            if self.config.database:
                logger.info(f"连接配置的数据库实例: {self.config.database}")
            
            # 达梦数据库连接配置
            if self.config.is_readonly_mode():
                logger.info("已设置达梦数据库连接为只读模式")
            
            logger.info(f"成功连接到达梦数据库（{self.config.security_mode.value}模式）")
            yield conn
            
        except dmPython.Error as e:
            logger.error(f"达梦数据库连接错误: {e}")
            raise
        finally:
            if conn:
                conn.close()
                logger.info("达梦数据库连接已关闭")
    
    def execute_query(self, sql: str, params: Optional[tuple] = None, use_cache: bool = True) -> List[Dict[str, Any]]:
        """执行查询语句"""
        # 安全检查：验证SQL是否符合当前安全模式
        if not self.sql_validator.validate_sql(sql, self.config.security_mode):
            error_msg = self.sql_validator.get_error_message(sql, self.config.security_mode)
            raise ValueError(f"SQL操作被安全策略禁止: {error_msg}")
        
        # 对于只读查询，尝试从缓存获取
        if use_cache and sql.upper().strip().startswith(('SELECT', 'WITH', 'SHOW', 'DESCRIBE', 'EXPLAIN')):
            cached_result = self.query_cache.get(sql)
            if cached_result is not None:
                logger.debug(f"从缓存返回查询结果: {sql[:50]}...")
                return cached_result
        
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
                        
                        # 将结果转换为字典列表，处理 Decimal 类型
                        result_dicts = []
                        for row in results:
                            # 转换 Decimal 为 float 或 str 以支持 JSON 序列化
                            converted_row = []
                            for value in row:
                                if isinstance(value, Decimal):
                                    # 对于 Decimal，转换为 float（如果精度允许）或 str
                                    try:
                                        converted_row.append(float(value))
                                    except (OverflowError, ValueError):
                                        converted_row.append(str(value))
                                else:
                                    converted_row.append(value)
                            result_dicts.append(dict(zip(columns, converted_row)))
                        
                        # 递归处理嵌套的 Decimal 类型
                        def deep_convert_decimals(obj):
                            if isinstance(obj, dict):
                                return {k: deep_convert_decimals(v) for k, v in obj.items()}
                            elif isinstance(obj, list):
                                return [deep_convert_decimals(item) for item in obj]
                            elif isinstance(obj, Decimal):
                                try:
                                    return float(obj)
                                except (OverflowError, ValueError):
                                    return str(obj)
                            else:
                                return obj
                        
                        result_dicts = deep_convert_decimals(result_dicts)
                        
                        # 限制返回结果数量
                        if len(result_dicts) > self.config.max_result_rows:
                            logger.warning(f"查询结果超过限制({self.config.max_result_rows})，截断返回")
                            result_dicts = result_dicts[:self.config.max_result_rows]
                        
                        logger.info(f"查询执行成功，返回 {len(result_dicts)} 条记录")
                        
                        # 将查询结果缓存
                        if use_cache:
                            self.query_cache.set(sql, result_dicts)
                        
                        return result_dicts
                    else:
                        # 对于非查询操作（INSERT、UPDATE等），返回影响的行数（已自动提交）
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
    
    def get_all_tables(self, schema: str = None) -> List[Dict[str, Any]]:
        """获取所有表信息（适配达梦数据库）"""
        if schema is None:
            schema = self.DEFAULT_SCHEMA
            
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
        """获取用户有权限访问的所有schema（基于表所有者）"""
        sql = f"""
        SELECT DISTINCT OWNER as schemaname
        FROM ALL_TABLES 
        WHERE OWNER NOT IN {self.SYSTEM_USERS}
        ORDER BY OWNER
        """
        return self.execute_safe_query(sql)

    def get_table_structure(self, table_name: str, schema: str = None) -> List[Dict[str, Any]]:
        """获取表结构信息（适配达梦数据库）"""
        if schema is None:
            schema = self.DEFAULT_SCHEMA
            
        # 验证模式是否在允许列表中
        if not self._is_schema_allowed(schema):
            allowed_schemas = self._get_allowed_schemas_display()
            raise ValueError(f"不允许访问模式: {schema}，允许的模式: {allowed_schemas}")
        
        # 达梦数据库查询表结构的SQL，使用USER_*视图
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
            com.COMMENTS as column_comment
        FROM USER_TAB_COLUMNS c
        LEFT JOIN USER_COL_COMMENTS com 
            ON com.TABLE_NAME = c.TABLE_NAME 
            AND com.COLUMN_NAME = c.COLUMN_NAME
        LEFT JOIN (
            SELECT cc.COLUMN_NAME
            FROM USER_CONSTRAINTS cons
            INNER JOIN USER_CONS_COLUMNS cc ON cons.CONSTRAINT_NAME = cc.CONSTRAINT_NAME
            WHERE cons.CONSTRAINT_TYPE = 'P'
                AND cons.TABLE_NAME = ?
        ) pk ON c.COLUMN_NAME = pk.COLUMN_NAME
        WHERE c.TABLE_NAME = ?
        ORDER BY c.COLUMN_ID
        """
        return self.execute_safe_query(sql, (table_name, table_name))

    def get_table_comment(self, table_name: str, schema: str = None) -> str:
        """获取表的注释（优先从 ALL_TAB_COMMENTS 读取）"""
        if schema is None:
            schema = self.DEFAULT_SCHEMA
            
        if not self._is_schema_allowed(schema):
            allowed_schemas = self._get_allowed_schemas_display()
            raise ValueError(f"不允许访问模式: {schema}，允许的模式: {allowed_schemas}")
        try:
            sql = """
            SELECT COMMENTS
            FROM USER_TAB_COMMENTS
            WHERE TABLE_NAME = ?
            """
            result = self.execute_safe_query(sql, (table_name,))
            if result and (result[0].get('COMMENTS') or result[0].get('comments')):
                return result[0].get('COMMENTS') or result[0].get('comments')
            return ""
        except Exception:
            return ""
    
    def get_table_indexes(self, table_name: str, schema: str = None) -> List[Dict[str, Any]]:
        """获取表索引信息（适配达梦数据库）"""
        if schema is None:
            schema = self.DEFAULT_SCHEMA
            
        if not self._is_schema_allowed(schema):
            allowed_schemas = self._get_allowed_schemas_display()
            raise ValueError(f"不允许访问模式: {schema}，允许的模式: {allowed_schemas}")
        
        try:
            sql = """
            SELECT 
                INDEX_NAME as indexname,
                'CREATE INDEX ' || INDEX_NAME || ' ON ' || TABLE_NAME as indexdef,
                CASE WHEN UNIQUENESS = 'UNIQUE' THEN 'YES' ELSE 'NO' END as is_unique
            FROM USER_INDEXES 
            WHERE TABLE_NAME = ?
            ORDER BY INDEX_NAME
            """
            return self.execute_safe_query(sql, (table_name,))
        except Exception as e:
            logger.warning(f"获取索引信息失败: {e}")
            return []  # 返回空列表而不是抛出异常
    
    def get_table_constraints(self, table_name: str, schema: str = None) -> List[Dict[str, Any]]:
        """获取表约束信息（适配达梦数据库）"""
        if schema is None:
            schema = self.DEFAULT_SCHEMA
            
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
            FROM USER_CONSTRAINTS cons
            LEFT JOIN USER_CONS_COLUMNS cc ON cons.CONSTRAINT_NAME = cc.CONSTRAINT_NAME
            LEFT JOIN USER_CONSTRAINTS ref_cons ON cons.R_CONSTRAINT_NAME = ref_cons.CONSTRAINT_NAME
            LEFT JOIN USER_CONS_COLUMNS ref_cc ON ref_cons.CONSTRAINT_NAME = ref_cc.CONSTRAINT_NAME
            WHERE cons.TABLE_NAME = ?
            ORDER BY cons.CONSTRAINT_TYPE, cons.CONSTRAINT_NAME
            """
            return self.execute_safe_query(sql, (table_name,))
        except Exception as e:
            logger.warning(f"获取约束信息失败: {e}")
            return []  # 返回空列表而不是抛出异常
    
    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            result = self.execute_safe_query("SELECT 1 as test_connection FROM DUAL")
            if len(result) > 0:
                # 达梦数据库字段名可能是大写，尝试两种格式
                first_row = result[0]
                test_value = first_row.get('test_connection') or first_row.get('TEST_CONNECTION')
                return test_value == 1
            return False
        except Exception as e:
            logger.error(f"连接测试失败: {e}")
            return False
    
    def get_table_statistics(self, table_name: str, schema: str = None) -> Dict[str, Any]:
        """获取表的统计信息"""
        if schema is None:
            schema = self.DEFAULT_SCHEMA
            
        if not self._is_schema_allowed(schema):
            allowed_schemas = self._get_allowed_schemas_display()
            raise ValueError(f"不允许访问模式: {schema}，允许的模式: {allowed_schemas}")
        
        try:
            # 获取表基本信息
            table_info_sql = """
            SELECT 
                TABLE_NAME,
                TABLESPACE_NAME,
                STATUS,
                LAST_ANALYZED
            FROM ALL_TABLES 
            WHERE TABLE_NAME = ? AND OWNER = ?
            """
            table_info = self.execute_safe_query(table_info_sql, (table_name, schema))
            
            if not table_info:
                return {}
            
            table_info = table_info[0]
            
            # 获取表的行数
            try:
                row_count_sql = f"SELECT COUNT(*) as row_count FROM {schema}.{table_name}"
                row_count_result = self.execute_safe_query(row_count_sql)
                row_count = row_count_result[0].get('row_count') or row_count_result[0].get('ROW_COUNT', 0)
            except Exception as e:
                logger.warning(f"获取表行数失败: {e}")
                row_count = 0
            
            # 获取字段数量
            try:
                column_count_sql = """
                SELECT COUNT(*) as column_count
                FROM ALL_TAB_COLUMNS 
                WHERE TABLE_NAME = ? AND OWNER = ?
                """
                column_count_result = self.execute_safe_query(column_count_sql, (table_name, schema))
                column_count = column_count_result[0].get('column_count') or column_count_result[0].get('COLUMN_COUNT', 0)
            except Exception as e:
                logger.warning(f"获取字段数量失败: {e}")
                column_count = 0
            
            # 获取索引数量
            try:
                index_count_sql = """
                SELECT COUNT(*) as index_count
                FROM ALL_INDEXES 
                WHERE TABLE_NAME = ? AND OWNER = ?
                """
                index_count_result = self.execute_safe_query(index_count_sql, (table_name, schema))
                index_count = index_count_result[0].get('index_count') or index_count_result[0].get('INDEX_COUNT', 0)
            except Exception as e:
                logger.warning(f"获取索引数量失败: {e}")
                index_count = 0
            
            # 获取约束数量
            try:
                constraint_count_sql = """
                SELECT COUNT(*) as constraint_count
                FROM ALL_CONSTRAINTS 
                WHERE TABLE_NAME = ? AND OWNER = ?
                """
                constraint_count_result = self.execute_safe_query(constraint_count_sql, (table_name, schema))
                constraint_count = constraint_count_result[0].get('constraint_count') or constraint_count_result[0].get('CONSTRAINT_COUNT', 0)
            except Exception as e:
                logger.warning(f"获取约束数量失败: {e}")
                constraint_count = 0
            
            # 获取表的大小信息（如果可用）
            try:
                # 尝试从系统统计表获取大小信息
                size_info_sql = """
                SELECT 
                    TOTAL_ROWS,
                    LAST_STAT_DT
                FROM SYS.SYSSTATTABLEIDU s
                INNER JOIN ALL_TABLES t ON s.ID = t.TABLE_ID
                WHERE t.TABLE_NAME = ? AND t.OWNER = ?
                """
                size_info_result = self.execute_safe_query(size_info_sql, (table_name, schema))
                if size_info_result:
                    size_info = size_info_result[0]
                    total_rows_from_stats = size_info.get('TOTAL_ROWS') or size_info.get('total_rows')
                    last_stat_date = size_info.get('LAST_STAT_DT') or size_info.get('last_stat_dt')
                else:
                    total_rows_from_stats = None
                    last_stat_date = None
            except Exception as e:
                logger.warning(f"获取表大小信息失败: {e}")
                total_rows_from_stats = None
                last_stat_date = None
            
            # 组装统计信息
            statistics = {
                "table_name": table_name,
                "schema": schema,
                "row_count": row_count,
                "column_count": column_count,
                "index_count": index_count,
                "constraint_count": constraint_count,
                "tablespace_name": table_info.get('TABLESPACE_NAME') or table_info.get('tablespace_name'),
                "status": table_info.get('STATUS') or table_info.get('status'),
                "last_analyzed": table_info.get('LAST_ANALYZED') or table_info.get('last_analyzed'),
                "total_rows_from_stats": total_rows_from_stats,
                "last_stat_date": last_stat_date
            }
            
            return statistics
            
        except Exception as e:
            logger.error(f"获取表统计信息失败: {e}")
            return {}
    
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
    
    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return self.query_cache.get_stats()
    
    def clear_cache(self):
        """清空查询缓存"""
        self.query_cache.clear()
        logger.info("查询缓存已清空")
    
    def get_table_relationships(self, schema: str = None) -> List[Dict[str, Any]]:
        """获取表间关系信息"""
        if schema is None:
            schema = self.DEFAULT_SCHEMA
        
        # 验证schema访问权限
        if not self._is_schema_allowed(schema):
            raise ValueError(f"没有权限访问模式: {schema}")
        
        sql = """
        SELECT 
            tc.TABLE_NAME as child_table,
            kcu.COLUMN_NAME as child_column,
            ccu.TABLE_NAME as parent_table,
            ccu.COLUMN_NAME as parent_column,
            tc.CONSTRAINT_NAME as constraint_name,
            tc.CONSTRAINT_TYPE as constraint_type
        FROM 
            USER_CONSTRAINTS tc
        JOIN 
            USER_CONS_COLUMNS kcu ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        JOIN 
            USER_CONS_COLUMNS ccu ON tc.R_CONSTRAINT_NAME = ccu.CONSTRAINT_NAME
        WHERE 
            tc.CONSTRAINT_TYPE = 'R'
            AND tc.TABLE_NAME IN (
                SELECT TABLE_NAME FROM USER_TABLES 
                WHERE TABLE_NAME NOT LIKE 'SYS_%'
            )
        ORDER BY 
            tc.TABLE_NAME, kcu.COLUMN_NAME
        """
        
        try:
            results = self.execute_query(sql, use_cache=True)
            logger.info(f"获取到 {len(results)} 个表关系")
            return results
        except Exception as e:
            logger.error(f"获取表关系失败: {e}")
            return []


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