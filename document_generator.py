"""
达梦数据库文档生成模块
生成表结构设计文档

Copyright (c) 2025 qyue
Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""
from typing import List, Dict, Any
from datetime import datetime
import json
from decimal import Decimal
from tabulate import tabulate
from jinja2 import Template
import re


class DocumentGenerator:
    """文档生成器"""
    
    def __init__(self):
        pass
    
    def _get_timestamp(self):
        """获取当前时间戳"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _get_field_value(self, data: Dict[str, Any], field_name: str, default: str = '') -> str:
        """安全获取字段值，兼容大小写字段名"""
        # 尝试小写字段名
        value = data.get(field_name.lower(), None)
        if value is not None:
            return str(value) if value else default
        
        # 尝试大写字段名
        value = data.get(field_name.upper(), None)
        if value is not None:
            return str(value) if value else default
        
        # 尝试原始字段名
        value = data.get(field_name, None)
        if value is not None:
            return str(value) if value else default
        
        return default
    
    def _json_serializer(self, obj):
        """JSON序列化处理器，处理Decimal等特殊类型"""
        if isinstance(obj, Decimal):
            return str(obj)
        if hasattr(obj, 'isoformat'):  # datetime对象
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    def generate_table_structure_doc(self, table_name: str, structure: List[Dict[str, Any]], 
                                   indexes: List[Dict[str, Any]], 
                                   constraints: List[Dict[str, Any]], 
                                   schema: str = "SYSDBA", 
                                   table_comment: str = "") -> str:
        """生成表结构文档"""
        
        # 基本信息
        doc = f"""# 表结构设计文档: {table_name}

**生成时间**: {self._get_timestamp()}  
**数据库**: 达梦数据库 (DM Database)  
**模式**: {schema}

---

## 表基本信息

**表名**: `{table_name}`  """
        
        if table_comment:
            doc += f"\n**表注释**: {table_comment}"
        
        doc += f"""
**字段数量**: {len(structure)}  
**索引数量**: {len(indexes)}  
**约束数量**: {len(constraints)}

---

## 字段结构

"""
        
        # 字段信息表格
        if structure:
            headers = ['序号', '字段名', '数据类型', '长度', '精度', '标度', '可空', '默认值', '主键', '注释']
            rows = []
            
            for col in structure:
                row = [
                    self._get_field_value(col, 'ordinal_position'),
                    f"`{self._get_field_value(col, 'column_name')}`",
                    self._get_field_value(col, 'data_type'),
                    self._get_field_value(col, 'character_maximum_length'),
                    self._get_field_value(col, 'numeric_precision'),
                    self._get_field_value(col, 'numeric_scale'),
                    '是' if self._get_field_value(col, 'is_nullable') == 'YES' else '否',
                    self._get_field_value(col, 'column_default'),
                    '是' if self._get_field_value(col, 'is_primary_key') == 'YES' else '否',
                    self._get_field_value(col, 'column_comment')
                ]
                rows.append(row)
            
            table_md = tabulate(rows, headers=headers, tablefmt='pipe')
            doc += table_md + "\n\n---\n\n"
        
        # 索引信息
        doc += "## 索引信息\n\n"
        if indexes:
            for idx in indexes:
                doc += f"### `{self._get_field_value(idx, 'indexname')}`\n\n"
                doc += f"**类型**: {'唯一索引' if self._get_field_value(idx, 'is_unique') == 'YES' else '普通索引'}\n\n"
                doc += f"**定义**: \n```sql\n{self._get_field_value(idx, 'indexdef')}\n```\n\n"
        else:
            doc += "暂无索引信息\n\n"
        
        doc += "---\n\n"
        
        # 约束信息
        doc += "## 约束信息\n\n"
        if constraints:
            constraint_types = {}
            for constraint in constraints:
                c_type = self._get_field_value(constraint, 'constraint_type')
                if c_type not in constraint_types:
                    constraint_types[c_type] = []
                constraint_types[c_type].append(constraint)
            
            for c_type, c_list in constraint_types.items():
                doc += f"### {self._get_constraint_type_name(c_type)}\n\n"
                for constraint in c_list:
                    doc += f"- **{self._get_field_value(constraint, 'constraint_name')}**: "
                    doc += f"字段 `{self._get_field_value(constraint, 'column_name')}`"
                    if self._get_field_value(constraint, 'foreign_key_references'):
                        doc += f" → 引用 `{self._get_field_value(constraint, 'foreign_key_references')}`"
                    doc += "\n"
                doc += "\n"
        else:
            doc += "暂无约束信息\n\n"
        
        doc += "---\n\n"
        doc += f"*文档生成时间: {self._get_timestamp()}*\n"
        doc += "*由 达梦数据库 MCP 服务自动生成*\n"
        
        return doc
    
    def generate_database_overview_doc(self, tables: List[Dict[str, Any]], schema: str = "SYSDBA") -> str:
        """生成数据库概览文档"""
        
        doc = f"""# 数据库概览文档

**生成时间**: {self._get_timestamp()}  
**数据库**: {schema} (达梦数据库)  
**表数量**: {len(tables)}

---

## 数据库表清单

"""
        
        if tables:
            headers = ['序号', '表名', '所有者', '是否有索引', '是否有规则', '是否有触发器']
            rows = []
            
            for i, table in enumerate(tables, 1):
                row = [
                    i,
                    f"`{self._get_field_value(table, 'tablename')}`",
                    self._get_field_value(table, 'tableowner'),
                    '是' if self._get_field_value(table, 'hasindexes') == 'YES' else '否',
                    '是' if self._get_field_value(table, 'hasrules') == 'YES' else '否',
                    '是' if self._get_field_value(table, 'hastriggers') == 'YES' else '否'
                ]
                rows.append(row)
            
            table_md = tabulate(rows, headers=headers, tablefmt='pipe')
            doc += table_md + "\n\n---\n\n"
        
        # 统计信息
        doc += "## 统计信息\n\n"
        
        has_indexes = sum(1 for t in tables if self._get_field_value(t, 'hasindexes') == 'YES')
        has_rules = sum(1 for t in tables if self._get_field_value(t, 'hasrules') == 'YES')
        has_triggers = sum(1 for t in tables if self._get_field_value(t, 'hastriggers') == 'YES')
        
        doc += f"- **包含索引的表**: {has_indexes} 个\n"
        doc += f"- **包含规则的表**: {has_rules} 个\n"
        doc += f"- **包含触发器的表**: {has_triggers} 个\n\n"
        
        doc += "---\n\n"
        doc += f"*文档生成时间: {self._get_timestamp()}*\n"
        doc += "*由 达梦数据库 MCP 服务自动生成*\n"
        
        return doc
    
    def generate_relationship_diagram(self, tables: List[Dict[str, Any]], 
                                    relationships: List[Dict[str, Any]], 
                                    schema: str = "SYSDBA") -> str:
        """生成表关系图（Mermaid格式）"""
        
        # 如果没有表，返回空图表
        if not tables:
            return """graph TD
    %% 没有找到表
    EMPTY["没有找到表"]
    
    %% 样式定义
    classDef emptyStyle fill:#ffebee,stroke:#c62828,stroke-width:2px
    
    %% 应用样式
    class EMPTY emptyStyle"""
        
        # 限制表数量，避免图表过于复杂
        max_tables = 15
        if len(tables) > max_tables:
            tables = tables[:max_tables]
        
        mermaid_code = f"""graph TD
    %% 达梦数据库表关系图 - {schema}模式
    %% 生成时间: {self._get_timestamp()}
    %% 显示表数量: {len(tables)} (限制最多{max_tables}个)
    
"""
        
        # 添加表节点 - 使用简化的表名
        for i, table in enumerate(tables):
            table_name = self._get_field_value(table, 'tablename')
            table_comment = self._get_field_value(table, 'tablecomment', '')
            
            # 简化表名显示
            if len(table_name) > 25:
                display_name = table_name[:22] + "..."
            else:
                display_name = table_name
            
            # 清理表名和注释中的特殊字符
            clean_table_name = re.sub(r'[^\w]', '_', table_name)
            clean_comment = re.sub(r'[^\w\s]', '', table_comment)[:12] if table_comment else ''
            
            # 使用更简洁的节点ID
            node_id = f"T{i+1}"
            
            if clean_comment:
                mermaid_code += f'    {node_id}["{display_name}<br/>{clean_comment}"]\n'
            else:
                mermaid_code += f'    {node_id}["{display_name}"]\n'
        
        mermaid_code += "\n"
        
        # 如果有关系，添加关系连线
        if relationships:
            for rel in relationships:
                parent_table = self._get_field_value(rel, 'parent_table')
                child_table = self._get_field_value(rel, 'child_table')
                parent_column = self._get_field_value(rel, 'parent_column')
                child_column = self._get_field_value(rel, 'child_column')
                
                # 找到对应的节点ID
                parent_id = None
                child_id = None
                for i, table in enumerate(tables):
                    table_name = self._get_field_value(table, 'tablename')
                    if table_name == parent_table:
                        parent_id = f"T{i+1}"
                    if table_name == child_table:
                        child_id = f"T{i+1}"
                
                if parent_id and child_id:
                    mermaid_code += f'    {parent_id} -->|"{parent_column} -> {child_column}"| {child_id}\n'
        
        # 如果没有关系，使用更好的布局
        if not relationships:
            # 创建一个简单的网格布局
            mermaid_code += "\n    %% 表分组布局\n"
            for i in range(0, len(tables), 3):
                group_tables = tables[i:i+3]
                for j, table in enumerate(group_tables):
                    node_id = f"T{i+j+1}"
                    if j < len(group_tables) - 1:
                        next_node_id = f"T{i+j+2}"
                        mermaid_code += f'    {node_id} --- {next_node_id}\n'
        
        # 生成节点ID列表
        node_ids = [f"T{i+1}" for i in range(len(tables))]
        node_ids_str = ','.join(node_ids)
        
        mermaid_code += f"""
    %% 样式定义
    classDef tableStyle fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
    classDef relationStyle stroke:#ff6f00,stroke-width:2px
    classDef noRelStyle fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    
    %% 应用样式
    class {node_ids_str} tableStyle
"""
        
        return mermaid_code
    
    def generate_relationship_doc(self, tables: List[Dict[str, Any]], 
                                relationships: List[Dict[str, Any]], 
                                schema: str = "SYSDBA") -> str:
        """生成表关系文档"""
        
        doc = f"""# 数据库表关系图文档

**生成时间**: {self._get_timestamp()}  
**数据库**: {schema} (达梦数据库)  
**表数量**: {len(tables)}  
**关系数量**: {len(relationships)}

---

## 表关系图

```mermaid
{self.generate_relationship_diagram(tables, relationships, schema)}
```

---

## 关系详情

"""
        
        if relationships:
            headers = ['序号', '父表', '父字段', '子表', '子字段', '约束名', '关系类型']
            rows = []
            
            for i, rel in enumerate(relationships, 1):
                row = [
                    i,
                    f"`{self._get_field_value(rel, 'parent_table')}`",
                    f"`{self._get_field_value(rel, 'parent_column')}`",
                    f"`{self._get_field_value(rel, 'child_table')}`",
                    f"`{self._get_field_value(rel, 'child_column')}`",
                    self._get_field_value(rel, 'constraint_name'),
                    self._get_field_value(rel, 'constraint_type', 'FOREIGN KEY')
                ]
                rows.append(row)
            
            table_md = tabulate(rows, headers=headers, tablefmt='pipe')
            doc += table_md + "\n\n"
        else:
            doc += "未发现表间关系。\n\n"
        
        # 统计信息
        doc += "## 统计信息\n\n"
        doc += f"- **表数量**: {len(tables)} 个\n"
        doc += f"- **关系数量**: {len(relationships)} 个\n"
        
        if relationships:
            # 统计每个表的关联数量
            table_relations = {}
            for rel in relationships:
                parent = self._get_field_value(rel, 'parent_table')
                child = self._get_field_value(rel, 'child_table')
                table_relations[parent] = table_relations.get(parent, 0) + 1
                table_relations[child] = table_relations.get(child, 0) + 1
            
            if table_relations:
                doc += f"- **关联最多的表**: {max(table_relations.items(), key=lambda x: x[1])[0]} ({max(table_relations.values())} 个关系)\n"
        
        doc += "\n---\n\n"
        doc += f"*文档生成时间: {self._get_timestamp()}*\n"
        doc += "*由 达梦数据库 MCP 服务自动生成*\n"
        
        return doc
    
    def generate_json_structure(self, table_name: str, structure: List[Dict[str, Any]], 
                              indexes: List[Dict[str, Any]], 
                              constraints: List[Dict[str, Any]], 
                              schema: str = "SYSDBA", 
                              table_comment: str = "") -> str:
        """生成JSON格式的表结构"""
        data = {
            "table_name": table_name,
            "table_comment": table_comment,
            "generated_at": self._get_timestamp(),
            "database": schema,
            "schema": schema,
            "structure": {
                "columns": structure,
                "indexes": indexes,
                "constraints": constraints
            },
            "statistics": {
                "column_count": len(structure),
                "index_count": len(indexes),
                "constraint_count": len(constraints)
            }
        }
        return json.dumps(data, ensure_ascii=False, indent=2, default=self._json_serializer)
    
    def _get_constraint_type_name(self, constraint_type: str) -> str:
        """获取约束类型中文名称（适配达梦数据库）"""
        type_mapping = {
            'P': '主键约束',
            'R': '外键约束',
            'U': '唯一约束',
            'C': '检查约束',
            'N': '非空约束'
        }
        return type_mapping.get(constraint_type, constraint_type)
    
    def generate_sql_create_statement(self, table_name: str, structure: List[Dict[str, Any]], table_comment: str = "") -> str:
        """生成建表SQL语句（仅用于文档参考）"""
        sql = f"-- 表结构参考SQL (仅供参考，不可执行)\n"
        sql += f"-- 表名: {table_name}\n"
        if table_comment:
            sql += f"-- 表注释: {table_comment}\n"
        sql += f"-- 生成时间: {self._get_timestamp()}\n"
        sql += f"-- 数据库: 达梦数据库\n\n"
        sql += f"CREATE TABLE {table_name} (\n"
        
        columns = []
        for col in structure:
            col_def = f"    {self._get_field_value(col, 'column_name')}"
            
            # 数据类型
            data_type = self._get_field_value(col, 'data_type')
            char_length = self._get_field_value(col, 'character_maximum_length')
            num_precision = self._get_field_value(col, 'numeric_precision')
            num_scale = self._get_field_value(col, 'numeric_scale')
            
            if char_length:
                data_type += f"({char_length})"
            elif num_precision and num_scale:
                data_type += f"({num_precision},{num_scale})"
            
            col_def += f" {data_type}"
            
            # 非空约束
            if self._get_field_value(col, 'is_nullable') == 'NO':
                col_def += " NOT NULL"
            
            # 默认值
            default_val = self._get_field_value(col, 'column_default')
            if default_val:
                col_def += f" DEFAULT {default_val}"
            
            # 注释
            comment = self._get_field_value(col, 'column_comment')
            if comment:
                col_def += f" -- {comment}"
            
            columns.append(col_def)
        
        sql += ",\n".join(columns)
        sql += "\n);\n\n"
        sql += "-- 注意: 此SQL仅为结构参考，实际建表请根据业务需求调整\n"
        
        return sql


# 全局文档生成器实例
doc_generator = DocumentGenerator() 