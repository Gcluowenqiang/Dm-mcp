# 使用官方Python 3.11镜像作为基础镜像
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# 创建工作目录
WORKDIR /app

# 安装系统依赖（达梦数据库客户端相关）
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libc6-dev \
    make \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件并安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用源代码
COPY . .

# 创建docs目录（用于文档生成）
RUN mkdir -p /app/docs

# 设置正确的文件权限
RUN chmod +x main.py

# 暴露默认端口（虽然MCP通过stdio通信，但为了兼容性保留）
EXPOSE 3000

# 设置健康检查（检查Python运行环境和基础配置）
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; import os; from config import DamengConfig; print('Health check passed')" || exit 1

# 注意：所有数据库连接配置必须通过运行时环境变量提供
# 平台将动态注入以下必需的环境变量：
# DAMENG_HOST, DAMENG_PORT, DAMENG_USERNAME, DAMENG_PASSWORD, DAMENG_DATABASE
# 以及可选的安全和配置参数

# 运行MCP服务器
CMD ["python", "main.py"] 