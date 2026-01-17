# server/detectors.py
"""
本地检测模块：HOG 默认 + 可选 YOLO
提供 person 检测和参照物候选
"""
from typing import Any, Dict, List, Optional
import io

import numpy as np
import cv2
from PIL import Image


# 常见可作为"参照物存在性线索"的类别（COCO 数据集类别）
COCO_REFERENCE_HINTS = {
    # 家具类（可估算相对尺寸）
    "chair", "couch", "bench", "dining table", "bed",
    # 电子设备（尺寸相对标准）
    "tv", "laptop", "cell phone", "remote",
    # 日用品（尺寸可参考）
    "bottle", "cup", "wine glass", "fork", "knife", "spoon",
    # 个人物品
    "backpack", "handbag", "suitcase", "umbrella",
    # 交通工具（如有）
    "car", "bicycle", "motorcycle",
    # 门/窗等建筑元素
    "door", "window"
}


def _decode_to_bgr(image_bytes: bytes) -> np.ndarray:
    """将图片字节解码为 BGR 格式的 numpy 数组"""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    arr = np.array(img)
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def _get_image_dimensions(image_bytes: bytes) -> Dict[str, int]:
    """获取图片尺寸"""
    img = Image.open(io.BytesIO(image_bytes))
    return {"width": img.width, "height": img.height}


def _hog_person_detect(bgr: np.ndarray) -> List[Dict[str, Any]]:
    """
    使用 OpenCV HOG 描述符进行行人检测
    轻量级，不需要额外模型文件
    """
    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    h, w = bgr.shape[:2]
    scale = 1.0
    
    # 缩放大图以提高速度
    if max(h, w) > 1200:
        scale = 1200 / max(h, w)
        bgr_small = cv2.resize(bgr, (int(w * scale), int(h * scale)))
    else:
        bgr_small = bgr

    rects, weights = hog.detectMultiScale(
        bgr_small, 
        winStride=(8, 8), 
        padding=(8, 8), 
        scale=1.05
    )
    
    persons = []
    for (x, y, rw, rh), wt in zip(rects, weights):
        # 映射回原始尺寸
        x0 = int(x / scale)
        y0 = int(y / scale)
        x1 = int((x + rw) / scale)
        y1 = int((y + rh) / scale)
        
        # 计算检测框占图片的比例
        box_height = y1 - y0
        box_width = x1 - x0
        height_ratio = box_height / h
        width_ratio = box_width / w
        
        persons.append({
            "label": "person",
            "conf": float(wt),
            "bbox": [x0, y0, x1, y1],
            "box_height_ratio": round(height_ratio, 3),
            "box_width_ratio": round(width_ratio, 3),
            "is_full_body": height_ratio > 0.6,  # 粗略判断是否全身
        })
    
    return persons


def _try_yolo_detect(bgr: np.ndarray) -> Optional[Dict[str, Any]]:
    """
    可选：如果安装了 ultralytics，使用 YOLO 进行更精确的检测
    返回 {persons:[], objects:[], engine:"yolo"} 或 None（不可用时）
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        return None
    except Exception:
        return None

    try:
        # 使用默认模型（首次运行会自动下载）
        model = YOLO("yolov8n.pt")

        # 推理
        res = model.predict(source=bgr, verbose=False)[0]
        names = res.names
        h, w = bgr.shape[:2]

        persons = []
        objects = []
        
        for box in res.boxes:
            cls_id = int(box.cls[0].item())
            label = names.get(cls_id, str(cls_id))
            conf = float(box.conf[0].item())
            x0, y0, x1, y1 = [float(v) for v in box.xyxy[0].tolist()]
            
            box_height = y1 - y0
            box_width = x1 - x0
            height_ratio = box_height / h
            width_ratio = box_width / w
            
            item = {
                "label": label, 
                "conf": round(conf, 3), 
                "bbox": [int(x0), int(y0), int(x1), int(y1)],
                "box_height_ratio": round(height_ratio, 3),
                "box_width_ratio": round(width_ratio, 3),
            }
            
            if label == "person":
                item["is_full_body"] = height_ratio > 0.6
                persons.append(item)
            else:
                objects.append(item)

        return {"engine": "yolo", "persons": persons, "objects": objects}
        
    except Exception as e:
        print(f"[YOLO] Detection failed: {e}")
        return None


def _analyze_person_visibility(persons: List[Dict[str, Any]], img_h: int) -> Dict[str, str]:
    """
    分析人物可见性：全身/上半身/头肩等
    基于检测框的高度比例进行判断
    """
    if not persons:
        return {"visibility": "不可见", "detail": "未检测到人物"}
    
    # 取置信度最高的人
    main_person = max(persons, key=lambda x: x.get("conf", 0))
    height_ratio = main_person.get("box_height_ratio", 0)
    
    if height_ratio > 0.75:
        return {"visibility": "可见全身", "detail": f"人物检测框占画面高度约{height_ratio*100:.0f}%"}
    elif height_ratio > 0.5:
        return {"visibility": "大部分可见", "detail": f"人物检测框占画面高度约{height_ratio*100:.0f}%，可能为全身或七分身"}
    elif height_ratio > 0.3:
        return {"visibility": "仅上半身", "detail": f"人物检测框占画面高度约{height_ratio*100:.0f}%，推测为上半身"}
    else:
        return {"visibility": "仅头肩", "detail": f"人物检测框占画面高度约{height_ratio*100:.0f}%，推测为头肩或局部"}


def run_detection(image_bytes: bytes) -> Dict[str, Any]:
    """
    主检测入口
    优先使用 YOLO（如已安装），否则回退到 HOG
    """
    bgr = _decode_to_bgr(image_bytes)
    dims = _get_image_dimensions(image_bytes)
    h, w = dims["height"], dims["width"]

    # 优先尝试 YOLO
    yolo = _try_yolo_detect(bgr)
    if yolo is not None:
        # 添加参照物筛选
        yolo["reference_objects"] = [
            o for o in yolo["objects"] 
            if o["label"] in COCO_REFERENCE_HINTS
        ]
        # 添加人物可见性分析
        yolo["person_visibility"] = _analyze_person_visibility(yolo["persons"], h)
        yolo["image_dims"] = dims
        return yolo

    # 回退到 HOG（仅检测人物）
    persons = _hog_person_detect(bgr)
    
    return {
        "engine": "hog",
        "persons": persons,
        "objects": [],
        "reference_objects": [],
        "person_visibility": _analyze_person_visibility(persons, h),
        "image_dims": dims,
    }
