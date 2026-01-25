# 环境变量配置说明

## 必需的环境变量

### OPENROUTER_API_KEY
- **说明**: OpenRouter API 密钥，用于调用 Gemini 3 多模态模型进行图像分析
- **获取方式**: 访问 https://openrouter.ai/keys 注册并获取 API Key
- **示例**: `OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx`

## 可选的环境变量

### OPENROUTER_MODEL
- **说明**: 指定使用的 OpenRouter 模型
- **默认值**: `google/gemini-3-pro-preview`
- **示例**: `OPENROUTER_MODEL=google/gemini-3-pro-preview`

### PORT
- **说明**: 后端服务监听端口
- **默认值**: `8000`
- **示例**: `PORT=8000`

## 配置方式

### Windows PowerShell
```powershell
$env:OPENROUTER_API_KEY="你的API密钥"
$env:OPENROUTER_MODEL="google/gemini-3-pro-preview"
```

### Windows CMD
```cmd
set OPENROUTER_API_KEY=你的API密钥
set OPENROUTER_MODEL=google/gemini-3-pro-preview
```

### macOS/Linux
```bash
export OPENROUTER_API_KEY="你的API密钥"
export OPENROUTER_MODEL="google/gemini-3-pro-preview"
```

### 使用 .env 文件（推荐）
1. 在项目根目录创建 `.env` 文件
2. 添加以下内容：
```
OPENROUTER_API_KEY=你的API密钥
OPENROUTER_MODEL=google/gemini-3-pro-preview
PORT=8000
```

注意：`.env` 文件不应提交到版本控制系统，请确保已添加到 `.gitignore`
