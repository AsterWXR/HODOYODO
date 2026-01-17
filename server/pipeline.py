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
# 品牌价格区间数据库
# ----------------------------
BRAND_PRICE_DATABASE = {
    # 奢侈品 - 的体价格区间（单位：人民币）
    "luxury": {
        # 奢侈品包袋
        "LV": {"tier": "奢侈品", "price_range": "8000-80000+", "category": "包袋/服饰"},
        "Gucci": {"tier": "奢侈品", "price_range": "5000-50000+", "category": "包袋/服饰"},
        "Chanel": {"tier": "奢侈品", "price_range": "10000-100000+", "category": "包袋/化妆品"},
        "Hermes": {"tier": "顶奢", "price_range": "30000-200000+", "category": "包袋/配饰"},
        "爱马仕": {"tier": "顶奢", "price_range": "30000-200000+", "category": "包袋/配饰"},
        "Prada": {"tier": "奢侈品", "price_range": "6000-40000+", "category": "包袋/服饰"},
        "Dior": {"tier": "奢侈品", "price_range": "5000-50000+", "category": "包袋/化妆品"},
        "Burberry": {"tier": "奢侈品", "price_range": "3000-30000+", "category": "服饰/包袋"},
        "Fendi": {"tier": "奢侈品", "price_range": "5000-40000+", "category": "包袋"},
        "Bottega Veneta": {"tier": "奢侈品", "price_range": "8000-50000+", "category": "包袋"},
        "BV": {"tier": "奢侈品", "price_range": "8000-50000+", "category": "包袋"},
        "Celine": {"tier": "奢侈品", "price_range": "6000-40000+", "category": "包袋"},
        "Saint Laurent": {"tier": "奢侈品", "price_range": "5000-35000+", "category": "包袋/服饰"},
        "YSL": {"tier": "奢侈品", "price_range": "5000-35000+", "category": "包袋/化妆品"},
        "Balenciaga": {"tier": "奢侈品", "price_range": "4000-30000+", "category": "包袋/鞋履"},
        "Loewe": {"tier": "奢侈品", "price_range": "8000-40000+", "category": "包袋"},
        # 奢侈手表
        "Rolex": {"tier": "顶奢", "price_range": "50000-500000+", "category": "手表"},
        "劳力士": {"tier": "顶奢", "price_range": "50000-500000+", "category": "手表"},
        "Omega": {"tier": "奢侈品", "price_range": "20000-150000+", "category": "手表"},
        "欧米茄": {"tier": "奢侈品", "price_range": "20000-150000+", "category": "手表"},
        "Cartier": {"tier": "顶奢", "price_range": "30000-300000+", "category": "手表/珠宝"},
        "卡地亚": {"tier": "顶奢", "price_range": "30000-300000+", "category": "手表/珠宝"},
        "Patek Philippe": {"tier": "顶奢", "price_range": "150000-3000000+", "category": "手表"},
        "百达翡丽": {"tier": "顶奢", "price_range": "150000-3000000+", "category": "手表"},
        # 高端护肤品
        "La Mer": {"tier": "高端护肤", "price_range": "1500-5000+", "category": "护肤品"},
        "海蓝之谜": {"tier": "高端护肤", "price_range": "1500-5000+", "category": "护肤品"},
        "SK-II": {"tier": "高端护肤", "price_range": "800-2500+", "category": "护肤品"},
        "雅诗兰黛": {"tier": "高端护肤", "price_range": "500-2000+", "category": "护肤品"},
        "Estee Lauder": {"tier": "高端护肤", "price_range": "500-2000+", "category": "护肤品"},
        "CPB": {"tier": "高端护肤", "price_range": "800-3000+", "category": "护肤品"},
        "肩邦御": {"tier": "高端护肤", "price_range": "800-3000+", "category": "护肤品"},
        "HR": {"tier": "高端护肤", "price_range": "1000-4000+", "category": "护肤品"},
        "赫莲娜": {"tier": "高端护肤", "price_range": "1000-4000+", "category": "护肤品"},
    },
    # 轻奢品牌
    "light_luxury": {
        "Coach": {"tier": "轻奢", "price_range": "1500-8000", "category": "包袋"},
        "Michael Kors": {"tier": "轻奢", "price_range": "1000-5000", "category": "包袋"},
        "MK": {"tier": "轻奢", "price_range": "1000-5000", "category": "包袋"},
        "Kate Spade": {"tier": "轻奢", "price_range": "1000-4000", "category": "包袋"},
        "Tory Burch": {"tier": "轻奢", "price_range": "1500-6000", "category": "包袋/鞋"},
        "Marc Jacobs": {"tier": "轻奢", "price_range": "1500-5000", "category": "包袋"},
        "Longchamp": {"tier": "轻奢", "price_range": "600-3000", "category": "包袋"},
        "珑骏": {"tier": "轻奢", "price_range": "600-3000", "category": "包袋"},
        "MCM": {"tier": "轻奢", "price_range": "2000-8000", "category": "包袋"},
        # 轻奢手表
        "Tissot": {"tier": "轻奢", "price_range": "2000-10000", "category": "手表"},
        "天梭": {"tier": "轻奢", "price_range": "2000-10000", "category": "手表"},
        "Longines": {"tier": "轻奢", "price_range": "8000-30000", "category": "手表"},
        "浪琴": {"tier": "轻奢", "price_range": "8000-30000", "category": "手表"},
        # 中端护肤品
        "兰蔻": {"tier": "中端护肤", "price_range": "300-1200", "category": "护肤品"},
        "Lancome": {"tier": "中端护肤", "price_range": "300-1200", "category": "护肤品"},
        "雅漾": {"tier": "中端护肤", "price_range": "150-500", "category": "护肤品"},
        "科颜氏": {"tier": "中端护肤", "price_range": "200-800", "category": "护肤品"},
        "欧舒丹": {"tier": "中端护肤", "price_range": "150-600", "category": "护肤品"},
    },
    # 运动品牌
    "sports": {
        "Nike": {"tier": "运动品牌", "price_range": "300-2000", "category": "运动服饰/鞋"},
        "耐克": {"tier": "运动品牌", "price_range": "300-2000", "category": "运动服饰/鞋"},
        "Adidas": {"tier": "运动品牌", "price_range": "300-1500", "category": "运动服饰/鞋"},
        "阿迪达斯": {"tier": "运动品牌", "price_range": "300-1500", "category": "运动服饰/鞋"},
        "Lululemon": {"tier": "高端运动", "price_range": "500-1500", "category": "运动服饰"},
        "Under Armour": {"tier": "运动品牌", "price_range": "200-1000", "category": "运动服饰"},
        "New Balance": {"tier": "运动品牌", "price_range": "400-1500", "category": "运动鞋"},
        "Puma": {"tier": "运动品牌", "price_range": "200-1000", "category": "运动服饰/鞋"},
        "Converse": {"tier": "休闲品牌", "price_range": "300-800", "category": "鞋"},
        "Vans": {"tier": "休闲品牌", "price_range": "300-700", "category": "鞋"},
    },
    # 快时尚/大众品牌
    "fast_fashion": {
        "Zara": {"tier": "快时尚", "price_range": "100-800", "category": "服饰"},
        "H&M": {"tier": "快时尚", "price_range": "50-500", "category": "服饰"},
        "优衣库": {"tier": "快时尚", "price_range": "50-500", "category": "服饰"},
        "Uniqlo": {"tier": "快时尚", "price_range": "50-500", "category": "服饰"},
        "GAP": {"tier": "快时尚", "price_range": "100-600", "category": "服饰"},
        "UR": {"tier": "快时尚", "price_range": "100-500", "category": "服饰"},
        # 大众护肤
        "大宝": {"tier": "大众护肤", "price_range": "20-80", "category": "护肤品"},
        "美加净": {"tier": "大众护肤", "price_range": "20-60", "category": "护肤品"},
        "百雀羚": {"tier": "大众护肤", "price_range": "30-100", "category": "护肤品"},
    },
    # 电子产品
    "electronics": {
        "iPhone": {"tier": "高端电子", "price_range": "5000-15000", "category": "手机"},
        "Apple": {"tier": "高端电子", "price_range": "2000-30000", "category": "电子产品"},
        "苹果": {"tier": "高端电子", "price_range": "2000-30000", "category": "电子产品"},
        "MacBook": {"tier": "高端电子", "price_range": "8000-25000", "category": "电脑"},
        "AirPods": {"tier": "高端电子", "price_range": "1000-2000", "category": "耳机"},
        "AirPods Pro": {"tier": "高端电子", "price_range": "1500-2000", "category": "耳机"},
        "iPad": {"tier": "高端电子", "price_range": "2500-12000", "category": "平板"},
        "Apple Watch": {"tier": "高端电子", "price_range": "2000-8000", "category": "智能手表"},
        "Samsung": {"tier": "中高端电子", "price_range": "2000-10000", "category": "电子产品"},
        "三星": {"tier": "中高端电子", "price_range": "2000-10000", "category": "电子产品"},
        "Sony": {"tier": "中高端电子", "price_range": "1500-8000", "category": "电子产品"},
        "索尼": {"tier": "中高端电子", "price_range": "1500-8000", "category": "电子产品"},
        "华为": {"tier": "中高端电子", "price_range": "2000-8000", "category": "电子产品"},
        "Huawei": {"tier": "中高端电子", "price_range": "2000-8000", "category": "电子产品"},
        "小米": {"tier": "大众电子", "price_range": "1000-5000", "category": "电子产品"},
        "Xiaomi": {"tier": "大众电子", "price_range": "1000-5000", "category": "电子产品"},
    }
}


def lookup_brand_info(brand_name: str) -> Optional[Dict[str, str]]:
    """查找品牌信息"""
    # 遍历所有分类查找
    for category_brands in BRAND_PRICE_DATABASE.values():
        # 精确匹配
        if brand_name in category_brands:
            return category_brands[brand_name]
        # 模糊匹配（大小写不敏感）
        for key, value in category_brands.items():
            if brand_name.lower() == key.lower():
                return value
    return None


def enrich_brands_with_price(brands_detected: Dict[str, List[str]]) -> Dict[str, Any]:
    """
    为识别到的品牌添加价格区间信息
    
    Returns:
        {
            "items": [
                {"brand": "LV", "tier": "奢侈品", "price_range": "8000-80000+", "category": "包袋/服饰"},
                ...
            ],
            "summary": "识别到1个奢侈品牌、2个运动品牌",
            "highest_tier": "奢侈品"
        }
    """
    if not brands_detected:
        return {"items": [], "summary": "未识别到品牌", "highest_tier": None}
    
    items = []
    tier_count = {}
    
    # 遍历所有品牌分类
    for category, brand_list in brands_detected.items():
        if not brand_list:
            continue
        for brand in brand_list:
            if not brand or brand == "未识别到品牌":
                continue
            info = lookup_brand_info(brand)
            if info:
                items.append({
                    "brand": brand,
                    "tier": info["tier"],
                    "price_range": f"¥{info['price_range']}",
                    "category": info["category"]
                })
                tier_count[info["tier"]] = tier_count.get(info["tier"], 0) + 1
            else:
                # 未知品牌
                items.append({
                    "brand": brand,
                    "tier": "未知",
                    "price_range": "未知",
                    "category": category
                })
    
    # 生成摘要
    if tier_count:
        parts = [f"{count}个{tier}" for tier, count in tier_count.items()]
        separator = "、"  # 顿号
        summary = f"识别到{separator.join(parts)}"
    else:
        summary = "未识别到已知品牌"
    
    # 确定最高档次
    tier_order = ["顶奢", "奢侈品", "高端护肤", "高端电子", "轻奢", "中端护肤", "高端运动", "运动品牌", "中高端电子", "快时尚", "休闲品牌", "大众护肤", "大众电子"]
    highest_tier = None
    for tier in tier_order:
        if tier in tier_count:
            highest_tier = tier
            break
    
    return {
        "items": items,
        "summary": summary,
        "highest_tier": highest_tier
    }

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
    """构建房间人数和关系推断分析
    
    注意：室外场景不进行室内物品分析
    """
    room = qwen_result.get("room_analysis", {})
    scene = qwen_result.get("scene", {})
    
    # 检查是否为室外场景
    location_type = scene.get("location_type", "")
    is_outdoor = "室外" in location_type
    
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
    
    # 室外场景：不进行室内物品分析（拖鞋、牙刷、餐具等）
    if is_outdoor:
        return {
            "inferred_people_count": "不适用",
            "relationship_hint": "不适用",
            "evidence": ["来自场景：室外场景不进行室内物品分析"],
            "clues": {
                "tableware": "不适用（室外场景）",
                "seating": "不适用（室外场景）",
                "personal_items": "不适用（室外场景）",
                "decoration": "不适用（室外场景）",
                "space_layout": "不适用（室外场景）"
            },
            "limitations": ["室外场景无法进行室内环境推断"],
            "confidence": "low",
            "is_outdoor": True
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
        
        # 提取品牌价格信息
        lifestyle_raw = qwen_result.get("lifestyle", {})
        brands_detected = lifestyle_raw.get("brands_detected", {})
        brands_info = enrich_brands_with_price(brands_detected)
        
        # 构建完整的 lifestyle 输出
        lifestyle_output = {
            "items": lifestyle_items,
            "consumption_level": lifestyle_raw.get("consumption_level", "无法判断"),
            "accommodation_level": lifestyle_raw.get("accommodation_level", "无法判断"),
            "brands_detected": brands_detected,
            "brands_info": brands_info  # 新增：带价格区间的品牌信息
        }
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
        
        # 空的品牌信息
        brands_info = {"items": [], "summary": "未识别到品牌", "highest_tier": None}
        lifestyle_output = {
            "items": lifestyle_items,
            "consumption_level": "无法判断",
            "accommodation_level": "无法判断",
            "brands_detected": {},
            "brands_info": brands_info
        }

    # 6) 可信度项
    credibility_items = cred["items"]

    return {
        "image_id": image_id,
        "analysis": {
            "lifestyle": lifestyle_output,  # 修改：使用包含品牌信息的完整输出
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
