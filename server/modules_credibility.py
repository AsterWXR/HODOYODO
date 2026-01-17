# server/modules_credibility.py
"""
可信度分析模块：EXIF 提取 + 模糊度检测 + 角度影响评估
"""
from typing import Any, Dict, List, Optional
import io

import numpy as np
import cv2
from PIL import Image, ExifTags


def mk_item(
    claim: str,
    evidence: Optional[List[str]],
    limitations: Optional[List[str]] = None,
    confidence: str = "low",
) -> Dict[str, Any]:
    """构建标准化的分析项（带 evidence gate）"""
    evidence = evidence or []
    limitations = limitations or []

    if len(evidence) == 0:
        return {
            "claim": "无法判断（缺少可引用的画面依据）",
            "evidence": [
                "证据缺失：未提供可指向画面元素/文字/构图/参照物的依据"
            ],
            "limitations": ["信息不足"],
            "confidence": "low",
        }

    return {
        "claim": claim,
        "evidence": evidence,
        "limitations": limitations,
        "confidence": confidence,
    }


def _extract_exif(image_bytes: bytes) -> Dict[str, Any]:
    """
    提取图片 EXIF 元数据
    包括相机信息、拍摄时间、GPS、焦距等
    """
    exif_out = {
        "camera": None,
        "datetime": None,
        "has_gps": False,
        "focal_35mm": None,
        "orientation": None,
        "software": None,
        "raw_tags": {}
    }
    
    try:
        img = Image.open(io.BytesIO(image_bytes))
        exif = img.getexif()
        
        if not exif:
            return exif_out

        # 映射标签名
        tag_map = {}
        for k, v in exif.items():
            tag_name = ExifTags.TAGS.get(k, str(k))
            tag_map[tag_name] = v
            # 保存部分原始标签（用于调试）
            if tag_name in ["Make", "Model", "DateTime", "Software", "FocalLengthIn35mmFilm"]:
                exif_out["raw_tags"][tag_name] = str(v)

        # 相机信息
        make = tag_map.get("Make")
        model = tag_map.get("Model")
        if make or model:
            exif_out["camera"] = f"{make or ''} {model or ''}".strip()

        # 拍摄时间
        exif_out["datetime"] = tag_map.get("DateTimeOriginal") or tag_map.get("DateTime")

        # GPS 信息
        gps = tag_map.get("GPSInfo")
        exif_out["has_gps"] = bool(gps)

        # 35mm 等效焦距
        fl35 = tag_map.get("FocalLengthIn35mmFilm")
        if fl35:
            try:
                exif_out["focal_35mm"] = int(fl35)
            except (ValueError, TypeError):
                pass

        # 图片方向
        exif_out["orientation"] = tag_map.get("Orientation")
        
        # 软件信息（可能暴露编辑痕迹）
        exif_out["software"] = tag_map.get("Software")

    except Exception as e:
        exif_out["_error"] = str(e)
    
    return exif_out


def _blur_score(image_bytes: bytes) -> float:
    """
    计算图片模糊度
    使用 Laplacian 方差法：数值越高通常越清晰
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        arr = np.array(img)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())
    except Exception:
        return -1.0


def _noise_estimate(image_bytes: bytes) -> float:
    """
    估计图片噪声水平（简单版本）
    使用高频分量的标准差
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        arr = np.array(img).astype(np.float32)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        
        # 高通滤波提取高频分量
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        high_freq = gray - blur
        
        return float(np.std(high_freq))
    except Exception:
        return -1.0


def _angle_impact_from_exif(exif: Dict[str, Any]) -> Dict[str, str]:
    """
    评估角度影响（基于焦距的广角畸变风险）
    
    - focal_35mm <= 28: 高风险（广角）
    - 29-50: 中等风险（标准焦段）
    - >50: 低风险（长焦）
    - unknown: 无法评估
    """
    fl = exif.get("focal_35mm")
    
    if fl is None:
        return {
            "level": "未知",
            "evidence": "角度影响：未知（EXIF缺少35mm等效焦距，无法评估广角畸变风险）"
        }

    if fl <= 28:
        return {
            "level": "高",
            "evidence": f"角度影响：高（EXIF显示35mm等效焦距约{fl}mm，广角畸变/透视影响风险更高）"
        }
    if fl <= 50:
        return {
            "level": "中",
            "evidence": f"角度影响：中（EXIF显示35mm等效焦距约{fl}mm，透视影响中等）"
        }
    return {
        "level": "低",
        "evidence": f"角度影响：低（EXIF显示35mm等效焦距约{fl}mm，透视畸变风险相对较低）"
    }


def _check_editing_hints(exif: Dict[str, Any]) -> List[str]:
    """检查可能的编辑痕迹提示"""
    hints = []
    
    software = exif.get("software")
    if software:
        software_lower = str(software).lower()
        # 常见图片编辑软件
        editing_keywords = ["photoshop", "lightroom", "snapseed", "vsco", 
                          "美图", "facetune", "picsart", "gimp"]
        for kw in editing_keywords:
            if kw in software_lower:
                hints.append(f"EXIF 显示软件字段包含 '{software}'（可能经过编辑）")
                break
    
    # 如果没有任何 EXIF 信息，也值得注意
    if not exif.get("camera") and not exif.get("datetime"):
        hints.append("EXIF 元数据几乎为空（可能被清除或来自截图/网络图片）")
    
    return hints


def credibility_module(image_bytes: bytes) -> Dict[str, Any]:
    """
    可信度分析主入口
    
    返回：
    - items: 标准化分析项列表
    - exif: 原始 EXIF 数据
    - blur_score: 模糊度分数
    - angle_impact: 角度影响评估
    """
    exif = _extract_exif(image_bytes)
    blur = _blur_score(image_bytes)
    noise = _noise_estimate(image_bytes)

    items = []
    
    # 1. 清晰度分析
    if blur < 0:
        sharp_text = "清晰度检测失败"
        conf = "low"
    elif blur < 60:
        sharp_text = "画面清晰度偏低（可能存在较强模糊）"
        conf = "medium"
    elif blur < 120:
        sharp_text = "画面清晰度一般（可能存在轻微模糊）"
        conf = "medium"
    else:
        sharp_text = "画面清晰度较好（模糊迹象不明显）"
        conf = "medium"

    items.append(mk_item(
        claim=sharp_text,
        evidence=[
            f"来自画面：模糊度指标（Laplacian 方差）≈ {blur:.1f}（数值越高通常越清晰）"
        ],
        limitations=["模糊度指标受分辨率、噪声、锐化影响；仅作技术线索"],
        confidence=conf,
    ))

    # 2. EXIF 元数据分析
    exif_evidence = []
    if exif.get("camera"):
        exif_evidence.append(f"相机: {exif['camera']}")
    if exif.get("datetime"):
        exif_evidence.append(f"拍摄时间: {exif['datetime']}")
    if exif.get("has_gps"):
        exif_evidence.append("包含 GPS 位置信息")
    if exif.get("focal_35mm"):
        exif_evidence.append(f"35mm等效焦距: {exif['focal_35mm']}mm")
    if exif.get("software"):
        exif_evidence.append(f"软件: {exif['software']}")
    
    if exif_evidence:
        items.append(mk_item(
            claim="EXIF 元数据存在，可辅助判断拍摄设备/时间",
            evidence=[f"来自EXIF：{'; '.join(exif_evidence)}"],
            limitations=["EXIF 可能被清除/篡改；存在不代表一定真实"],
            confidence="low",
        ))
    else:
        items.append(mk_item(
            claim="EXIF 元数据几乎为空",
            evidence=["来自EXIF：未提取到有效元数据（可能已被清除或为截图/网络图片）"],
            limitations=["EXIF 缺失不代表照片不真实，但失去一项验证手段"],
            confidence="low",
        ))

    # 3. 编辑痕迹提示
    editing_hints = _check_editing_hints(exif)
    if editing_hints:
        items.append(mk_item(
            claim="检测到可能的编辑痕迹提示",
            evidence=[f"来自EXIF：{hint}" for hint in editing_hints],
            limitations=["软件标记可能被修改；仅作参考线索"],
            confidence="low",
        ))

    # 角度影响评估
    angle = _angle_impact_from_exif(exif)

    return {
        "items": items,
        "exif": exif,
        "blur_score": blur,
        "noise_estimate": noise,
        "angle_impact": angle,
    }
