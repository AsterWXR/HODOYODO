# server/main.py
"""
FastAPI 入口 - 网恋照片真实性验证与人物画像分析系统
使用 Qwen VL 多模态模型进行图像分析
"""
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pipeline import analyze_image_bytes

app = FastAPI(
    title="网恋安全卫士",
    description="你最可靠的网恋侦探",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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
    if image.content_type not in ALLOWED_MIME:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    data = await image.read()
    if len(data) > MAX_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")

    result = await analyze_image_bytes(data, mime=image.content_type, target_gender=target_gender)
    return result


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "model": "qwen-vl-plus"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
