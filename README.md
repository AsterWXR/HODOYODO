# 网恋安全卫士 (HODOYODO)

基于多模态 AI 的网恋照片真实性验证工具

## 快速开始

### 1. 环境要求

- Python 3.11+
- Node.js 18+
- 通义千问 API Key

### 2. 后端启动

```bash
cd server

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 DASHSCOPE_API_KEY

# 启动服务
python main.py
```

### 3. 前端启动

```bash
cd web

# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build
```

### 4. Docker 部署

```bash
# 构建镜像
docker build -t hodoyodo .

# 运行容器
docker run -p 7860:7860 -e DASHSCOPE_API_KEY=你的key hodoyodo
```

### 5. ModelScope 部署

1. 上传代码到 GitHub
2. 在 ModelScope 创建 Studio
3. 选择 Docker 部署，使用 `deploy.json` 配置
4. 设置环境变量 `DASHSCOPE_API_KEY`

## 项目结构

```
├── server/          # Python 后端
│   ├── main.py      # FastAPI 入口
│   ├── pipeline.py  # 分析流程
│   └── qwen_client.py  # AI 模型调用
├── web/             # React 前端
│   └── src/
├── Dockerfile       # Docker 配置
└── deploy.json      # ModelScope 部署配置
```

## 环境变量

| 变量名 | 说明 | 必填 |
|--------|------|------|
| DASHSCOPE_API_KEY | 通义千问 API Key | ✅ |
| PORT | 服务端口 | ❌ |
