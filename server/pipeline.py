# server/pipeline.py
"""
统一输出管道 + "无 evidence 自动降级" + 人物 gate 机制
"""
import uuid
from typing import Any, Dict, List, Optional

from qwen_client import analyze_with_qwen
from modules_credibility import credibility_module
from detectors import run_detection
from modules_person import person_module, validate_person_evidence


# ----------------------------
# Schema helpers
# ----------------------------
def mk_item(
    claim: str,
    evidence: Optional[List[str]],
    limitations: Optional[List[str]] = None,
    confidence: str = "low",
) -> Dict[str, Any]:
    """Every conclusion MUST have evidence; otherwise force fallback."""
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


def _build_lifestyle_items(qwen_result: Dict[str, Any], det: Dict[str, Any]) -> List[Dict[str, Any]]:
    """构建生活方式分析项，融合 Qwen 结果和本地检测"""
    items = []
    
    # 从 Qwen 结果获取
    lifestyle = qwen_result.get("lifestyle", {})
    if lifestyle.get("claim") and lifestyle.get("evidence"):
        items.append(mk_item(
            claim=lifestyle.get("claim", "无法判断"),
            evidence=lifestyle.get("evidence", []),
            limitations=lifestyle.get("limitations", ["AI分析存在不确定性"]),
            confidence=lifestyle.get("confidence", "low")
        ))
    
    # 从场景分析获取
    scene = qwen_result.get("scene", {})
    if scene.get("location_type") and scene.get("evidence"):
        items.append(mk_item(
            claim=f"场景判断：{scene.get('location_type')}，{scene.get('environment', '环境特征不明')}",
            evidence=scene.get("evidence", []),
            limitations=["场景判断基于视觉特征，可能存在误判"],
            confidence=scene.get("confidence", "low")
        ))
    
    # 从物体检测获取
    objects = qwen_result.get("objects", {})
    detected_objects = objects.get("detected", [])
    if detected_objects:
        brands = objects.get("brands", [])
        brand_str = f"，识别到品牌：{', '.join(brands)}" if brands else ""
        items.append(mk_item(
            claim=f"画面中检测到物体：{', '.join(detected_objects[:8])}{brand_str}",
            evidence=objects.get("evidence", [f"来自画面：Qwen VL 检测到物体"]),
            limitations=["物体识别可能存在误检/漏检"],
            confidence="low"
        ))
    
    # 补充本地检测结果（如有YOLO）
    if det.get("objects"):
        obj_names = list(set([o["label"] for o in det["objects"][:8]]))
        items.append(mk_item(
            claim=f"本地检测补充：检测到物体 {', '.join(obj_names)}",
            evidence=[f"来自本地检测（引擎：{det.get('engine')}）：物体检测结果"],
            limitations=["本地检测作为辅助参考"],
            confidence="low"
        ))
    
    # 如果没有任何有效项，添加默认项
    if not items:
        items.append(mk_item(
            claim="无法判断具体生活方式线索（缺少可引用物体/场景依据）",
            evidence=["来自流程：未能从画面中提取有效生活方式线索"],
            limitations=["需要更多画面细节支撑"],
            confidence="low"
        ))
    
    return items


def _build_details_items(qwen_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """构建细节分析项"""
    items = []
    
    details = qwen_result.get("details", {})
    
    # 文字检测
    text_detected = details.get("text_detected", [])
    if text_detected:
        items.append(mk_item(
            claim=f"画面中识别到文字：{', '.join(text_detected[:5])}",
            evidence=[f"来自画面：Qwen VL 文字识别结果"],
            limitations=["文字识别可能存在误读"],
            confidence="medium"
        ))
    
    # 特殊元素
    special = details.get("special_elements", [])
    if special:
        items.append(mk_item(
            claim=f"检测到特殊元素：{', '.join(special)}",
            evidence=details.get("evidence", ["来自画面：特殊元素分析"]),
            limitations=["特殊元素判断存在主观性"],
            confidence="low"
        ))
    
    # 如果没有检测到任何细节
    if not items:
        items.append(mk_item(
            claim="未检测到显著文字/特殊元素（或识别置信度过低）",
            evidence=["来自流程：Qwen VL 未返回有效细节信息"],
            limitations=["可接入专业 OCR 增强文字识别能力"],
            confidence="low"
        ))
    
    return items


def _build_intention_items(qwen_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """构建意图分析项"""
    items = []
    
    intention = qwen_result.get("intention", {})
    if intention.get("claim") and intention.get("evidence"):
        items.append(mk_item(
            claim=intention.get("claim"),
            evidence=intention.get("evidence"),
            limitations=["照片意图判断存在较大不确定性，仅供参考"],
            confidence=intention.get("confidence", "low")
        ))
    else:
        items.append(mk_item(
            claim="照片用途倾向暂无法稳定判断（展示/记录/正式用途均可能）",
            evidence=[
                "来自流程：缺少足够的构图/语义线索支撑意图判断"
            ],
            limitations=["需要构图特征+文字+场景识别联合判断"],
            confidence="low"
        ))
    
    return items


def _build_room_analysis(qwen_result: Dict[str, Any]) -> Dict[str, Any]:
    """构建房间人数和关系推断分析"""
    room = qwen_result.get("room_analysis", {})
    
    # 默认值
    default_result = {
        "inferred_people_count": "无法判断",
        "relationship_hint": "无法判断",
        "evidence": ["来自流程：未能从画面中提取有效的环境线索"],
        "clues": {
            "tableware": "未见相关线索",
            "seating": "未见相关线索",
            "personal_items": "未见相关线索",
            "decoration": "未见相关线索",
            "space_layout": "未见相关线索"
        },
        "limitations": ["环境推断存在较大不确定性，仅供参考"],
        "confidence": "low"
    }
    
    if not room:
        return default_result
    
    # 检查是否有有效的 evidence
    evidence = room.get("evidence", [])
    if not evidence or all("未见" in str(e) or "无法" in str(e) for e in evidence):
        # 证据不足，强制降级
        return {
            "inferred_people_count": "无法判断",
            "relationship_hint": "无法判断",
            "evidence": evidence if evidence else ["来自环境：未检测到可用于推断人数/关系的线索"],
            "clues": room.get("clues", default_result["clues"]),
            "limitations": room.get("limitations", default_result["limitations"]),
            "confidence": "low"
        }
    
    # 有有效证据，返回 Qwen 的分析结果
    return {
        "inferred_people_count": room.get("inferred_people_count", "无法判断"),
        "relationship_hint": room.get("relationship_hint", "无法判断"),
        "evidence": evidence,
        "clues": room.get("clues", default_result["clues"]),
        "limitations": room.get("limitations", default_result["limitations"]),
        "confidence": room.get("confidence", "low")
    }


async def analyze_image_bytes(image_bytes: bytes, mime: str, target_gender: str = "boyfriend") -> Dict[str, Any]:
    """
    主分析流程
    
    1. 本地检测（EXIF/模糊度/HOG或YOLO）
    2. Qwen VL 多模态分析
    3. 融合结果 + evidence gate 校验
    
    Args:
        image_bytes: 图片二进制数据
        mime: MIME类型
        target_gender: 分析对象性别 ('boyfriend' 或 'girlfriend')
    """
    image_id = uuid.uuid4().hex[:8]

    # 1) 可信度/EXIF/质量分析（本地）
    cred = credibility_module(image_bytes)

    # 2) 本地检测（person + 参照物候选）
    det = run_detection(image_bytes)

    # 3) 调用 Qwen VL 进行多模态分析
    # 将本地检测结果作为辅助上下文
    extra_context = {
        "local_detection": {
            "engine": det.get("engine"),
            "person_count": len(det.get("persons", [])),
            "reference_objects": [o["label"] for o in det.get("reference_objects", [])],
        },
        "exif": cred.get("exif", {}),
        "blur_score": cred.get("blur_score"),
        "angle_impact": cred.get("angle_impact", {}).get("level", "未知")
    }
    
    qwen_result = await analyze_with_qwen(
        image_bytes=image_bytes,
        mime=mime,
        extra_context=extra_context,
        target_gender=target_gender
    )

    # 4) 人物体征分析（严格 evidence gate）
    person = person_module(det, cred, qwen_result)

    # 5) 构建各分析模块输出
    if qwen_result.get("_success"):
        lifestyle_items = _build_lifestyle_items(qwen_result, det)
        details_items = _build_details_items(qwen_result)
        intention_items = _build_intention_items(qwen_result)
        room_analysis = _build_room_analysis(qwen_result)
    else:
        # Qwen 调用失败，使用保守的本地结果
        lifestyle_items = []
        if det.get("objects"):
            obj_names = [o["label"] for o in det["objects"][:8]]
            lifestyle_items.append(mk_item(
                claim="画面中检测到若干物体（仅作线索，AI分析暂不可用）",
                evidence=[f"来自本地检测：检测到物体 {', '.join(obj_names)}（引擎：{det.get('engine')}）"],
                limitations=["Qwen VL 调用失败，仅使用本地检测结果"],
                confidence="low"
            ))
        else:
            lifestyle_items.append(mk_item(
                claim="无法判断生活方式线索",
                evidence=["来自流程：AI 分析暂不可用，本地检测未发现物体"],
                limitations=["请检查 API 配置后重试"],
                confidence="low"
            ))
        
        details_items = [mk_item(
            claim="细节分析暂不可用",
            evidence=["来自流程：Qwen VL 调用失败"],
            limitations=[qwen_result.get("_error", "未知错误")],
            confidence="low"
        )]
        
        intention_items = [mk_item(
            claim="意图分析暂不可用",
            evidence=["来自流程：Qwen VL 调用失败"],
            limitations=[qwen_result.get("_error", "未知错误")],
            confidence="low"
        )]
        
        room_analysis = {
            "inferred_people_count": "无法判断",
            "relationship_hint": "无法判断",
            "evidence": ["来自流程：Qwen VL 调用失败，无法进行环境分析"],
            "clues": {},
            "limitations": [qwen_result.get("_error", "未知错误")],
            "confidence": "low"
        }

    # 6) 可信度项
    credibility_items = cred["items"]

    return {
        "image_id": image_id,
        "analysis": {
            "lifestyle": {"items": lifestyle_items},
            "details": {"items": details_items},
            "intention": {"items": intention_items},
            "credibility": {"items": credibility_items},
            "person": person,
            "room_analysis": room_analysis,
        },
        "girlfriend_comments": qwen_result.get("girlfriend_comments", []),
        "_meta": {
            "model": qwen_result.get("_model", "unknown"),
            "model_success": qwen_result.get("_success", False),
            "local_engine": det.get("engine", "unknown")
        }
    }
