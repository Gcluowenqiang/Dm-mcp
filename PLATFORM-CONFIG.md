# 平台部署配置说明

## 环境变量配置

本MCP服务采用完全动态配置，所有数据库连接信息必须通过平台运行时环境变量提供。

### 达梦数据库连接特点

**重要说明**：达梦数据库的架构特点是一个实例通常就是一个数据库，用户连接到实例后通过不同的Schema来区分数据空间，因此连接时**不需要**指定具体的database名称。这与MySQL等数据库不同。

### 必需环境变量

```bash
DAMENG_HOST=your_database_host        # 达梦数据库主机地址
DAMENG_PORT=5236                      # 达梦数据库端口
DAMENG_USERNAME=your_username         # 数据库用户名
DAMENG_PASSWORD=your_password         # 数据库密码
# 注意：达梦数据库不需要database参数，通过schema区分数据空间
```

### 可选环境变量

```bash
# 安全配置
DAMENG_SECURITY_MODE=readonly         # 安全模式 (默认: readonly)
DAMENG_ALLOWED_SCHEMAS=*              # 允许访问的模式 (默认: *)
DAMENG_MAX_RESULT_ROWS=1000          # 最大返回行数 (默认: 1000)
DAMENG_ENABLE_QUERY_LOG=false        # 查询日志 (默认: false)

# 连接配置
DAMENG_CONNECT_TIMEOUT=30            # 连接超时/秒 (默认: 30)
DAMENG_QUERY_TIMEOUT=60              # 查询超时/秒 (默认: 60)
DAMENG_MAX_RETRIES=3                 # 最大重试次数 (默认: 3)
```

## 安全模式说明

### readonly (只读模式) - 推荐
- 仅允许查询操作
- 禁止写入和危险操作

### limited_write (限制写入)
- 允许查询、插入、更新操作
- 禁止删除、删表等危险操作

### full_access (完全访问) - 谨慎使用
- 允许所有SQL操作

## 配置示例

### 生产环境推荐
```bash
DAMENG_HOST=prod-dm.company.com
DAMENG_PORT=5236
DAMENG_USERNAME=readonly_user
DAMENG_PASSWORD=secure_password
DAMENG_SECURITY_MODE=readonly
DAMENG_ALLOWED_SCHEMAS=PROD_SCHEMA
DAMENG_MAX_RESULT_ROWS=500
```

### 开发环境配置
```bash
DAMENG_HOST=dev-dm.company.com
DAMENG_PORT=5236
DAMENG_USERNAME=dev_user
DAMENG_PASSWORD=dev_password
DAMENG_SECURITY_MODE=limited_write
DAMENG_ALLOWED_SCHEMAS=*
DAMENG_ENABLE_QUERY_LOG=true
```

## 部署注意事项

1. **不要硬编码数据库连接信息**
2. **密码等敏感信息必须通过平台安全环境变量提供**
3. **生产环境建议使用只读模式**
4. **定期轮换数据库密码**

