# 使用官方Python 3.11镜像作为基础镜像
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# 设置达梦数据库相关环境变量（解决加密模块加载问题）
ENV LD_LIBRARY_PATH="/opt/dmdbms/bin:/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH"
ENV DM_HOME="/opt/dmdbms"

# 创建工作目录
WORKDIR /app

# 安装系统依赖（包含达梦数据库加密模块所需的库）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libc6-dev \
    make \
    curl \
    wget \
    openssl \
    libssl-dev \
    libssl3 \
    libaio1 \
    libc6 \
    libgcc-s1 \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 创建达梦数据库驱动目录
RUN mkdir -p /opt/dmdbms/bin

# 复制达梦数据库驱动文件（如果有本地驱动文件）
# 注意：在实际部署时，需要将达梦数据库的驱动文件复制到 /opt/dmdbms/bin 目录
# COPY ./dmdbms /opt/dmdbms

# 设置驱动文件权限（确保加密模块可执行）
RUN chmod -R +x /opt/dmdbms/bin 2>/dev/null || true

# 复制requirements文件并安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=300 -r requirements.txt

# 复制应用源代码
COPY . .

# 创建docs目录（用于文档生成）
RUN mkdir -p /app/docs

# 设置正确的文件权限
RUN chmod +x main.py 2>/dev/null || true

# 暴露默认端口（虽然MCP通过stdio通信，但为了兼容性保留）
EXPOSE 3000

# 简化的健康检查（不连接数据库）
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# 验证环境配置
RUN echo "达梦数据库环境配置:" && \
    echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH" && \
    echo "DM_HOME: $DM_HOME" && \
    echo "Python版本: $(python --version)" && \
    echo "构建验证完成"

# 注意：所有数据库连接配置必须通过运行时环境变量提供
# 平台将动态注入以下必需的环境变量：
# DAMENG_HOST, DAMENG_PORT, DAMENG_USERNAME, DAMENG_PASSWORD
# 以及可选的安全和配置参数

# 运行MCP服务器
CMD ["python", "main.py"] 