# server/modules_person.py
"""
人物体征分析模块（严格 evidence gate + 三元证据字段）

人物体征估计规则：
- 身高：只能输出 "偏高/中等/偏矮/无法判断"
- 体型：只能输出 "偏瘦/匀称/偏壮/无法判断"
- 姿态：只能输出 "挺拔/放松/含胸/不确定"
- 性别：只能输出 "男性/女性/无法判断"

evidence 必须包含三要素：
- 参照物：画面中可用于参照的物体
- 全身：是否可见全身轮廓
- 角度影响：拍摄角度对判断的影响

如果 evidence 缺少任何一个要素，强制降级。
"""
from typing import Any, Dict, List, Optional, Tuple


# 人物体征 evidence 必须包含的三个关键字段
REQUIRED_EVIDENCE_KEYS = ["参照物", "全身", "角度影响"]

# 允许的输出值
VALID_HEIGHT = {"偏高", "中等", "偏矮", "无法判断"}
VALID_BODY_TYPE = {"偏瘦", "匀称", "偏壮", "无法判断"}
VALID_POSTURE = {"挺拔", "放松", "含胸", "不确定"}
VALID_GENDER = {"男性", "女性", "无法判断"}


def validate_person_evidence(evidence: Dict[str, str]) -> Tuple[bool, List[str]]:
    """
    验证人物体征 evidence 是否满足三要素要求
    
    Returns:
        (is_valid, missing_keys)
    """
    if not evidence:
        return False, REQUIRED_EVIDENCE_KEYS.copy()
    
    # 检查三个关键字段
    evidence_blob = " ".join(str(v) for v in evidence.values())
    missing = []
    
    for key in REQUIRED_EVIDENCE_KEYS:
        if key not in evidence_blob:
            # 检查是否有对应的字段
            has_field = False
            for k, v in evidence.items():
                if key in k or key in str(v):
                    has_field = True
                    break
            if not has_field:
                missing.append(key)
    
    return len(missing) == 0, missing


def _normalize_height(value: str) -> str:
    """规范化身高输出"""
    if not value:
        return "无法判断"
    value = str(value).strip()
    if value in VALID_HEIGHT:
        return value
    # 尝试模糊匹配
    if "高" in value and "偏" not in value:
        return "偏高"
    if "矮" in value:
        return "偏矮"
    if "中" in value:
        return "中等"
    return "无法判断"


def _normalize_body_type(value: str) -> str:
    """
    规范化体型输出
    
    支持多种描述方式的识别：
    - 偏瘦：瘦、纤细、苗条、消瘦、单薄、骨感等
    - 偏壮：壮、胖、丰满、结实、健壮、圆润、有肉等
    - 匀称：匀称、正常、适中、标准、中等、健康等
    """
    if not value:
        return "无法判断"
    value = str(value).strip()
    
    # 精确匹配
    if value in VALID_BODY_TYPE:
        return value
    
    # 偏瘦类关键词（优先级高）
    slim_keywords = ["瘦", "纤细", "苗条", "消瘦", "单薄", "骨感", "瘦弱", "瘦小", "修长"]
    for kw in slim_keywords:
        if kw in value:
            return "偏瘦"
    
    # 偏壮类关键词
    fat_keywords = ["壮", "胖", "丰满", "结实", "健壮", "圆润", "有肉", "赘肉", "粗壮", "高大", "吧商", "厚实", "肉感"]
    for kw in fat_keywords:
        if kw in value:
            return "偏壮"
    
    # 匀称类关键词（范围最广，放最后匹配）
    normal_keywords = ["匀称", "正常", "适中", "标准", "中等", "健康", "普通", "一般", "平均"]
    for kw in normal_keywords:
        if kw in value:
            return "匀称"
    
    return "无法判断"


def _normalize_posture(value: str) -> str:
    """规范化姿态输出"""
    if not value:
        return "不确定"
    value = str(value).strip()
    if value in VALID_POSTURE:
        return value
    # 尝试模糊匹配
    if "挺" in value:
        return "挺拔"
    if "放松" in value or "松弛" in value:
        return "放松"
    if "含胸" in value or "驼背" in value:
        return "含胸"
    return "不确定"


def _normalize_gender(value: str) -> str:
    """规范化性别输出"""
    if not value:
        return "无法判断"
    value = str(value).strip()
    if value in VALID_GENDER:
        return value
    # 尝试模糊匹配
    if "男" in value:
        return "男性"
    if "女" in value:
        return "女性"
    return "无法判断"


def _validate_gender_evidence(gender_evidence: Dict[str, str]) -> Tuple[bool, str]:
    """
    验证性别判断的证据是否充分
    
    Returns:
        (is_valid, reason)
    """
    if not gender_evidence:
        return False, "缺少性别判断证据"
    
    appearance = gender_evidence.get("appearance", "")
    environment = gender_evidence.get("environment", "")
    consistency = gender_evidence.get("consistency", "")
    
    # 检查是否有有效线索
    has_appearance_clue = appearance and "未见" not in appearance and "无法" not in appearance
    has_env_clue = environment and "未见" not in environment and "无法" not in environment
    
    # 至少需要一个有效线索
    if not has_appearance_clue and not has_env_clue:
        return False, "外观线索和环境线索均不足"
    
    # 检查线索一致性
    if "矛盾" in consistency or "不一致" in consistency:
        return False, "多个线索指向不一致"
    
    return True, ""


def _build_evidence_from_context(
    det: Dict[str, Any],
    cred: Dict[str, Any],
    qwen_result: Dict[str, Any]
) -> Dict[str, str]:
    """
    从多个来源构建人物体征 evidence
    确保包含三要素：参照物、全身、角度影响
    """
    evidence = {}
    
    # 1. 参照物
    reference_objects = det.get("reference_objects", [])
    if reference_objects:
        obj_names = list(set([o["label"] for o in reference_objects[:5]]))
        evidence["reference"] = f"参照物：检测到 {', '.join(obj_names)}（来自{det.get('engine', 'unknown')}检测）"
    else:
        # 尝试从 Gemini 3 结果获取
        qwen_objects = qwen_result.get("objects", {}).get("detected", [])
        if qwen_objects:
            evidence["reference"] = f"参照物：Gemini 3 识别到 {', '.join(qwen_objects[:5])}"
        else:
            evidence["reference"] = "参照物：未检测到明显参照物（无法进行尺寸对比）"
    
    # 2. 全身可见性
    person_visibility = det.get("person_visibility", {})
    visibility = person_visibility.get("visibility", "不可见")
    detail = person_visibility.get("detail", "")
    evidence["body_visibility"] = f"全身：{visibility}（{detail}）" if detail else f"全身：{visibility}"
    
    # 从 Gemini 3 结果补充
    qwen_person = qwen_result.get("person", {})
    qwen_evidence = qwen_person.get("evidence", {})
    # 确保 qwen_evidence 是字典类型
    if not isinstance(qwen_evidence, dict):
        qwen_evidence = {}
    if isinstance(qwen_evidence, dict) and qwen_evidence.get("body_visibility"):
        evidence["body_visibility"] = qwen_evidence["body_visibility"]
    
    # 3. 角度影响
    angle_impact = cred.get("angle_impact", {})
    evidence["angle_impact"] = angle_impact.get("evidence", "角度影响：未知（无法评估）")
    
    # 如果 Gemini 3 提供了更具体的角度判断，使用它
    if isinstance(qwen_evidence, dict) and qwen_evidence.get("angle_impact"):
        evidence["angle_impact"] = qwen_evidence["angle_impact"]
    
    return evidence


def _force_add_missing_evidence(evidence: Dict[str, str], missing: List[str]) -> Dict[str, str]:
    """为缺失的 evidence 字段添加默认值"""
    result = dict(evidence)
    
    defaults = {
        "参照物": "参照物：未检测到（信息不足，无法进行身高/体型推断）",
        "全身": "全身：不可见或无法判断（信息不足）",
        "角度影响": "角度影响：未知（缺少焦距信息，无法评估透视影响）"
    }
    
    for key in missing:
        if key == "参照物":
            result["reference"] = defaults[key]
        elif key == "全身":
            result["body_visibility"] = defaults[key]
        elif key == "角度影响":
            result["angle_impact"] = defaults[key]
    
    return result


def _extract_body_type_from_partial_features(partial_features: Dict[str, str]) -> Tuple[str, bool]:
    """
    从局部特征中提取体型判断
    
    即使没有参照物，也可以通过局部特征（手部、手臂、脸部、颈肩、身体）推断体型
    
    Returns:
        (body_type, has_valid_clue)
    """
    if not partial_features:
        return "无法判断", False
    
    # 检查是否有有效的局部特征
    valid_features = []
    feature_keys = ["hand", "arm", "face", "neck_shoulder", "body"]
    
    for key in feature_keys:
        value = partial_features.get(key, "")
        # 排除无效的特征（未见、无法、N/A等）
        if value and "未见" not in value and "无法" not in value and "N/A" not in value and "不可见" not in value:
            valid_features.append(key)
    
    # 如果没有有效的局部特征，无法判断
    if not valid_features:
        return "无法判断", False
    
    # 检查 body_type_clue 综合判断
    body_type_clue = partial_features.get("body_type_clue", "")
    if body_type_clue and "无法" not in body_type_clue and "不确定" not in body_type_clue:
        # 从 body_type_clue 中提取体型
        normalized = _normalize_body_type(body_type_clue)
        if normalized != "无法判断":
            return normalized, True
    
    # 如果没有明确的 body_type_clue，从各个局部特征中推断
    # 扩展关键词列表 - 更全面的关键词
    slim_keywords = [
        "纤细", "修长", "瘦削", "骨骼", "线条分明", "瘦", "细", 
        "锁骨明显", "锁骨", "骨感", "瘦小", "苗条", "纤弱",
        "手指修长", "手腕细", "胳膊细", "身材细小",
        "细瘦", "消瘦", "窄窄", "瘦弱", "单薄"
    ]
    fat_keywords = [
        "圆润", "有肉", "粗", "壮", "胖", "丰满", "赘肉", 
        "肌肉", "结实", "厚实", "健壮", "粗壮", "高大",
        "手指短粗", "手腕粗", "胳膊粗", "双下巴",
        "腹部", "小腹", "圆脸", "肉感", "宽厚"
    ]
    normal_keywords = [
        "匀称", "正常", "适中", "标准", "中等", "健康"
    ]
    
    clues = []
    all_text = " ".join([partial_features.get(key, "") for key in valid_features])
    
    for keyword in slim_keywords:
        if keyword in all_text:
            clues.append("偏瘦")
            break
    
    for keyword in fat_keywords:
        if keyword in all_text:
            clues.append("偏壮")
            break
    
    for keyword in normal_keywords:
        if keyword in all_text:
            clues.append("匀称")
            break
    
    if clues:
        # 统计最多的线索
        from collections import Counter
        most_common = Counter(clues).most_common(1)
        if most_common:
            return most_common[0][0], True
    
    # 如果仍然无法判断，但有有效特征，默认返回"匀称"（因为没有明显胖/瘦特征）
    if valid_features:
        return "匀称", True
    
    return "无法判断", False


def person_module(
    det: Dict[str, Any],
    cred: Dict[str, Any],
    qwen_result: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    人物体征分析主入口
    
    evidence gate 规则：
    - 身高判断：需要参照物 + 全身可见性 + 角度信息
    - 体型判断：可以通过局部特征（手部、手臂、脸部等）推断，不一定需要参照物
    - 姿态判断：需要可见身体部分
    
    Args:
        det: 本地检测结果
        cred: 可信度分析结果
        qwen_result: Gemini 3 分析结果（可选）
    
    Returns:
        人物体征分析结果
    """
    qwen_result = qwen_result or {}
    
    # 从 Qwen 结果获取人物分析
    qwen_person = qwen_result.get("person", {})
    partial_features = qwen_person.get("partial_features", {})
    
    # 检查是否检测到人物（本地检测或 Qwen 检测）
    persons = det.get("persons", [])
    local_person_detected = bool(persons)
    
    # Qwen 检测到人物（支持布尔值、字符串、数字）
    qwen_detected = qwen_person.get("detected", False)
    if isinstance(qwen_detected, str):
        qwen_detected = qwen_detected.lower() in ("true", "1", "yes")
    qwen_person_detected = bool(qwen_detected)
    
    # Qwen 返回了人数 > 0
    qwen_count = qwen_person.get("count", 0)
    if isinstance(qwen_count, str):
        try:
            qwen_count = int(qwen_count)
        except:
            qwen_count = 0
    qwen_has_count = qwen_count > 0
    
    # Qwen 返回了任何局部特征
    has_partial_features = bool(partial_features) and any(
        v and "未见" not in str(v) and "N/A" not in str(v) 
        for v in partial_features.values()
    )
    
    # Qwen 返回了体型相关的 evidence
    qwen_evidence = qwen_person.get("evidence", {})
    # 确保 qwen_evidence 是字典类型
    if not isinstance(qwen_evidence, dict):
        qwen_evidence = {}
    body_vis = qwen_evidence.get("body_visibility", "")
    has_body_visibility = body_vis and "可见" in body_vis and "不可见" not in body_vis
    
    # Qwen 返回了有效的体型判断
    qwen_body_type = qwen_person.get("body_type", "")
    has_valid_body_type = qwen_body_type and "无法" not in qwen_body_type and qwen_body_type.strip() != ""
    
    # 综合判断：任一条件满足即认为检测到人物
    has_person_detected = (
        local_person_detected or 
        qwen_person_detected or 
        qwen_has_count or 
        has_partial_features or
        has_body_visibility or
        has_valid_body_type
    )
    
    # 如果本地和 Qwen 都没检测到人物，才返回空结果
    if not has_person_detected:
        return {
            "detected": False,
            "count": 0,
            "gender": "无法判断",
            "gender_evidence": {
                "appearance": "外观线索：N/A（未检测到人物）",
                "environment": "环境线索：N/A",
                "consistency": "线索一致性：N/A"
            },
            "height": "无法判断",
            "body_type": "无法判断",
            "posture": "不确定",
            "evidence": {
                "reference": "参照物：N/A（未检测到人物）",
                "body_visibility": "全身：不可见（未检测到人物）",
                "angle_impact": "角度影响：N/A（未检测到人物）"
            },
            "evidence_list": ["来自检测：当前画面未检测到人物"],
            "limitations": ["无人物，无法进行体征分析"],
            "confidence": "low"
        }
    
    # 构建 evidence
    evidence = _build_evidence_from_context(det, cred, qwen_result)
    
    # 验证 evidence 是否满足三要素
    is_valid, missing = validate_person_evidence(evidence)
    
    # 如果缺失，补充默认值
    if missing:
        evidence = _force_add_missing_evidence(evidence, missing)
    
    # 性别判断（单独处理，不受体征 evidence gate 影响）
    gender_evidence = qwen_person.get("gender_evidence", {})
    gender_valid, gender_reason = _validate_gender_evidence(gender_evidence)
    
    if gender_valid:
        gender = _normalize_gender(qwen_person.get("gender", ""))
    else:
        gender = "无法判断"
        # 补充默认的 gender_evidence
        if not gender_evidence:
            gender_evidence = {
                "appearance": "外观线索：未提供有效线索",
                "environment": "环境线索：未提供有效线索",
                "consistency": f"线索一致性：{gender_reason}"
            }
    
    limitations = []
    
    # 身高判断：严格要求参照物
    has_reference = "未检测到" not in evidence.get("reference", "") and "无明显" not in evidence.get("reference", "")
    
    if is_valid and has_reference:
        height = _normalize_height(qwen_person.get("height", ""))
    else:
        height = "无法判断"
        if not has_reference:
            limitations.append("参照物不明显，无法准确判断身高")
    
    # 体型判断：可以通过局部特征推断
    # 先尝试从 Qwen 的直接结果获取
    body_type = _normalize_body_type(qwen_person.get("body_type", ""))
    
    # 如果 Qwen 直接结果是"无法判断"，尝试从局部特征推断
    if body_type == "无法判断":
        # 优先从 partial_features 推断
        if partial_features:
            inferred_body_type, has_clue = _extract_body_type_from_partial_features(partial_features)
            if has_clue:
                body_type = inferred_body_type
                limitations.append("体型基于局部特征推断，仅供参考")
        
        # 如果还是无法判断，检查身体可见性
        if body_type == "无法判断" and has_body_visibility:
            body_type = "匀称"
            limitations.append("体型无明显胖瘦特征，默认为匀称")
        
        # 最终 fallback：如果检测到了人物（任何条件），但上面都没有给出判断，默认匀称
        if body_type == "无法判断" and has_person_detected:
            body_type = "匀称"
            limitations.append("体型无足够线索，默认为匀称")
    
    # 姿态判断
    if is_valid:
        posture = _normalize_posture(qwen_person.get("posture", ""))
        confidence = qwen_person.get("confidence", "low")
    else:
        posture = "不确定"
        confidence = "low"
        if missing:
            limitations.append(f"evidence 缺少：{', '.join(missing)}，姿态判断降级")
    
    # ★★★ 终极保底：走到这里说明检测到了人物，绝对不允许返回"无法判断" ★★★
    if body_type == "无法判断":
        body_type = "匀称"
        if "体型" not in ' '.join(limitations):
            limitations.append("体型无明显特征，默认为匀称")
    
    if not limitations:
        limitations = ["人物体征估计受拍摄角度、参照物等因素影响，仅供参考"]
    
    # 构建 evidence_list（用于前端展示）
    evidence_list = [
        evidence.get("reference", ""),
        evidence.get("body_visibility", ""),
        evidence.get("angle_impact", "")
    ]
    evidence_list = [e for e in evidence_list if e]  # 过滤空值
    
    # 确定人物数量（优先用 Qwen 的结果，否则用本地检测）
    person_count = qwen_count if qwen_count > 0 else len(persons)
    if person_count == 0 and has_person_detected:
        person_count = 1  # 检测到人物但数量未知，默认为1
    
    return {
        "detected": True,
        "count": person_count,
        "gender": gender,
        "gender_evidence": gender_evidence,
        "height": height,
        "body_type": body_type,
        "posture": posture,
        "partial_features": partial_features if partial_features else None,
        "evidence": evidence,
        "evidence_list": evidence_list,
        "limitations": limitations,
        "confidence": confidence,
        "_qwen_raw": qwen_person if qwen_person else None
    }
