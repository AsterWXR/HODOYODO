FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# 复制后端代码和依赖
COPY server/requirements.txt ./server/
RUN pip install --no-cache-dir -r server/requirements.txt

# 复制前端代码并构建
COPY web/ ./web/
WORKDIR /app/web
RUN npm install && npm run build

# 复制后端代码
WORKDIR /app
COPY server/ ./server/

# 复制前端构建产物到后端静态目录
RUN mkdir -p server/static && cp -r web/dist/* server/static/

WORKDIR /app/server

# 暴露端口
EXPOSE 7860

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
