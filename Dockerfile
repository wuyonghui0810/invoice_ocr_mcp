# 使用官方Python基础镜像
FROM python:3.11-slim as base

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-0 \
    libgthread-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 创建应用用户
RUN useradd --create-home --shell /bin/bash app

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt pyproject.toml ./

# 创建虚拟环境并安装Python依赖
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# 开发环境阶段
FROM base as development

# 安装开发依赖
RUN pip install pytest pytest-asyncio pytest-mock pytest-cov \
    black flake8 isort mypy

# 复制源代码
COPY --chown=app:app . .

# 切换到应用用户
USER app

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "src/invoice_ocr_mcp/server.py"]

# 生产环境阶段
FROM base as production

# 复制源代码
COPY --chown=app:app src/ /app/src/
COPY --chown=app:app configs/ /app/configs/
COPY --chown=app:app scripts/ /app/scripts/

# 安装应用
COPY --chown=app:app pyproject.toml ./
RUN pip install -e .

# 创建必要的目录
RUN mkdir -p /app/logs /app/data /app/cache && \
    chown -R app:app /app/logs /app/data /app/cache

# 设置健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import asyncio; import aiohttp; asyncio.run(aiohttp.ClientSession().get('http://localhost:8000/health').close())" || exit 1

# 切换到应用用户
USER app

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "-m", "invoice_ocr_mcp.server"]

# GPU支持版本
FROM nvidia/cuda:11.8-runtime-ubuntu20.04 as gpu

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装Python和系统依赖
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    gcc \
    g++ \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 创建Python3.11符号链接
RUN ln -s /usr/bin/python3.11 /usr/bin/python

# 设置工作目录
WORKDIR /app

# 复制并安装依赖
COPY requirements.txt pyproject.toml ./
RUN pip install --upgrade pip setuptools wheel && \
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118 && \
    pip install -r requirements.txt

# 复制源代码
COPY src/ /app/src/
COPY configs/ /app/configs/

# 安装应用
RUN pip install -e .

# 创建应用用户
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app

USER app

# 暴露端口
EXPOSE 8000

# GPU版本启动命令
CMD ["python", "-m", "invoice_ocr_mcp.server", "--gpu"] 