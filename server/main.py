# server/main.py
"""
FastAPI 入口 - 网恋照片真实性验证与人物画像分析系统
使用 Gemini 3 多模态模型进行图像分析
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pipeline import analyze_image_bytes

# 加载 .env 文件
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

app = FastAPI(
    title="网恋安全卫士",
    description="你最可靠的网恋侦探",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}


@app.post("/api/analyze")
async def analyze(
    image: UploadFile = File(...),
    target_gender: str = Form(default="boyfriend")
):
    """
    上传图片进行分析
    
    - 支持格式: JPEG, PNG, WebP
    - 最大文件大小: 5MB
    - target_gender: 'boyfriend' 或 'girlfriend'
    
    返回包含以下分析结果:
    - lifestyle: 生活方式线索
    - details: 细节分析
    - intention: 照片意图判断
    - credibility: 可信度分析
    - person: 人物体征估计
    - girlfriend_comments: 口语化吐槽分析
    """
    try:
        if image.content_type not in ALLOWED_MIME:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        data = await image.read()
        if len(data) > MAX_SIZE_BYTES:
            raise HTTPException(status_code=400, detail="File too large (max 5MB)")

        result = await analyze_image_bytes(data, mime=image.content_type, target_gender=target_gender)
        return result
    except HTTPException:
        # 重新抛出 HTTP 异常
        raise
    except Exception as e:
        # 捕获其他未预期的异常
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "provider": "openrouter", "model": os.getenv("OPENROUTER_MODEL", "google/gemini-3-pro-preview")}


# 静态文件服务（Docker部署时使用）
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    # 检查assets目录是否存在
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    
    @app.get("/")
    async def serve_index():
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "网恋安全卫士 API", "docs": "/docs"}
    
    @app.get("/{path:path}")
    async def serve_static(path: str):
        # 跳过 API 路径
        if path.startswith("api/") or path == "health" or path == "docs" or path == "openapi.json":
            return
        try:
            file_path = os.path.join(static_dir, path)
            # 安全检查：防止路径遍历攻击
            file_path = os.path.normpath(file_path)
            if not file_path.startswith(os.path.normpath(static_dir)):
                return {"error": "Invalid path"}
            
            if os.path.exists(file_path) and os.path.isfile(file_path):
                return FileResponse(file_path)
            # 回退到 index.html (SPA)
            index_path = os.path.join(static_dir, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            return {"error": "not found"}
        except Exception as e:
            return {"error": f"Internal error: {str(e)}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
